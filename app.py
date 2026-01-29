import streamlit as st
import pandas as pd
import numpy as np
from dhanhq import dhanhq
import requests
import time

# --- 1. PAGE SETUP & SESSION STATE ---
st.set_page_config(layout="wide", page_title="PRO Dhan Live Monitor", page_icon="🏹")

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
    st.error("❌ Secrets missing! Add DHAN_CLIENT_ID & DHAN_ACCESS_TOKEN in Streamlit Cloud.")
    st.stop()

# --- 3. LOGIC FUNCTIONS ---

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
    
    if 16 <= iv <= 22: score += 20
    
    if side == "CALL" and pcr_val <= 0.90: score += 10
    elif side == "PUT" and pcr_val >= 1.10: score += 10
    
    return round(score, 1)

def telegram_pro_alert(title, strike, price, status, action, score):
    token = st.secrets.get("TELEGRAM_BOT_TOKEN")
    chat_id = st.secrets.get("TELEGRAM_CHAT_ID")
    if token and chat_id:
        msg = f"🚨 {title}\n{strike}\n💰 LTP: ₹{price}\n📊 Score: {score}"
        try: requests.post(f"https://api.telegram.org/bot{token}/sendMessage", data={"chat_id": chat_id, "text": msg})
        except: pass

# --- 4. 3-INDEX LIVE SCREENER ---
st.header("🔥 PRO 3-INDEX LIVE MONITOR")
indices = {
    "NIFTY": {"id": 13, "seg": "IDX_I"},
    "BANKNIFTY": {"id": 25, "seg": "IDX_I"},
    "SENSEX": {"id": 1, "seg": "IDX_I"}
}

side_choice = st.sidebar.selectbox("Select Side", ["CALL", "PUT"])
opt_type = "CE" if side_choice == "CALL" else "PE"

col_idx = st.columns(3)

for i, (name, config) in enumerate(indices.items()):
    with col_idx[i]:
        st.subheader(f"📈 {name}")
        try:
            # ధన్ నుండి ఎక్స్‌పైరీ లిస్ట్‌ని పొందడం
            # గమనిక: SDK వెర్షన్ బట్టి 'get_expiry_dates' లేదా 'expiry_list' మారుతుంది
            expiry_resp = dhan.get_expiry_dates(under_security_id=int(config['id']), under_exchange_segment=config['seg'])
            
            if expiry_resp and expiry_resp.get('status') == 'success':
                current_expiry = expiry_resp['data'][0]
                
                # ఎక్స్‌పైరీతో ఆప్షన్ చైన్ పిలవడం
                resp = dhan.option_chain(
                    under_security_id=int(config['id']), 
                    under_exchange_segment=config['seg'],
                    expiry=current_expiry
                )
                
                if resp and resp.get('status') == 'success':
                    full_df = pd.DataFrame(resp['data'])
                    pcr_val = calculate_pcr(full_df)
                    live_spot = resp.get('underlyingValue', 0)
                    
                    st.write(f"📅 {current_expiry}")
                    m1, m2 = st.columns(2)
                    m1.metric("SPOT", f"₹{live_spot:,.2f}")
                    m2.metric("PCR", f"{pcr_val}")

                    df = full_df[full_df['type'] == opt_type].copy()
                    if not df.empty:
                        df['PRO_SCORE'] = df.apply(lambda x: calculate_pro_score(x, pcr_val, side_choice), axis=1)
                        df = df.sort_values(by='PRO_SCORE', ascending=False)
                        best = df.iloc[0]
                        
                        st.success(f"🎯 {best['strike_price']} [{best['PRO_SCORE']}/100]")
                        
                        if st.button(f"🚀 TRACK {name}", key=f"btn_{name}"):
                            telegram_pro_alert(f"{name} ENTRY", f"{name} {best['strike_price']} {opt_type}", best['last_price'], "LIVE", "START", best['PRO_SCORE'])
                            st.toast(f"Tracking {name} Started!")
                        
                        st.dataframe(df[['strike_price', 'last_price', 'oi_change', 'PRO_SCORE']].head(8), use_container_width=True)
            else:
                st.error(f"{name}: No Expiry Data")
        except Exception as e:
            st.error(f"{name} Error: {e}")

# --- 5. REFRESH ---
st.info("🔄 Auto-refreshing in 15 seconds...")
time.sleep(15)
st.rerun()
