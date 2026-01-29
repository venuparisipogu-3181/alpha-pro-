import streamlit as st
import pandas as pd
import numpy as np
from dhanhq import dhanhq
import requests
import time

# --- 1. SETUP ---
st.set_page_config(layout="wide", page_title="PRO Dhan Live", page_icon="🏹")

try:
    client_id = st.secrets["DHAN_CLIENT_ID"]
    access_token = st.secrets["DHAN_ACCESS_TOKEN"]
    dhan = dhanhq(client_id, access_token)
except Exception as e:
    st.error("❌ API Keys missing in Secrets!")
    st.stop()

# --- 2. UNIVERSAL EXPIRY FINDER (వెర్షన్ ఏదైనా పనిచేస్తుంది) ---
def fetch_expiry(idx_id, idx_seg):
    # పద్ధతి 1: కొత్త SDK వెర్షన్ (1.3.0+)
    try:
        exp_data = dhan.get_expiry(under_security_id=int(idx_id), under_exchange_segment=idx_seg)
        if exp_data and exp_data.get('status') == 'success':
            return exp_data['data'][0]
    except AttributeError:
        pass

    # పద్ధతి 2: పాత SDK వెర్షన్ (1.1.0 - 1.2.0)
    try:
        exp_data = dhan.get_expiry_dates(under_security_id=int(idx_id), under_exchange_segment=idx_seg)
        if exp_data and exp_data.get('status') == 'success':
            return exp_data['data'][0]
    except AttributeError:
        pass
    
    return None

# --- 3. UI SCREENER ---
st.header("🏹 PRO 3-INDEX LIVE MONITOR")
indices = {
    "NIFTY": {"id": 13, "seg": "IDX_I"},
    "BANKNIFTY": {"id": 25, "seg": "IDX_I"},
    "SENSEX": {"id": 1, "seg": "IDX_I"}
}

side = st.sidebar.selectbox("Side", ["CALL", "PUT"])
opt_type = "CE" if side == "CALL" else "PE"

cols = st.columns(3)
for i, (name, conf) in enumerate(indices.items()):
    with cols[i]:
        st.subheader(f"📈 {name}")
        
        # ఎక్స్‌పైరీని పట్టుకోవడం
        current_expiry = fetch_expiry(conf['id'], conf['seg'])
        
        if current_expiry:
            try:
                resp = dhan.option_chain(
                    under_security_id=int(conf['id']), 
                    under_exchange_segment=conf['seg'],
                    expiry=current_expiry
                )
                
                if resp and resp.get('status') == 'success':
                    data = pd.DataFrame(resp['data'])
                    spot = resp.get('underlyingValue', 0)
                    st.write(f"📅 Expiry: {current_expiry}")
                    st.metric("SPOT", f"₹{spot}")
                    
                    df_side = data[data['type'] == opt_type].copy()
                    st.dataframe(df_side[['strike_price', 'last_price', 'oi_change']].head(8), use_container_width=True)
                else:
                    st.warning(f"{name}: No Data found.")
            except Exception as e:
                st.error(f"Chain Error: {e}")
        else:
            st.error(f"❌ Could not fetch Expiry for {name}")

# --- 4. REFRESH ---
st.info("🔄 Auto-refreshing every 15 seconds...")
time.sleep(15)
st.rerun()
