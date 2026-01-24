import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import numpy as np
from dhanhq import dhanhq
import os
from dotenv import load_dotenv
import telegram
import asyncio
from datetime import datetime

# Load env
load_dotenv()

# Dhan Setup
dcx = dhanhq.DhanContext(os.getenv("DHAN_CLIENT_ID"), os.getenv("DHAN_ACCESS_TOKEN"))

# Telegram Setup
async def send_alert(message):
    bot = telegram.Bot(token=os.getenv("TELEGRAM_BOT_TOKEN"))
    await bot.send_message(chat_id=os.getenv("TELEGRAM_CHAT_ID"), text=message)

st.set_page_config(page_title="Options Screener", layout="wide")

# Sidebar
st.sidebar.title("🚀 Multi Index Screener")
index = st.sidebar.selectbox("Index", ["NIFTY", "BANKNIFTY", "FINNIFTY"])
side = st.sidebar.selectbox("Side", ["CE", "PE"])
st.sidebar.markdown("---")

# Session State
if 'tracked' not in st.session_state:
    st.session_state.tracked = []

# Dhan Data
@st.cache_data(ttl=60)  # 1 min cache
def get_chain(symbol):
    try:
        data = dcx.option_chain({"symbol": symbol})
        return data['data']
    except:
        return None

# Best Strike Logic
def best_strike(chain_data, side):
    if not chain_data: return None
    
    strikes = chain_data.get(side.lower(), [])
    pcr = chain_data.get('put_oi_total', 1) / chain_data.get('call_oi_total', 1)
    
    best = None
    max_score = 0
    
    for s in strikes:
        # Score: OI change + Delta + IV
        score = (s.get('oi_change_pct', 0) + 
                abs(s.get('delta', 0) - 0.3) * -100 + 
                s.get('iv', 0) / 10)
        
        if score > max_score:
            best = s
            max_score = score
    
    return best if (side=="CE" and pcr<0.8) or (side=="PE" and pcr>1.2) else None

# Main App
st.title("🔥 Nifty Options Screener - Greeks + Alerts")

col1, col2 = st.columns(2)

with col1:
    st.header("📊 Live Data")
    chain = get_chain(index)
    
    if chain:
        pcr = chain.get('put_oi_total',1)/chain.get('call_oi_total',1)
        st.metric("PCR", f"{pcr:.2f}")
        
        best = best_strike(chain, side)
        if best:
            st.success(f"**{side} Strike:** {best['strike']} | LTP: ₹{best['ltp']}")
            st.info(f"Delta: {best['delta']:.2f} | IV: {best['iv']:.1f}%")

with col2:
    if st.button("🚀 SELECT & TRACK STRIKE", use_container_width=True):
        best = best_strike(chain, side)
        if best:
            st.session_state.tracked.append({
                'symbol': f"{index}{best['expiry']}{best['strike']}{side}",
                'entry_price': best['ltp'],
                'entry_oi': best['oi'],
                'timestamp': datetime.now()
            })
            
            # Entry Alert
            msg = f"🟢 ENTRY {index} {side}\nStrike: {best['strike']}\nLTP: ₹{best['ltp']}\nPCR: {pcr:.2f}"
            asyncio.run(send_alert(msg))
            st.balloons()

# Tracked Strikes Table
if st.session_state.tracked:
    st.header("📈 Tracked Strikes")
    tracked_df = pd.DataFrame(st.session_state.tracked)
    st.dataframe(tracked_df)

    # Check Exits
    for i, strike in enumerate(st.session_state.tracked):
        # Simulate OI check (real Dhan data తో replace)
        current_oi = strike['entry_oi'] * np.random.uniform(0.7, 1.3)
        if current_oi < strike['entry_oi'] * 0.8:
            msg = f"🔴 EXIT {strike['symbol']} - OI -20%!"
            asyncio.run(send_alert(msg))
            st.error(f"EXIT: {strike['symbol']}")
            st.session_state.tracked.pop(i)

st.markdown("---")
st.caption("DhanHQ Live Data | Auto Alerts | Multi Index")
