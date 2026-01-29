import streamlit as st
import pandas as pd
import numpy as np
from dhanhq import dhanhq
import requests
import time
from datetime import datetime

# --- 1. PAGE SETUP & SESSION STATE ---
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
    st.error("❌ Secrets Error: Please configure DHAN_CLIENT_ID and DHAN_ACCESS_TOKEN in Streamlit Cloud.")
    st.stop()

# --- 3. CORE FUNCTIONS ---

@st.cache_data(ttl=86400)
def load_dhan_master():
    """Fetches Security IDs for tracking"""
    url = "https://images.dhan.co/api-data/api-scrip-master.csv"
    try:
        return pd.read_csv(url)
    except:
        return pd.DataFrame()

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
    """Calculates Put-Call Ratio for the index"""
    ce_oi = df_all[df_all['type'] == 'CE']['oi'].sum()
    pe_oi = df_all[df_all['type'] == 'PE']['oi'].sum()
    return round(pe_oi / ce_oi, 2) if ce_oi > 0 else 1.0

def calculate_pro_score(row, pcr_val, side):
    """Your Original PRO Scoring Logic"""
    score = 0
    oi_delta = row.get('oi_change', 0)
    iv = row.get('iv', 0)
    
    # OI Change Points
    if oi_delta >= 2500: score += 40
    elif oi_delta >= 1500: score += 35
    elif oi_delta >= 800: score += 30
    
    # IV Points
    if 16 <= iv <= 22: score += 20
    elif 14 <= iv <= 25: score += 15
    
    # PCR Bonus
    if side == "CALL" and pcr_val <= 0.90: score += 10
    elif side == "PUT" and pcr_val >= 1.10: score += 10
    
    return round(score, 1)

def telegram_pro_alert(title, strike, price, status, action, score):
    token = st.secrets.get("TELEGRAM_BOT_TOKEN")
    chat_id = st.secrets.get("TELEGRAM_CHAT_ID")
    if token and chat_id:
        msg = f"🚨 {title}\n{strike}\n\n💰 LTP: ₹{price}\n🎯 Action: {action}\n📊 Status: {status}\n⭐ Score: {score}"
        try: requests.post(f"https://api.telegram.org/bot{token}/sendMessage", data={"chat_id": chat_id, "text": msg})
        except: pass

# --- 4. SIDEBAR ---
st.sidebar.title("🎯 PRO DHAN SCREENER")
side_choice = st.sidebar.selectbox("Select Side", ["CALL", "PUT"])
opt_type = "CE" if side_choice == "CALL" else "PE"

# --- 5. 3-INDEX LIVE SCREENER ---
st.header("🔥 PRO 3-INDEX LIVE SCREENER (DHAN)")
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
            resp = dhan.option_chain(under_security_id=int(config['id']), under_exchange_segment=config['seg'])
            
            if resp and resp.get('status') == 'success':
                full_df = pd.DataFrame(resp['data'])
                pcr_val = calculate_pcr(full_df)
                live_spot = resp.get('underlyingValue', 0)
                
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
                            "type": opt_type, "index_id": config['id'], "strike": best['strike_price']
                        }
                        telegram_pro_alert(f"{name} ENTRY", s_sym, best['last_price'], "LIVE", "START MONITOR", best['PRO_SCORE'])
                        st.rerun()
                    
                    st.dataframe(df[['strike_price', 'last_price', 'oi_change', 'PRO_SCORE']].head(8), use_container_width=True)
            else:
                st.error("API Limit reached or Market Closed")
        except Exception as e:
            st.error(f"Error: {e}")

# --- 6. LIVE MONITOR + EXIT RULES ---
if st.session_state.monitor_active:
    st.markdown("---")
    st.header("🔴 SINGLE STRIKE LIVE MONITOR")
    trade = st.session_state.tracked_trade
    
    try:
        mon_resp = dhan.option_chain(under_security_id=int(trade['index_id']), under_exchange_segment="IDX_I")
        if mon_resp and mon_resp.get('status') == 'success':
            m_df = pd.DataFrame(mon_resp['data'])
            m_row = m_df[(m_df['strike_price'] == float(trade['strike'])) & (m_df['type'] == trade['type'])].iloc[0]
            
            cur_ltp = m_row['last_price']
            cur_oi_chg = m_row['oi_change']
            
            st.subheader(f"🚀 Tracking: {trade['symbol']} | Entry: ₹{trade['entry_price']}")
            
            met1, met2, met3 = st.columns(3)
            met1.metric("LTP", f"₹{cur_ltp}", f"{cur_ltp - trade['entry_price']:+.2f}")
            met2.metric("Target", f"₹{trade['target']}")
            met3.metric("Stoploss", f"₹{trade['sl']}")
            
            # OI Alerts
            if cur_oi_chg < -1000: st.error(f"🔴 OI COLLAPSE ({cur_oi_chg:+})")
            elif cur_oi_chg > 2000: st.success(f"🟢 OI BUILDUP ({cur_oi_chg:+})")

            # Exit Buttons
            e1, e2, e3 = st.columns(3)
            with e1:
                if st.button("🎯 TARGET HIT", disabled=(cur_ltp < trade['target']), use_container_width=True):
                    telegram_pro_alert("TARGET REACHED", trade['symbol'], cur_ltp, "EXIT", "SELL NOW", 100)
                    st.session_state.monitor_active = False
                    st.rerun()
            with e2:
                if st.button("🛑 SL HIT", disabled=(cur_ltp > trade['sl']), use_container_width=True):
                    telegram_pro_alert("STOPLOSS HIT", trade['symbol'], cur_ltp, "EXIT", "SELL NOW", 0)
                    st.session_state.monitor_active = False
                    st.rerun()
            with e3:
                if st.button("🚨 OI EXIT", disabled=(cur_oi_chg > -1000), use_container_width=True):
                    telegram_pro_alert("OI EMERGENCY", trade['symbol'], cur_ltp, "EXIT", "EMERGENCY SELL", 20)
                    st.session_state.monitor_active = False
                    st.rerun()
    except Exception as e:
        st.warning("Fetching live updates...")

    if st.button("⏹️ STOP MONITOR"):
        st.session_state.monitor_active = False
        st.rerun()

st.info("🔄 Auto-refreshing every 15 seconds...")
time.sleep(15)
st.rerun()
