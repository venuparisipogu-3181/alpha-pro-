import streamlit as st
import pandas as pd
import threading
import time
import requests
from streamlit_autorefresh import st_autorefresh

# DhanHQ లైబ్రరీ
from dhanhq import marketfeed 

# ---------------- PAGE CONFIG ----------------
st.set_page_config(
    page_title="PRO Strike Dashboard (Live OI & Signals)",
    layout="wide"
)

# ---------------- GLOBALS & CONFIG ----------------
data_lock = threading.Lock()
live_data = {}

# ఇక్కడ మీకు కావాల్సిన ఇండెక్స్ మరియు స్ట్రైక్స్ ఇవ్వండి
UNDERLYING_SYMBOL = "NIFTY"
strikes_to_monitor = ["25000", "25100", "25200"] 

# 🔐 SECURITY FIX: డైరెక్ట్ గా కీలు రాయకుండా secrets వాడాము
CLIENT_ID = st.secrets.get("DHAN_CLIENT_ID", "")
ACCESS_TOKEN = st.secrets.get("DHAN_ACCESS_TOKEN", "")

# ---------------- AUTO FETCH REAL TOKENS (MEMORY OPTIMIZED) ----------------
# రోజుకు ఒక్కసారి మాత్రమే డౌన్‌లోడ్ అయ్యేలా Cache వాడుతున్నాం
@st.cache_data(ttl=86400) 
def get_real_dhan_tokens(symbol, strikes):
    st.info("📥 ధన్ సర్వర్ నుండి టోకెన్స్ డౌన్‌లోడ్ అవుతున్నాయి (Memory Optimized)...")
    csv_url = "https://images.dhan.co/api-data/api-scrip-master.csv"
    
    try:
        # 🚀 MEMORY FIX: సర్వర్ క్రాష్ అవ్వకుండా కేవలం ఈ 6 కాలమ్స్ మాత్రమే తీసుకుంటున్నాం
        required_cols = [
            'SEM_INSTRUMENT_NAME', 'SEM_EXM_TRAD_SYMBOL', 'SEM_EXPIRY_DATE', 
            'SEM_STRIKE_PRICE', 'SEM_OPTION_TYPE', 'SEM_SMST_SECURITY_ID'
        ]
        
        df = pd.read_csv(csv_url, usecols=required_cols, low_memory=False)
        df_opt = df[(df['SEM_INSTRUMENT_NAME'] == 'OPTIDX') & (df['SEM_EXM_TRAD_SYMBOL'].str.startswith(symbol))]
        
        # దగ్గరి ఎక్స్‌పైరీ (Nearest Expiry) ఫిల్టర్ చేయడం
        df_opt['SEM_EXPIRY_DATE'] = pd.to_datetime(df_opt['SEM_EXPIRY_DATE'])
        nearest_expiry = df_opt['SEM_EXPIRY_DATE'].min()
        df_current_expiry = df_opt[df_opt['SEM_EXPIRY_DATE'] == nearest_expiry]
        
        real_tokens = {}
        for strike in strikes:
            strike_float = float(strike)
            ce_row = df_current_expiry[(df_current_expiry['SEM_STRIKE_PRICE'] == strike_float) & (df_current_expiry['SEM_OPTION_TYPE'] == 'CE')]
            pe_row = df_current_expiry[(df_current_expiry['SEM_STRIKE_PRICE'] == strike_float) & (df_current_expiry['SEM_OPTION_TYPE'] == 'PE')]
            
            if not ce_row.empty and not pe_row.empty:
                ce_id = int(ce_row.iloc[0]['SEM_SMST_SECURITY_ID'])
                pe_id = int(pe_row.iloc[0]['SEM_SMST_SECURITY_ID'])
                real_tokens[strike] = {"CE": ce_id, "PE": pe_id}
                
        st.success("✅ నిజమైన టోకెన్స్ కనెక్ట్ అయ్యాయి!")
        return real_tokens
    except Exception as e:
        st.error(f"❌ టోకెన్స్ తీసుకురావడంలో తప్పు జరిగింది: {e}")
        return {}

# ఫంక్షన్ కాల్ చేసి నిజమైన టోకెన్స్ తెచ్చుకోవడం
#tokens = get_real_dhan_tokens(UNDERLYING_SYMBOL, strikes_to_monitor)
tokens = {
    "25000": {"CE": 11111, "PE": 22222},
    "25100": {"CE": 33333, "PE": 44444},
    "25200": {"CE": 55555, "PE": 66666}
}
# ---------------- TELEGRAM ALERT ----------------
def telegram_alert(title, message):
    try:
        token = st.secrets.get("TELEGRAM_BOT_TOKEN", "")
        chat_id = st.secrets.get("TELEGRAM_CHAT_ID", "")
        if not token or not chat_id:
            return
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        requests.post(url, data={"chat_id": chat_id, "text": f"{title}\n\n{message}"})
    except:
        pass

# ---------------- WEBSOCKET THREAD ----------------
def fetch_data_thread(active_tokens):
    global live_data
    
    # ముందే స్ట్రక్చర్ సెటప్ చేయడం
    with data_lock:
        for strike in strikes_to_monitor:
            live_data[strike] = {'CE': 0, 'PE': 0, 'Diff': 0, 'Signal': 'NEUTRAL', 'Last_Alert': None}

    instruments = []
    for strike in strikes_to_monitor:
        if strike in active_tokens:
            instruments.append((2, str(active_tokens[strike]['CE']), 17)) 
            instruments.append((2, str(active_tokens[strike]['PE']), 17))

    if not instruments:
        return

    def on_connect(instance):
        print("🟢 Dhan WebSocket సక్సెస్! (Live Data వస్తోంది...)")

    def on_message(instance, message):
        global live_data
        try:
            if 'security_id' in message:
                sec_id = int(message['security_id'])
                oi_val = message.get('OI', message.get('oi', message.get('open_interest', 0)))
                
                if oi_val > 0:
                    with data_lock:
                        for strike, t_data in active_tokens.items():
                            updated = False
                            
                            if t_data['CE'] == sec_id:
                                live_data[strike]['CE'] = int(oi_val)
                                updated = True
                            elif t_data['PE'] == sec_id:
                                live_data[strike]['PE'] = int(oi_val)
                                updated = True
                                
                            if updated:
                                ce_oi = live_data[strike]['CE']
                                pe_oi = live_data[strike]['PE']
                                
                                diff = pe_oi - ce_oi
                                live_data[strike]['Diff'] = diff
                                
                                current_signal = "NEUTRAL"
                                if diff > 0:
                                    current_signal = "BUY"
                                elif diff < 0:
                                    current_signal = "SELL"
                                    
                                live_data[strike]['Signal'] = current_signal
                                
                                # టెలిగ్రామ్ లాజిక్ - కొత్త సిగ్నల్స్ మాత్రమే
                                last_alert = live_data[strike]['Last_Alert']
                                
                                if last_alert is None:
                                    live_data[strike]['Last_Alert'] = current_signal
                                elif current_signal in ["BUY", "SELL"] and current_signal != last_alert:
                                    msg = f"Strike: {strike}\nSignal: {current_signal}\nDiff: {diff}\nCE OI: {ce_oi} | PE OI: {pe_oi}"
                                    telegram_alert(f"🚨 {current_signal} ALERT", msg)
                                    live_data[strike]['Last_Alert'] = current_signal
                                elif current_signal == "NEUTRAL" and last_alert != "NEUTRAL":
                                    live_data[strike]['Last_Alert'] = "NEUTRAL"

        except Exception as e: 
            pass

    while True:
        try:
            # ఇక్కడ క్లయింట్ ఐడీ పాస్ అవుతుంది
            feed = marketfeed.MarketFeed(CLIENT_ID, ACCESS_TOKEN, instruments, on_connect=on_connect, on_message=on_message)
            feed.run_forever()
            time.sleep(5)
        except Exception as e:
            time.sleep(5)

# ---------------- BACKGROUND THREAD START ----------------
@st.cache_resource
def start_websocket(_active_tokens):
    if _active_tokens:
        t = threading.Thread(target=fetch_data_thread, args=(_active_tokens,), daemon=True)
        t.start()
        return t
    return None

start_websocket(tokens)

# ---------------- UI & DATAFRAME STYLING ----------------
def prepare_dataframe(data):
    if not data:
        return pd.DataFrame()
    df = pd.DataFrame.from_dict(data, orient='index')
    df.reset_index(inplace=True)
    df.rename(columns={'index': 'Strike'}, inplace=True)
    df = df[['Strike', 'CE', 'PE', 'Diff', 'Signal']]
    return df

def style_dataframe(df):
    def highlight_signal(val):
        if val == 'BUY':
            return 'color: #00FF00; font-weight: bold; background-color: #002200;' 
        elif val == 'SELL':
            return 'color: #FF0000; font-weight: bold; background-color: #220000;'
        return 'color: gray;'
        
    def highlight_diff(val):
        if val > 0:
            return 'color: #00FF00; font-weight: bold'
        elif val < 0:
            return 'color: #FF0000; font-weight: bold'
        return ''

    return df.style.applymap(highlight_signal, subset=['Signal']).applymap(highlight_diff, subset=['Diff'])

# ---------------- DASHBOARD DISPLAY ----------------
st.title("🔥 PRO Strike Dashboard (Live OI Signals)")

# ప్రతి 5 సెకన్లకు UI రిఫ్రెష్ (ఇప్పుడు క్రాష్ అవ్వదు కాబట్టి దీన్ని ఆన్ చేశాను)
st_autorefresh(interval=5000, key="data_refresh")

st.divider()

if not tokens:
    st.warning("⚠️ టోకెన్స్ డౌన్‌లోడ్ కాలేదు. దయచేసి ఇంటర్నెట్ కనెక్షన్ మరియు స్ట్రైక్ ప్రైస్ చెక్ చేయండి.")
elif live_data:
    with data_lock:
        df = prepare_dataframe(live_data)
        
    if not df.empty:
        styled_df = style_dataframe(df)
        st.dataframe(styled_df, use_container_width=True, hide_index=True, height=400)
else:
    st.info("🔄 ధన్ వెబ్‌సాకెట్ కనెక్ట్ అవుతోంది... లైవ్ డేటా కోసం వేచి ఉండండి.")
