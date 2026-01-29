import streamlit as st
import pandas as pd
import numpy as np
from dhanhq import dhanhq
import requests
import time
from datetime import datetime

# --- 1. PAGE SETUP ---
st.set_page_config(layout="wide", page_title="PRO Dhan Live Monitor", page_icon="🎯")

if 'monitor_active' not in st.session_state:
    st.session_state.monitor_active = False
if 'tracked_trade' not in st.session_state:
    st.session_state.tracked_trade = None

# --- 2. API CONNECTION ---
try:
    CLIENT_ID = st.secrets["DHAN_CLIENT_ID"]
    ACCESS_TOKEN = st.secrets["DHAN_ACCESS_TOKEN"]
    dhan = dhanhq(CLIENT_ID, ACCESS_TOKEN)
except Exception as e:
    st.error("❌ Secrets Missing! Add DHAN_CLIENT_ID & DHAN_ACCESS_TOKEN in Streamlit Cloud.")
    st.stop()

# --- 3. HELPER FUNCTIONS ---

@st.cache_data(ttl=86400)
def load_dhan_master():
    url = "https://images.dhan.co/api-data/api-scrip-master.csv"
    try: return pd.read_csv(url)
    except: return pd.DataFrame()

def get_security_id(index_name, strike, option_type):
    master_df = load_dhan_master()
    if master_df.empty: return None, None
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

def calculate_pcr(df_all):
    ce_oi = df_all[df_all['type'] == 'CE']['oi'].sum()
    pe_oi = df_all[df_all['type'] == 'PE']['oi'].sum()
    return round(pe_oi / ce_oi, 2) if ce_oi > 0 else 1.0

def calculate_pro_score(row, pcr_val, side):
    score = 0
    oi_delta = row.get('oi_change', 0)
    iv = row.get('iv', 0)
    if oi_delta >= 2500: score += 40
    elif oi_delta >= 1500: score += 35
    elif oi_delta >= 800: score += 30
    if 16 <= iv <= 22: score += 20
    elif 14 <= iv <= 25: score += 15
    if side == "CALL" and pcr_val <= 0.90: score += 10
    elif side == "PUT" and pcr_val >= 1.10: score += 10
    return round(score, 1)

def telegram_pro_alert(title, strike, price, status, action, score):
    token = st.secrets.get("TELEGRAM_BOT_TOKEN")
    chat_id = st.secrets.get("TELEGRAM_CHAT_ID")
    if token and chat_id:
        msg = f"🚨 {title}\n{strike}\n💰 LTP: ₹{price}\n🎯 Action: {action}\n📊 Score: {score}"
        try: requests.post(f"https://api.telegram.org/bot{token}/sendMessage", data={"chat_id": chat_id, "text": msg})
        except: pass

# --- 4. SIDEBAR ---
st.sidebar.title("🎯 PRO SCREENER")
side_choice = st.sidebar.selectbox("Select Side", ["CALL", "PUT"])
opt_type = "CE" if side_choice == "CALL" else "PE"

# --- 5. 3-INDEX LIVE SCREENER ---
st.header("🔥 PRO 3-INDEX LIVE SCREENER")
indices = {
    "NIFTY": {"id": 13, "seg": "IDX_I"},
    "BANKNIFTY": {"id": 25, "seg": "IDX_I"},
    "SENSEX": {"id": 1, "seg": "IDX_I"}
}

col_idx = st.columns(3)
for i, (name, config) in enumerate(indices.items()):
    with col_idx[i]:
        st.subheader(f"📈 {name}")
        try:
            # 1. Fetch Expiry Dates first
            expiry_data = dhan.get_expiry_dates(under_security_id=int(config['id']), under_exchange_segment=config['seg'])
            
            if expiry_data and expiry_data.get('status') == 'success':
                current_expiry = expiry_data['data'][0] # మొదటి ఎక్స్‌పైరీ తీసుకుంటుంది
                
                # 2. Fetch Option Chain with Expiry
                resp = dhan.option_chain(
                    under_security_id=int(config['id']), 
                    under_exchange_segment=config['seg'],
                    expiry=current_expiry
                )
                
                if resp and resp.get('status') == 'success':
                    full_df = pd.DataFrame(resp['data'])
                    pcr_val = calculate_pcr(full_df)
                    live_spot = resp.get('underlyingValue', 0)
                    
                    st.write(f"📅 Expiry: {current_expiry}")
                    m1, m2 = st.columns(2)
                    m1.metric("SPOT", f"₹{live_spot:,.2f}")
                    m2.metric("PCR", f"{pcr_val}")

                    df = full_df[full_df['type'] == opt_type].copy()
                    if not df.empty:
                        df['PRO_SCORE'] = df.apply(lambda x: calculate_pro_score(x, pcr_val, side_choice), axis=1)
                        df = df.sort_values(by='PRO_SCORE', ascending=False)
                        best = df.iloc[0]
                        
                        st.success(f"🎯 BEST: {best['strike_price']} [{best['PRO_SCORE']}/100]")
                        
                        if st.button(f"🚀 TRACK {name}", key=f"btn_{name}"):
                            s_id, s_sym = get_security_id(name, best['strike_price'], side_choice)
                            st.session_state.monitor_active = True
                            st.session_state.tracked_trade = {
                                "sec_id": s_id, "symbol": s_sym, "entry_price": best['last_price'],
                                "target": best['last_price'] + 60, "sl": best['last_price'] - 30, 
                                "type": opt_type, "index_id": config['id'], "strike": best['strike_price'], "expiry": current_expiry
                            }
                            telegram_pro_alert(f"{name} ENTRY", s_sym, best['last_price'], "LIVE", "START", best['PRO_SCORE'])
                            st.rerun()
                        
                        st.dataframe(df[['strike_price', 'last_price', 'oi_change', 'PRO_SCORE']].head(8), use_container_width=True)
            else:
                st.error(f"Could not fetch expiry for {name}")
        except Exception as e:
            st.error(f"Error: {e}")

# --- 6. LIVE MONITOR ---
if st.session_state.monitor_active:
    st.markdown("---")
    st.header("🔴 LIVE TRACKING")
    t = st.session_state.tracked_trade
    try:
        mon_resp = dhan.option_chain(under_security_id=int(t['index_id']), under_exchange_segment="IDX_I", expiry=t['expiry'])
        if mon_resp and mon_resp.get('status') == 'success':
            m_df = pd.DataFrame(mon_resp['data'])
            m_row = m_df[(m_df['strike_price'] == float(t['strike'])) & (m_df['type'] == t['type'])].iloc[0]
            
            cur_ltp = m_row['last_price']
            cur_oi = m_row['oi_change']
            
            st.subheader(f"🚀 {t['symbol']} | Entry: ₹{t['entry_price']}")
            met1, met2, met3 = st.columns(3)
            met1.metric("LTP", f"₹{cur_ltp}", f"{cur_ltp - t['entry_price']:+.2f}")
            met2.metric("Target", f"₹{t['target']}")
            met3.metric("SL", f"₹{t['sl']}")

            if st.button("⏹️ STOP MONITOR"):
                st.session_state.monitor_active = False
                st.rerun()
    except: st.warning("Refreshing data...")

st.info("🔄 Auto-refreshing in 15s...")
time.sleep(15)
st.rerun()
