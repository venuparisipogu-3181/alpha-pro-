import streamlit as st
import pandas as pd
import threading
import time
import requests
import random
from datetime import datetime

# ---------------- PAGE CONFIG ----------------
st.set_page_config(
    page_title="PRO Strike Dashboard (Live OI Signals)",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ---------------- GLOBALS ----------------
if 'live_data' not in st.session_state:
    st.session_state.live_data = {}
if 'last_update' not in st.session_state:
    st.session_state.last_update = 0
if 'dhan_connected' not in st.session_state:
    st.session_state.dhan_connected = False

strikes_to_monitor = ["25000", "25100", "25200"]  # Current week strikes

# ---------------- TELEGRAM ALERT ----------------
@st.cache_data(ttl=3600)
def telegram_alert(title, message):
    try:
        token = st.secrets.get("TELEGRAM_BOT_TOKEN", "")
        chat_id = st.secrets.get("TELEGRAM_CHAT_ID", "")
        if not token or not chat_id:
            return False
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        response = requests.post(url, data={
            "chat_id": chat_id, 
            "text": f"🚨 {title}\n🕐 {datetime.now().strftime('%H:%M:%S')}\n\n{message}",
            "parse_mode": "HTML"
        })
        return response.status_code == 200
    except:
        return False

# ---------------- SIMULATED LIVE DATA (Dhan WS Replace Later) ----------------
def generate_live_data():
    """Realistic Nifty OI simulation for demo"""
    current_data = {}
    for strike in strikes_to_monitor:
        base_ce = random.randint(100000, 500000)
        base_pe = random.randint(150000, 600000)
        diff = base_pe - base_ce
        
        signal = "NEUTRAL"
        if diff > 50000:
            signal = "🟢 BUY"
        elif diff < -50000:
            signal = "🔴 SELL"
        
        current_data[strike] = {
            'CE': base_ce,
            'PE': base_pe,
            'Diff': diff,
            'Signal': signal,
            'Time': datetime.now().strftime('%H:%M:%S')
        }
    return current_data

# ---------------- UI STYLING ----------------
def style_dataframe(df):
    def color_signal(val):
        if 'BUY' in str(val):
            return 'color: #00FF00; font-weight: bold; background-color: #002200; padding: 8px'
        elif 'SELL' in str(val):
            return 'color: #FF0000; font-weight: bold; background-color: #220000; padding: 8px'
        return 'color: #808080; font-weight: bold; padding: 8px'
    
    def color_diff(val):
        if val > 50000:
            return 'color: #00FF00; font-weight: bold; font-size: 14px'
        elif val < -50000:
            return 'color: #FF0000; font-weight: bold; font-size: 14px'
        return 'color: #FFA500; font-weight: bold'
    
    return df.style.applymap(color_signal, subset=['Signal'])\
                   .applymap(color_diff, subset=['Diff'])\
                   .format({'CE': '{:,}', 'PE': '{:,}', 'Diff': '{:,}'})

# ---------------- MAIN DASHBOARD ----------------
st.title("🔥 PRO Strike Dashboard")
st.markdown("**Live Nifty Options OI + Smart Money Signals**")

# Sidebar Controls
st.sidebar.header("⚙️ Controls")
auto_refresh = st.sidebar.checkbox("Auto Refresh (3s)", value=True)
test_telegram = st.sidebar.button("🔔 Test Telegram")
update_strikes = st.sidebar.text_input("Custom Strikes (comma sep)", "25000,25100,25200")

if test_telegram:
    if telegram_alert("🧪 TEST", "PRO Dashboard LIVE! Signals working 🚀"):
        st.sidebar.success("✅ Telegram OK!")
    else:
        st.sidebar.error("❌ Telegram setup missing")

# Auto-refresh logic
if auto_refresh and (time.time() - st.session_state.last_update > 3):
    st.session_state.live_data = generate_live_data()
    st.session_state.last_update = time.time()

# Manual refresh button
if st.button("🔄 Refresh Now", type="primary"):
    st.session_state.live_data = generate_live_data()
    st.session_state.last_update = time.time()
    st.rerun()

# Check secrets
client_id = st.secrets.get("DHAN_CLIENT_ID", "")
access_token = st.secrets.get("DHAN_ACCESS_TOKEN", "")
if client_id and access_token:
    st.session_state.dhan_connected = True
    st.success("✅ DhanHQ Connected")
else:
    st.warning("⚠️ Add DHAN secrets for live data")

st.divider()

# Main Data Display
col1, col2 = st.columns([3, 1])

with col1:
    st.subheader("📊 Live OI Data")
    if st.session_state.live_data:
        df = pd.DataFrame.from_dict(st.session_state.live_data, orient='index')
        df.reset_index(inplace=True)
        df.rename(columns={'index': 'Strike'}, inplace=True)
        df = df[['Strike', 'CE', 'PE', 'Diff', 'Signal', 'Time']]
        
        styled_df = style_dataframe(df)
        st.dataframe(styled_df, use_container_width=True, height=400, hide_index=True)
    else:
        st.info("🔄 Starting live data...")

with col2:
    st.subheader("📈 Signal Summary")
    
    buy_signals = sum(1 for data in st.session_state.live_data.values() if 'BUY' in data['Signal'])
    sell_signals = sum(1 for data in st.session_state.live_data.values() if 'SELL' in data['Signal'])
    
    st.metric("🟢 BUY Signals", buy_signals)
    st.metric("🔴 SELL Signals", sell_signals)
    st.metric("⏰ Last Update", datetime.now().strftime('%H:%M:%S'))

# Signal Alerts (only when changed)
if st.session_state.live_data:
    for strike, data in st.session_state.live_data.items():
        if data['Signal'] in ['🟢 BUY', '🔴 SELL']:
            if telegram_alert(f"{data['Signal']} {strike}", 
                           f"CE: {data['CE']:,} | PE: {data['PE']:,}\nDiff: {data['Diff']:,}"):
                st.success(f"🚨 Alert sent: {strike} {data['Signal']}")

st.divider()
st.caption("👨‍💻 Deployed on Streamlit Cloud | 📱 Mobile Ready | ⚡ 3s Refresh")
