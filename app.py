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
    st.error("❌ Secrets Error!")
    st.stop()

# --- 2. LOGIC ---
def get_safe_option_chain(idx_id, idx_seg):
    """ఎక్స్‌పైరీ ఎర్రర్ రాకుండా హ్యాండిల్ చేసే ఫంక్షన్"""
    try:
        # పద్ధతి 1: నేరుగా ఆప్షన్ చైన్ ట్రై చేయడం
        resp = dhan.option_chain(under_security_id=int(idx_id), under_exchange_segment=idx_seg)
        return resp
    except TypeError:
        # పద్ధతి 2: ఒకవేళ expiry అడిగితే (కొత్త SDK వెర్షన్)
        # ఇక్కడ మనం ఏ డేట్ ఇవ్వాలో తెలియదు కాబట్టి, ప్రస్తుతానికి ఎర్రర్ మెసేజ్ చూపిస్తుంది
        return {"status": "error", "remarks": "expiry_required"}

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
        # ఇక్కడ మనం వెర్షన్ సంబంధం లేకుండా డేటా తెచ్చే ప్రయత్నం చేస్తున్నాం
        try:
            # Dhan SDK లో వెర్షన్ బట్టి ఫంక్షన్ మారుతుంది
            # ఒకవేళ get_expiry_dates లేకపోతే నేరుగా ఆప్షన్ చైన్ వాడుతున్నాం
            resp = dhan.option_chain(under_security_id=int(conf['id']), under_exchange_segment=conf['seg'])
            
            if resp and resp.get('status') == 'success':
                data = pd.DataFrame(resp['data'])
                spot = resp.get('underlyingValue', 0)
                st.metric("SPOT", f"₹{spot}")
                
                df_side = data[data['type'] == opt_type].copy()
                st.dataframe(df_side[['strike_price', 'last_price', 'oi_change']].head(5))
            else:
                st.warning(f"{name}: No Live Data (Market Closed?)")
        except AttributeError:
            st.error(f"❌ SDK Version Issue in {name}. Please update requirements.txt")

# --- 4. REFRESH ---
st.info("🔄 Auto-refreshing...")
time.sleep(15)
st.rerun()
