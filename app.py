import streamlit as st
import pandas as pd
import numpy as np
from dhanhq import dhanhq
import requests
import time
from datetime import datetime

# --- 1. CONFIGURATION & SESSION STATE ---
st.set_page_config(layout="wide", page_title="PRO Dhan Strike Monitor")

if 'monitor_active' not in st.session_state:
    st.session_state.monitor_active = False
if 'tracked_trade' not in st.session_state:
    st.session_state.tracked_trade = None

# --- 2. API CONNECTIVITY (GITHUB SECRETS) ---
try:
    CLIENT_ID = st.secrets["DHAN_CLIENT_ID"]
    ACCESS_TOKEN = st.secrets["DHAN_ACCESS_TOKEN"]
    dhan = dhanhq(CLIENT_ID, ACCESS_TOKEN)
except:
    st.error("❌ Secrets Missing! Add DHAN_CLIENT_ID & DHAN_ACCESS_TOKEN in Streamlit Cloud Settings.")
    st.stop()

# --- 3. HELPER FUNCTIONS ---

@st.cache_data(ttl=86400)
def load_dhan_master():
    """Dhan Master CSV నుండి డేటా లోడ్ చేస్తుంది (ID Finder కోసం)"""
    url = "https://images.dhan.co/api-data/api-scrip-master.csv"
    return pd.read_csv(url)

def get_security_id(index_name, strike, option_type):
    master_df = load_dhan_master()
    segment = "NSE_FNO" if index_name != "SENSEX" else "BSE_FNO"
    opt = "CE" if option_type == "CALL" else "PE"
    try:
        match = master_df[
            (master_df['SEM_EXCH_SEGMENT'] == segment) & 
            (master_df['SEM_STRIKE_PRICE'] == float(strike)) & 
            (master_df['SEM_OPTION_TYPE'] == opt) &
            (master_df['SEM_TRADING_SYMBOL'].str.contains(index_name))
        ]
        if not match.empty:
            return match.iloc[0]['SEM_SMST_SECURITY_ID'], match.iloc[0]['SEM_TRADING_SYMBOL']
    except: return None, None
    return None, None

def telegram_pro_alert(title, strike, price, status, action, score):
    token = st.secrets.get("TELEGRAM_BOT_TOKEN")
    chat_id = st.secrets.get("TELEGRAM_CHAT_ID")
    if token and chat_id:
        msg = f"🚨 {title}\n{strike}\n\n💰 LTP: ₹{price}\n🎯 Action: {action}\n📊 Status: {status}\n⭐ Score: {score}"
        requests.post(f"https://api.telegram.org/bot{token}/sendMessage", data={"chat_id": chat_id, "text": msg})

def calculate_pro_score(row):
    score = 0
    oi_delta = row.get('oi_change', 0)
    iv = row.get('iv', 0)
    
    # OI Logic
    if oi_delta >= 2500: score += 40
    elif oi_delta >= 1500: score += 35
    elif oi_delta >= 800: score += 30
    
    # IV Logic
    if 16 <= iv <= 22: score += 20
    elif 14 <= iv <= 25: score += 15
    
    return round(score, 1)

# --- 4. SIDEBAR CONTROLS ---
st.sidebar.title("🎯 PRO DHAN SCREENER")
side_choice = st.sidebar.selectbox("Side", ["CALL", "PUT"])
opt_type = "CE" if side_choice == "CALL" else "PE"

# --- 5. 3-INDEX SCREENER ---
st.header("🔥 PRO 3-INDEX LIVE SCREENER")
indices = {
    "NIFTY": {"id": "13", "seg": "IDX_I"},
    "BANKNIFTY": {"id": "25", "seg": "IDX_I"},
    "SENSEX": {"id": "1", "seg": "IDX_I"}
}

col_idx = st.columns(3)
for i, (name, config) in enumerate(indices.items()):
    with col_idx[i]:
        st.subheader(f"📈 {name}")
        resp = dhan.option_chain(under_security_id=config['id'], under_exchange_segment=config['seg'])
        
        if resp['status'] == 'success':
            df = pd.DataFrame(resp['data'])
            df = df[df['type'] == opt_type].copy()
            df['PRO_SCORE'] = df.apply(calculate_pro_score, axis=1)
            df = df.sort_values(by='PRO_SCORE', ascending=False)
            
            best = df.iloc[0]
            st.success(f"🎯 BEST: {best['strike_price']} [{best['PRO_SCORE']}/100]")
            st.metric("LTP", f"₹{best['last_price']}")
            
            if st.button(f"🚀 TRACK {name}", key=f"btn_{name}"):
                s_id, s_sym = get_security_id(name, best['strike_price'], side_choice)
                st.session_state.monitor_active = True
                st.session_state.tracked_trade = {
                    "sec_id": s_id, "symbol": s_sym, "entry_price": best['last_price'],
                    "target": best['last_price'] + 60, "sl": best['last_price'] - 30, "type": opt_type
                }
                telegram_pro_alert(f"{name} ENTRY", s_sym, best['last_price'], "LIVE", "START MONITOR", best['PRO_SCORE'])
                st.rerun()
            
            st.dataframe(df[['strike_price', 'last_price', 'oi_change', 'PRO_SCORE']].head(8))

# --- 6. LIVE MONITOR + EXIT RULES ---
st.markdown("---")
st.header("🔴 SINGLE STRIKE LIVE MONITOR + TRIPLE EXIT")

if st.session_state.monitor_active:
    trade = st.session_state.tracked_trade
    
    # Fetch Real-time LTP for the tracked security
    # Note: Using option_chain again to get current LTP & OI for simplicity
    monitor_resp = dhan.option_chain(under_security_id=indices[trade['symbol'].split()[0]]['id'], under_exchange_segment="IDX_I")
    
    if monitor_resp['status'] == 'success':
        m_df = pd.DataFrame(monitor_resp['data'])
        m_row = m_df[(m_df['strike_price'] == float(trade['symbol'].split()[1])) & (m_df['type'] == trade['type'])].iloc[0]
        
        live_ltp = m_row['last_price']
        live_oi_change = m_row['oi_change']
        
        st.subheader(f"🚀 Tracking: {trade['symbol']} | Entry: ₹{trade['entry_price']}")
        
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("LTP", f"₹{live_ltp}", f"{live_ltp - trade['entry_price']:+.2f}")
        m2.metric("Target", f"₹{trade['target']}")
        m3.metric("Stoploss", f"₹{trade['sl']}")
        
        # OI Condition Status
        if live_oi_change < -1000:
            st.error(f"🔴 OI COLLAPSE ({live_oi_change:+})")
        elif live_oi_change > 2000:
            st.success(f"🟢 OI BUILDUP ({live_oi_change:+})")
        else:
            st.info(f"🟡 OI STABLE ({live_oi_change:+})")

        # Exit Buttons
        e1, e2, e3 = st.columns(3)
        with e1:
            if st.button("🎯 TARGET HIT SELL", disabled=(live_ltp < trade['target']), use_container_width=True):
                telegram_pro_alert("TARGET HIT", trade['symbol'], live_ltp, "EXIT", "SELL NOW", 100)
                st.session_state.monitor_active = False
                st.success("Target Exit Sent!")
        with e2:
            if st.button("🛑 SL HIT SELL", disabled=(live_ltp > trade['sl']), use_container_width=True):
                telegram_pro_alert("SL HIT", trade['symbol'], live_ltp, "EXIT", "SELL NOW", 0)
                st.session_state.monitor_active = False
                st.error("Stoploss Exit Sent!")
        with e3:
            if st.button("🚨 OI EMERGENCY EXIT", disabled=(live_oi_change > -1000), use_container_width=True):
                telegram_pro_alert("OI EMERGENCY", trade['symbol'], live_ltp, "EXIT", "EMERGENCY SELL", 20)
                st.session_state.monitor_active = False
                st.warning("OI Emergency Exit Sent!")

    if st.button("⏹️ STOP MONITOR"):
        st.session_state.monitor_active = False
        st.rerun()

st.info("🔄 Auto-refreshing every 15 seconds...")
time.sleep(15)
st.rerun()
