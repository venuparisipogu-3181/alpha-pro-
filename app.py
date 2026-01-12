import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import requests
import time
from datetime import datetime

# Page Setup
st.set_page_config(layout="wide", page_title="Alpha Pro Trading")

# Telegram Info (మీ టోకెన్స్ ఇక్కడ ఇవ్వండి)
TOKEN = "8289933882:AAGgTyAhFHYzlKbZ_0rvH8GztqXeTB6P-yQ"
CHAT_ID = ""2115666034"

def send_alert(msg):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    requests.post(url, data={'chat_id': CHAT_ID, 'text': msg, 'parse_mode': 'HTML'})

st.title("🚀 Alpha Pro - Live Terminal")

# Placeholders (ఎర్రర్స్ రాకుండా ఉండటానికి)
status_spot = st.empty()
chart_spot = st.empty()
table_spot = st.empty()

while True:
    try:
        # Data Fetching
        df = yf.download("^NSEI", period="2d", interval="1m", progress=False)
        df.reset_index(inplace=True)
        
        # Sync Error Fix: RangeIndex సమస్య రాకుండా క్లీన్ చేయడం
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        # Indicators
        df['EMA20'] = ta.ema(df['Close'], length=20)
        df['RSI'] = ta.rsi(df['Close'], length=14)
        
        curr_p = float(df['Close'].iloc[-1])
        rsi_v = float(df['RSI'].iloc[-1])
        ema_v = float(df['EMA20'].iloc[-1])

        with status_spot.container():
            c1, c2, c3 = st.columns(3)
            c1.metric("LTP", f"{curr_p:.2f}")
            c2.metric("RSI", f"{rsi_v:.1f}")
            c3.write(f"Updated: {datetime.now().strftime('%H:%M:%S')}")

        with chart_spot:
            st.line_chart(df[['Close', 'EMA20']].tail(50))

        with table_spot.container():
            st.subheader("🎯 Strike Selection")
            atm = int(round(curr_p / 50) * 50)
            
            # Duplicate Key Error Fix: ప్రతి బటన్‌కు Unique Time Key ఇవ్వడం
            btn_key = f"buy_{atm}_{int(time.time())}"
            if st.button(f"EXECUTE {atm} CE", key=btn_key, use_container_width=True):
                send_alert(f"🚀 Alpha Pro Order: {atm} CE @ {curr_p}")
                st.balloons()

    except Exception as e:
        st.error(f"Waiting for Data... {e}")
    
    time.sleep(15)
    st.rerun()
