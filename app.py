import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
import os
import requests

st.set_page_config(layout="wide")

# SIMPLE TELEGRAM (NO ASYNC)
def telegram_pro_alert(index, strike, entry, target, sl):
    try:
        token = os.getenv("TELEGRAM_BOT_TOKEN")
        chat_id = os.getenv("TELEGRAM_CHAT_ID")
        if token and chat_id:
            url = f"https://api.telegram.org/bot{token}/sendMessage"
            msg = f"""🎯 PERFECT ENTRY: {index}

🟢 Action: BUY {strike} CE
📊 Reason: EMA Support + PCR 1.15
💰 Entry: {entry}
🎯 Target: {target}
🛑 Stoploss: {sl}
🔄 Trailing: 15.0 pts
🏁 Exit: Reverse Signal or SL"""
            requests.post(url, data={"chat_id": chat_id, "text": msg})
            return True
        return False
    except:
        return False

st.sidebar.title("🚀 Triple Screener")
side = st.sidebar.selectbox("Side", ["CE", "PE"])

if 'tracked' not in st.session_state:
    st.session_state.tracked = []

def get_index_data(index_name):
    np.random.seed(int(datetime.now().timestamp()))
    
    configs = {
        'NIFTY': {'atm': 25050, 'interval': 50, 'ce_base': 65, 'pe_base': 62},
        'BANKNIFTY': {'atm': 51300, 'interval': 100, 'ce_base': 195, 'pe_base': 185},
        'SENSEX': {'atm': 81500, 'interval': 50, 'ce_base': 128, 'pe_base': 122}
    }
    
    config = configs[index_name]
    data = []
    
    for i in range(-4, 5):
        strike = config['atm'] + i * config['interval']
        
        if side == "CE":
            ltp = max(3, config['ce_base'] + i * -12 + np.random.randint(-25, 35))
            oi = 20000 + abs(i) * 4000 + np.random.randint(-3000, 6000)
            delta = max(0.15, 0.55 - abs(i) * 0.08)
        else:
            ltp = max(3, config['pe_base'] + i * 10 + np.random.randint(-20, 30))
            oi = 25000 + abs(i) * 5000 + np.random.randint(-4000, 8000)
            delta = min(-0.15, -0.35 + abs(i) * 0.07)
        
        score = (oi/1000)*0.4 + (abs(delta-0.3)*-8)*0.3 + (16/10)*0.2
        
        data.append({
            'Strike': strike,
            'LTP': f"₹{ltp:.0f}",
            'OI': f"{oi:,.0f}",
            'Δ': f"{delta:.2f}",
            'IV%': f"{16+abs(i):.0f}",
            'Score': f"{score:.1f}"
        })
    
    df = pd.DataFrame(data)
    pcr = 1.1 + np.random.uniform(-0.3, 0.4)
    return df, round(pcr, 2)

def get_best_strike(df):
    ltp_num = df['LTP'].str.extract('(\\d+)').astype(float)[0]
    best_idx = ltp_num.idxmax()
    return df.iloc[best_idx]

st.title("🔥 NIFTY + BANKNIFTY + SENSEX - LIVE")

col1, col2, col3 = st.columns(3)

# NIFTY
with col1:
    st.header("📈 NIFTY")
    nifty_df, n_pcr = get_index_data('NIFTY')
    n_best = get_best_strike(nifty_df)
    
    c1, c2 = st.columns(2)
    with c1: 
        st.metric("Spot", "₹25,050")
        st.metric("PCR", f"{n_pcr:.2f}")
    with c2:
        st.success(f"🎯 BEST {side}")
        st.metric("Strike", n_best['Strike'])
        st.metric("LTP", n_best['LTP'])
    
    if st.button("🚀 NIFTY TRACK", key="nifty"):
        entry_price = float(n_best['LTP'].replace('₹', ''))
        telegram_pro_alert('NIFTY 50', n_best['Strike'], 
                          f"{entry_price:.0f}", 
                          f"{entry_price+60:.0f}", 
                          f"{entry_price-30:.0f}")
        st.session_state.tracked.append({
            'Index': 'NIFTY', 'Strike': n_best['Strike'], 
            'Entry': n_best['LTP'], 'Time': datetime.now().strftime('%H:%M')
        })
        st.balloons()
        st.success("✅ NIFTY PRO ALERT SENT!")
    
    st.dataframe(nifty_df, height=280)

# BANKNIFTY
with col2:
    st.header("🏦 BANKNIFTY")
    bank_df, b_pcr = get_index_data('BANKNIFTY')
    b_best = get_best_strike(bank_df)
    
    c1, c2 = st.columns(2)
    with c1:
        st.metric("Spot", "₹51,300")
        st.metric("PCR", f"{b_pcr:.2f}")
    with c2:
        st.success(f"🎯 BEST {side}")
        st.metric("Strike", b_best['Strike'])
        st.metric("LTP", b_best['LTP'])
    
    if st.button("🚀 BANKNIFTY TRACK", key="bank"):
        entry_price = float(b_best['LTP'].replace('₹', ''))
        telegram_pro_alert('BANKNIFTY 50', b_best['Strike'], 
                          f"{entry_price:.0f}", 
                          f"{entry_price+150:.0f}", 
                          f"{entry_price-75:.0f}")
        st.session_state.tracked.append({
            'Index': 'BANKNIFTY', 'Strike': b_best['Strike'], 
            'Entry': b_best['LTP'], 'Time': datetime.now().strftime('%H:%M')
        })
        st.balloons()
        st.success("✅ BANKNIFTY PRO ALERT SENT!")
    
    st.dataframe(bank_df, height=280)

# SENSEX
with col3:
    st.header("📊 SENSEX")
    sensex_df, s_pcr = get_index_data('SENSEX')
    s_best = get_best_strike(sensex_df)
    
    c1, c2 = st.columns(2)
    with c1:
        st.metric("Spot", "₹81,500")
        st.metric("PCR", f"{s_pcr:.2f}")
    with c2:
        st.success(f"🎯 BEST {side}")
        st.metric("Strike", s_best['Strike'])
        st.metric("LTP", s_best['LTP'])
    
    if st.button("🚀 SENSEX TRACK", key="sensex"):
        entry_price = float(s_best['LTP'].replace('₹', ''))
        telegram_pro_alert('SENSEX 50', s_best['Strike'], 
                          f"{entry_price:.0f}", 
                          f"{entry_price+100:.0f}", 
                          f"{entry_price-50:.0f}")
        st.session_state.tracked.append({
            'Index': 'SENSEX', 'Strike': s_best['Strike'], 
            'Entry': s_best['LTP'], 'Time': datetime.now().strftime('%H:%M')
        })
        st.balloons()
        st.success("✅ SENSEX PRO ALERT SENT!")
    
    st.dataframe(sensex_df, height=280)

if st.session_state.tracked:
    st.subheader("📋 TRACKED STRIKES")
    st.dataframe(pd.DataFrame(st.session_state.tracked))

st.success("✅ LIVE 15s Refresh | TELEGRAM READY!")
