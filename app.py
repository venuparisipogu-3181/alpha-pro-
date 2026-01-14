import streamlit as st
import pandas as pd
import numpy as np
import time
import math
from datetime import datetime

st.set_page_config(layout="wide", page_title="Alpha Pro v9.0")

# Simple Session State
if 'portfolio' not in st.session_state: st.session_state.portfolio = []
if 'cash' not in st.session_state: st.session_state.cash = 100000
if 'pnl' not in st.session_state: st.session_state.pnl = 0

# Simple Telegram (Optional - Works without)
def telegram(msg):
    try:
        import requests
        requests.post("https://api.telegram.org/bot8289933882:AAGgTyAhFHYzlKbZ_0rvH8GztqXeTB6P-yQ/sendMessage", 
                     data={'chat_id': '2115666034', 'text': msg[:1000]})
        return True
    except:
        return False

st.title("🚀 ALPHA PRO v9.0 - CE + PE Trading")

# Index Data
index_name = st.selectbox("INDEX", ["NIFTY", "BANKNIFTY", "SENSEX"])
nifty = 25700 + math.sin(time.time()/100)*50

col1, col2, col3 = st.columns(3)
col1.metric("SPOT", f"₹{nifty:.0f}")
col2.metric("CASH", f"₹{st.session_state.cash:,.0f}")
col3.metric("P&L", f"₹{st.session_state.pnl:,.0f}")

# Strike Table - SIMPLIFIED
st.header("🎯 CE + PE STRIKES")
strikes = []
for i in range(9):
    strike = 25500 + i*100
    ce_price = max(20, 150 + math.sin(time.time()/500 + i)*40)
    pe_price = max(20, 140 + math.sin(time.time()/600 - i)*35)
    strikes.append([strike, f"₹{ce_price:.0f}", f"{int(120000+i*10000)/1000}K", f"₹{pe_price:.0f}", f"{int(130000+i*12000)/1000}K", "1.15"])
    
df = pd.DataFrame(strikes, columns=["Strike", "CE LTP", "CE OI", "PE LTP", "PE OI", "PCR"])
st.dataframe(df, use_container_width=True)

# Trading Panels
col_ce, col_pe = st.columns(2)

with col_ce:
    st.subheader("🟢 CE BUY")
    ce_strike = st.selectbox("CE", ["25700CE", "25800CE", "25600CE"])
    ce_qty = st.number_input("CE Qty", 25, 200, 50)
    ce_price = st.number_input("CE ₹", 50, 300, 150)
    
    if st.button("🚀 BUY CE", use_container_width=True):
        cost = ce_qty * ce_price
        if cost <= st.session_state.cash:
            st.session_state.cash -= cost
            st.session_state.portfolio.append({
                'symbol': ce_strike, 'qty': ce_qty, 
                'buy_price': ce_price, 'status': 'LIVE'
            })
            telegram(f"🟢 BUY {ce_strike} {ce_qty}x{ce_price}")
            st.success("✅ CE BOUGHT!")
            st.rerun()
        else:
            st.error("❌ NO CASH!")

with col_pe:
    st.subheader("🔴 PE BUY")
    pe_strike = st.selectbox("PE", ["25700PE", "25800PE", "25600PE"])
    pe_qty = st.number_input("PE Qty", 25, 200, 50)
    pe_price = st.number_input("PE ₹", 40, 250, 120)
    
    if st.button("🔻 BUY PE", use_container_width=True):
        cost = pe_qty * pe_price
        if cost <= st.session_state.cash:
            st.session_state.cash -= cost
            st.session_state.portfolio.append({
                'symbol': pe_strike, 'qty': pe_qty, 
                'buy_price': pe_price, 'status': 'LIVE'
            })
            telegram(f"🔴 BUY {pe_strike} {pe_qty}x{pe_price}")
            st.success("✅ PE BOUGHT!")
            st.rerun()
        else:
            st.error("❌ NO CASH!")

# Portfolio
st.header("📊 PORTFOLIO")
if st.session_state.portfolio:
    port_data = []
    for trade in st.session_state.portfolio[-5:]:
        if trade['status'] == 'LIVE':
            # Simulate OI Exit
            oi_change = int(math.sin(time.time()/300 + hash(trade['symbol'])) * 25000)
            if abs(oi_change) > 15000:
                trade['status'] = 'EXIT'
                pnl = (trade['buy_price'] * 1.1 - trade['buy_price']) * trade['qty']
                st.session_state.pnl += pnl
            
            port_data.append([
                trade['symbol'], trade['qty'], 
                f"₹{trade['buy_price']:.0f}",
                f"{oi_change:+,} OI", 
                "🚨 EXIT" if trade['status'] != 'LIVE' else "✅ LIVE"
            ])
    
    if port_data:
        st.dataframe(pd.DataFrame(port_data, columns=["Strike", "Qty", "Entry", "OI Δ", "Status"]), use_container_width=True)
else:
    st.info("👆 BUY to start!")

# Buttons
col1, col2, col3 = st.columns(3)
if col1.button("📱 TELEGRAM REPORT"): 
    telegram(f"📊 NIFTY {nifty:.0f} | Cash ₹{st.session_state.cash:,.0f} | P&L ₹{st.session_state.pnl:,.0f}")
if col2.button("🗑️ RESET"): 
    st.session_state.portfolio = []
    st.session_state.cash = 100000
    st.session_state.pnl = 0
    st.rerun()
if col3.button("🔄 REFRESH"): st.rerun()

st.markdown("---")
st.success("✅ **SIMPLE | NO ERRORS | CE+PE | AUTO OI EXIT** 🚀")
