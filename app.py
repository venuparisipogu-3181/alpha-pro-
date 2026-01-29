import streamlit as st
import pandas as pd
import numpy as np
from dhanhq import dhanhq
import requests
import time
from datetime import datetime

# --- 1. CONFIGURATION & SESSION STATE ---
st.set_page_config(layout="wide", page_title="PRO Dhan Live Monitor")

if 'monitor_active' not in st.session_state:
    st.session_state.monitor_active = False
if 'tracked_trade' not in st.session_state:
    st.session_state.tracked_trade = None

# --- 2. API CONNECTIVITY ---
try:
    CLIENT_ID = st.secrets["DHAN_CLIENT_ID"]
    ACCESS_TOKEN = st.secrets["DHAN_ACCESS_TOKEN"]
    dhan = dhanhq(CLIENT_ID, ACCESS_TOKEN)
except:
    st.error("❌ Secrets Missing! Add DHAN_CLIENT_ID & DHAN_ACCESS_TOKEN in Streamlit Cloud.")
    st.stop()

# --- 3. HELPER FUNCTIONS ---

@st.cache_data(ttl=86400)
def load_dhan_master():
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
    if oi_delta >= 2500: score += 40
    elif oi_delta >= 1500: score += 35
    elif oi_delta >= 800: score += 30
    if 16 <= iv <= 22: score += 20
    elif 14 <= iv <= 25: score += 15
    return round(score, 1)

# --- 4. SIDEBAR & FILTERS ---
st.sidebar.title("🎯 PRO DHAN SCREENER")
side_choice = st.sidebar.selectbox("Side", ["CALL", "PUT"])
opt_type = "CE" if side_choice == "CALL" else "PE"

# --- 5. 3-INDEX SCREENER (LIVE SPOT UPDATED) ---
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
            # 🔥 LIVE SPOT PRICE ఇక్కడ అప్‌డేట్ అవుతుంది
            live_spot = resp.get('underlyingValue', 0)
            st.metric("LIVE SPOT", f"₹{live_spot:,.2f}")
            
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
                    "target": best['last_price'] + 60, "sl": best['last_price'] - 30, 
                    "type": opt_type, "index_id": config['id']
                }
                telegram_pro_alert(f"{name} ENTRY", s_sym, best['last_price'], "LIVE", "START MONITOR", best['PRO_SCORE'])
                st.rerun()
            
            st.dataframe(df[['strike_price', 'last_price', 'oi_change', 'PRO_SCORE']].head(8), use_container_width=True)

# --- 6. LIVE MONITOR + EXIT RULES ---
if st.session_state.monitor_active:
    st.markdown("---")
    st.header("🔴 SINGLE STRIKE LIVE MONITOR")
    trade = st.session_state.tracked_trade
    
    monitor_resp = dhan.option_chain(under_security_id=trade['index_id'], under_exchange_segment="IDX_I")
    
    if monitor_resp['status'] == 'success':
        m_df = pd.DataFrame(monitor_resp['data'])
        # స్ట్రైక్ ప్రైస్ ని సరిగ్గా మ్యాచ్ చేయడం
        strike_to_find = float(trade['symbol'].split()[-2]) if name == "SENSEX" else float(trade['symbol'].split()[-2])
        # కచ్చితమైన రో (row) ని వెతకడం
        m_row = m_df[(m_df['strike_price'] == trade['entry_price'] + (trade['target']-trade['entry_price']-60)) | (m_df['last_price'] > 0)].iloc[0] # Simplified logic for matching
        
        # Real-time data from matching row
        current_ltp = m_row['last_price']
        current_oi_change = m_row['oi_change']
        
        st.subheader(f"🚀 Tracking: {trade['symbol']} | Entry: ₹{trade['entry_price']}")
        
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("LTP", f"₹{current_ltp}", f"{current_ltp - trade['entry_price']:+.2f}")
        m2.metric("Target", f"₹{trade['target']}")
        m3.metric("Stoploss", f"₹{trade['sl']}")
        
        # OI Condition Status
        if current_oi_change < -1000:
            st.error(f"🔴 OI COLLAPSE ({current_oi_change:+}) - EMERGENCY EXIT!")
        elif current_oi_change > 2000:
            st.success(f"🟢 OI BUILDUP ({current_oi_change:+}) - HOLD.")
        else:
            st.info(f"🟡 OI STABLE ({current_oi_change:+})")

        # Exit Buttons
        e1, e2, e3 = st.columns(3)
        with e1:
            if st.button("🎯 TARGET HIT SELL", disabled=(current_ltp < trade['target']), use_container_width=True):
                telegram_pro_alert("TARGET HIT", trade['symbol'], current_ltp, "EXIT", "SELL NOW", 100)
                st.session_state.monitor_active = False
                st.rerun()
        with e2:
            if st.button("🛑 SL HIT SELL", disabled=(current_ltp > trade['sl']), use_container_width=True):
                telegram_pro_alert("SL HIT", trade['symbol'], current_ltp, "EXIT", "SELL NOW", 0)
                st.session_state.monitor_active = False
                st.rerun()
        with e3:
            if st.button("🚨 OI EMERGENCY EXIT", disabled=(current_oi_change > -1000), use_container_width=True):
                telegram_pro_alert("OI EMERGENCY", trade['symbol'], current_ltp, "EXIT", "EMERGENCY SELL", 20)
                st.session_state.monitor_active = False
                st.rerun()

    if st.button("⏹️ STOP MONITOR"):
        st.session_state.monitor_active = False
        st.rerun()

st.info("🔄 Auto-refreshing every 15 seconds...")
time.sleep(15)
st.rerun()
