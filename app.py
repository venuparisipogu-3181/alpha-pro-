import streamlit as st
import pandas as pd
import threading
import time
import requests
from streamlit_autorefresh import st_autorefresh
from dhanhq import marketfeed 

# ---------------- PAGE CONFIG ----------------
st.set_page_config(
    page_title="PRO Strike Dashboard (Live OI & Signals)",
    layout="wide"
)

# ---------------- GLOBALS & CONFIG ----------------
data_lock = threading.Lock()
live_data = {}

CLIENT_ID = st.secrets.get("DHAN_CLIENT_ID", "")
ACCESS_TOKEN = st.secrets.get("DHAN_ACCESS_TOKEN", "")

# 🛑 CSV డౌన్‌లోడ్ తీసేసి, మాన్యువల్ టోకెన్స్ వాడుతున్నాం
strikes_to_monitor = ["25000", "25100", "25200"] 

# ఇక్కడ ఈ వారానికి సంబంధించిన నిజమైన టోకెన్స్ మార్చుకోండి
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
        requests.post(url, data={"chat_id": chat_id, "text": f"🚨 {title}\n\n{message}"})
    except:
        pass

# ---------------- WEBSOCKET THREAD ----------------
def fetch_data_thread(active_tokens):
    global live_data
    
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
                                
                                last_alert = live_data[strike]['Last_Alert']
                                
                                if last_alert is None:
                                    live_data[strike]['Last_Alert'] = current_signal
                                elif current_signal in ["BUY", "SELL"] and current_signal != last_alert:
                                    msg = f"Strike: {strike}\nSignal: {current_signal}\nDiff: {diff}\nCE OI: {ce_oi} | PE OI: {pe_oi}"
                                    telegram_alert(f"{current_signal} ALERT", msg)
                                    live_data[strike]['Last_Alert'] = current_signal
                                elif current_signal == "NEUTRAL" and last_alert != "NEUTRAL":
                                    live_data[strike]['Last_Alert'] = "NEUTRAL"

        except Exception as e: 
            pass

    while True:
        try:
            if CLIENT_ID and ACCESS_TOKEN:
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

# ప్రతి 5 సెకన్లకు UI రిఫ్రెష్
st_autorefresh(interval=5000, key="data_refresh")

st.divider()

if live_data:
    with data_lock:
        df = prepare_dataframe(live_data)
        
    if not df.empty:
        styled_df = style_dataframe(df)
        st.dataframe(styled_df, use_container_width=True, hide_index=True, height=400)
else:
    st.info("🔄 ధన్ వెబ్‌సాకెట్ కనెక్ట్ అవుతోంది... లైవ్ డేటా కోసం వేచి ఉండండి.")
