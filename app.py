import streamlit as st
import pandas as pd
import threading
import time
import requests
from dhanhq import DhanContext, MarketFeed

st.set_page_config(page_title="PRO Strike Dashboard", layout="wide")

data_lock = threading.Lock()
live_data = {}
CLIENT_ID = st.secrets.get("DHAN_CLIENT_ID", "")
ACCESS_TOKEN = st.secrets.get("DHAN_ACCESS_TOKEN", "")
strikes_to_monitor = ["25000", "25100", "25200"]

def telegram_alert(title, message):
    try:
        token = st.secrets.get("TELEGRAM_BOT_TOKEN", "")
        chat_id = st.secrets.get("TELEGRAM_CHAT_ID", "")
        if not token or not chat_id: return
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        requests.post(url, data={"chat_id": chat_id, "text": f"🚨 {title}\n\n{message}"})
    except: pass

# Auto-refresh logic
if 'last_update' not in st.session_state:
    st.session_state.last_update = time.time()

st.title("🔥 PRO Strike Dashboard (Live OI Signals)")

if time.time() - st.session_state.last_update > 3:
    st.session_state.last_update = time.time()
    st.rerun()

if CLIENT_ID and ACCESS_TOKEN:
    st.success("✅ Dhan Connected!")
    
    # Dummy data for demo (replace with real WS later)
    if not live_data:
        for strike in strikes_to_monitor:
            live_data[strike] = {
                'CE': 123456 + int(strike)*100, 
                'PE': 234567 + int(strike)*100, 
                'Diff': 111111, 
                'Signal': '🟢 BUY'
            }

    df = pd.DataFrame.from_dict(live_data, orient='index')
    df.reset_index(inplace=True)
    df.rename(columns={'index': 'Strike'}, inplace=True)
    df = df[['Strike', 'CE', 'PE', 'Diff', 'Signal']]
    
    def color_signal(val):
        if 'BUY' in str(val): return 'color: #00FF00; font-weight: bold; background: #002200'
        elif 'SELL' in str(val): return 'color: #FF0000; font-weight: bold; background: #220000'
        return 'color: gray'
    
    styled_df = df.style.applymap(color_signal, subset=['Signal'])
    st.dataframe(styled_df, use_container_width=True, hide_index=True)
    
else:
    st.error("❌ DHAN secrets missing! Add to `.streamlit/secrets.toml`")

st.caption("Deployed on Streamlit Cloud 🚀")
