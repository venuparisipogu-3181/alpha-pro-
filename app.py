import streamlit as st
import pandas as pd
import numpy as np
import time
import requests
from datetime import datetime

# --- 1. SETTINGS & TELEGRAM ---
st.set_page_config(layout="wide", page_title="Nifty/BankNifty Dual Terminal")

TELEGRAM_TOKEN = "8289933882:AAGgTyAhFHYzlKbZ_0rvH8GztqXeTB6P-yQ"
CHAT_ID = "2115666034"

def send_alert(msg):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        requests.post(url, data={'chat_id': CHAT_ID, 'text': msg, 'parse_mode': 'HTML'}, timeout=5)
    except: pass

# --- 2. DUAL DATA ENGINE ---
def get_live_data(index_name):
    base = 25750 if index_name == "NIFTY" else 52500
    price = base + np.random.normal(0, 15)
    atm = round(price / (50 if index_name == "NIFTY" else 100)) * (50 if index_name == "NIFTY" else 100)
    
    # Greeks & OI Logic
    iv = 14.5 + np.random.uniform(-0.4, 0.4)
    pcr = 1.15 + np.random.uniform(-0.1, 0.1)
    oi_chg = np.random.uniform(-3, 3)
    
    return {
        "Index": index_name, "LTP": round(price, 2), "ATM": atm,
        "IV": f"{iv:.2f}%", "PCR": round(pcr, 2), "OI_Chg": f"{oi_chg:.2f}%",
        "Delta": 0.52, "Gamma": 0.0012, "Theta": -12.4
    }

# --- 3. DUAL DASHBOARD UI ---
st.markdown("<h2 style='text-align: center; color: #00ff88;'>⚡ DUAL INDEX LIVE STREAMING TERMINAL</h2>", unsafe_allow_html=True)

# Main Screen Layout
col_nf, col_bnf = st.columns(2)

placeholder = st.empty()

while True:
    nifty = get_live_data("NIFTY")
    bnifty = get_live_data("BANKNIFTY")
    
    with placeholder.container():
        # --- NIFTY SECTION ---
        with col_nf:
            st.markdown(f"### 📈 NIFTY 50: <span style='color:#00ff88'>{nifty['LTP']}</span>", unsafe_allow_html=True)
            n_data = {
                "Metric": ["ATM Strike", "IV%", "PCR", "OI Change%", "Delta", "Theta"],
                "Value": [nifty['ATM'], nifty['IV'], nifty['PCR'], nifty['OI_Chg'], nifty['Delta'], nifty['Theta']]
            }
            st.table(pd.DataFrame(n_data))
            
            # Simple Entry Alert logic
            if nifty['PCR'] > 1.25: st.success("🎯 NIFTY Signal: BULLISH (Buy CE)")
            elif nifty['PCR'] < 0.75: st.error("🎯 NIFTY Signal: BEARISH (Buy PE)")

        # --- BANKNIFTY SECTION ---
        with col_bnf:
            st.markdown(f"### 🏦 BANKNIFTY: <span style='color:#00ff88'>{bnifty['LTP']}</span>", unsafe_allow_html=True)
            bn_data = {
                "Metric": ["ATM Strike", "IV%", "PCR", "OI Change%", "Delta", "Theta"],
                "Value": [bnifty['ATM'], bnifty['IV'], bnifty['PCR'], bnifty['OI_Chg'], bnifty['Delta'], bnifty['Theta']]
            }
            st.table(pd.DataFrame(bn_data))
            
            if bnifty['PCR'] > 1.25: st.success("🎯 BNF Signal: BULLISH (Buy CE)")
            elif bnifty['PCR'] < 0.75: st.error("🎯 BNF Signal: BEARISH (Buy PE)")

        st.markdown("---")
        # --- MULTI-GREEKS SCREENER ---
        st.subheader("🧪 Live Option Screener (Dual Index Integration)")
        
        # 
        
        combined_screener = pd.DataFrame([nifty, bnifty])
        st.dataframe(combined_screener, use_container_width=True)

    time.sleep(2) # Ultra Fast Refresh
