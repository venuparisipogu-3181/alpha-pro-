import streamlit as st
import pandas as pd
import threading
import time
import requests
from streamlit_autorefresh import st_autorefresh
from dhanhq import DhanContext, MarketFeed  # v2 import

# ---------------- PAGE CONFIG ----------------
st.set_page_config(page_title="PRO Strike Dashboard (Live OI & Signals)", layout="wide")

# ---------------- GLOBALS & CONFIG ----------------
data_lock = threading.Lock()
live_data = {}
dhan_context = None
feed_instance = None

CLIENT_ID = st.secrets.get("DHAN_CLIENT_ID", "")
ACCESS_TOKEN = st.secrets.get("DHAN_ACCESS_TOKEN", "")
strikes_to_monitor = ["25000", "25100", "25200"]  # Change for current week

# ---------------- GET REAL TOKENS ----------------
@st.cache_data(ttl=300)  # Cache 5 mins
def get_option_tokens(strikes):
    """Dhan Option Chain API - Real tokens fetch"""
    try:
        from dhanhq import dhanhq
        dhan = dhanhq(dhan_context)
        # Get current expiry (NIFTY example)
        expiry_list = dhan.expiry_list(under_security_id=13, under_exchange_segment="IDX_I")
        current_expiry = expiry_list['data'][0]['expiry'] if expiry_list['data'] else "2026-02-27"
        
        tokens = {}
        for strike in strikes:
            # Option Chain for strike range
            chain = dhan.option_chain(under_security_id=13, under_exchange_segment="IDX_I", expiry=current_expiry)
            for row in chain['data']:
                if row['strike'] == int(strike):
                    tokens[strike] = {"CE": row['security_id_ce'], "PE": row['security_id_pe']}
                    break
        return tokens
    except:
        # Fallback manual (your original)
        return {"25000": {"CE": 11111, "PE": 22222}, "25100": {"CE": 33333, "PE": 44444}, "25200": {"CE": 55555, "PE": 66666}}

# ---------------- TELEGRAM ALERT ----------------
def telegram_alert(title, message):
    try:
        token = st.secrets.get("TELEGRAM_BOT_TOKEN", "")
        chat_id = st.secrets.get("TELEGRAM_CHAT_ID", "")
        if not token or not chat_id: return
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        requests.post(url, data={"chat_id": chat_id, "text": f"🚨 {title}\n\n{message}"})
    except: pass

# ---------------- WEBSOCKET THREAD ----------------
def fetch_data_thread(active_tokens):
    global live_data, feed_instance
    
    with data_lock:
        for strike in strikes_to_monitor:
            live_data[strike] = {'CE': 0, 'PE': 0, 'Diff': 0, 'Signal': 'NEUTRAL', 'Last_Alert': None}

    if CLIENT_ID and ACCESS_TOKEN:
        dhan_context = DhanContext(CLIENT_ID, ACCESS_TOKEN)
    
    instruments = []
    for strike, t_data in active_tokens.items():
        instruments.append((MarketFeed.NSE_FNO, str(t_data['CE']), MarketFeed.Quote))  # v2 format: (segment, sec_id, Quote)
        instruments.append((MarketFeed.NSE_FNO, str(t_data['PE']), MarketFeed.Quote))

    def on_message(message):
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
                                if diff > 50000:  # Threshold adjust
                                    current_signal = "🟢 BUY"
                                elif diff < -50000:
                                    current_signal = "🔴 SELL"
                                live_data[strike]['Signal'] = current_signal
                                
                                last_alert = live_data[strike]['Last_Alert']
                                if last_alert is None:
                                    live_data[strike]['Last_Alert'] = current_signal
                                elif current_signal in ["🟢 BUY", "🔴 SELL"] and current_signal != last_alert:
                                    msg = f"Strike: {strike}\nSignal: {current_signal}\nDiff: {diff:,}\nCE OI: {ce_oi:,} | PE OI: {pe_oi:,}"
                                    telegram_alert(f"{current_signal} PRO ALERT", msg)
                                    live_data[strike]['Last_Alert'] = current_signal
        except: pass

    while True:
        try:
            if instruments and dhan_context:
                feed_instance = MarketFeed(dhan_context, instruments, version="v2")
                def on_connect(): st.success("🟢 Dhan WebSocket LIVE!")
                feed_instance.on_message = on_message
                feed_instance.on_connect = on_connect
                feed_instance.run_forever()
            time.sleep(5)
        except Exception as e:
            st.error(f"Reconnecting... {e}")
            time.sleep(5)

# ---------------- START THREAD ----------------
@st.cache_resource
def start_dashboard():
    if CLIENT_ID and ACCESS_TOKEN:
        tokens = get_option_tokens(strikes_to_monitor)
        st.success(f"✅ Tokens loaded: {tokens}")
        t = threading.Thread(target=fetch_data_thread, args=(tokens,), daemon=True)
        t.start()
        return t
    return None

if CLIENT_ID and ACCESS_TOKEN:
    dhan_context = DhanContext(CLIENT_ID, ACCESS_TOKEN)
    start_dashboard()
else:
    st.error("❌ DHAN_CLIENT_ID & ACCESS_TOKEN secrets add చేయండి!")

# ---------------- UI ----------------
st.title("🔥 PRO Strike Dashboard (Live OI Signals)")
st_autorefresh(interval=3000, key="refresh")  # 3s

st.divider()

def prepare_df():
    if not live_data: return pd.DataFrame()
    with data_lock:
        df = pd.DataFrame.from_dict(live_data, orient='index')
        df.reset_index(inplace=True)
        df.rename(columns={'index': 'Strike'}, inplace=True)
        return df[['Strike', 'CE', 'PE', 'Diff', 'Signal']]

def style_df(df):
    def color_signal(val):
        if 'BUY' in str(val): return 'color: #00FF00; font-weight: bold; background: #002200'
        elif 'SELL' in str(val): return 'color: #FF0000; font-weight: bold; background: #220000'
        return 'color: gray'
    def color_diff(val):
        if val > 0: return 'color: #00FF00; font-weight: bold'
        elif val < 0: return 'color: #FF0000; font-weight: bold'
        return ''
    return df.style.applymap(color_signal, subset=['Signal']).applymap(color_diff, subset=['Diff'])

if live_data:
    df = prepare_df()
    if not df.empty:
        st.dataframe(style_df(df), use_container_width=True, hide_index=True, height=400)
    else:
        st.info("📊 OI data loading...")
else:
    st.info("🔄 Dhan WebSocket connecting... 1-2 mins wait (9:15 AM - 3:30 PM market hours)")

st.caption("💡 web.dhan.co → Profile → DhanHQ APIs → Token generate → .streamlit/secrets.toml")
