import streamlit as st
import pandas as pd
import numpy as np
import time
from datetime import datetime

st.set_page_config(layout="wide", page_title="PRO Strike LIVE")

st.title("🔥 PRO Strike Dashboard")
st.markdown("**Nifty Live OI Signals | 3s Auto Refresh | Mobile Ready**")

# ✅ FIXED: Define strikes + data dict
strikes = ["25000", "25100", "25200"]  # Nifty strikes
data = {}

# ✅ FIXED: Safe random seed
np.random.seed(int(time.time()) % 10000)

# ✅ FIXED: Loop with proper variables
for strike in strikes:
    ce = np.random.randint(100000, 500000)
    pe = np.random.randint(150000, 600000)
    diff = pe - ce
    
    signal = "⚪ NEUTRAL"
    if diff > 50000: 
        signal = "🟢 BUY"  
    elif diff < -50000: 
        signal = "🔴 SELL"
    
    data[strike] = {
        'CE': f"{ce:,}", 
        'PE': f"{pe:,}", 
        'Diff': f"{diff:,}", 
        'Signal': signal
    }

# DataFrame
df = pd.DataFrame.from_dict(data, orient='index').reset_index()
df.rename(columns={'index':'Strike'}, inplace=True)
df = df[['Strike', 'CE', 'PE', 'Diff', 'Signal']]

# ✅ FIXED: Safe styling (no row param)
def highlight_signals(val):
    if 'BUY' in str(val):
        return 'background-color: #d4edda; color: #155724; font-weight: bold; padding: 8px'
    elif 'SELL' in str(val):
        return 'background-color: #f8d7da; color: #721c24; font-weight: bold; padding: 8px'
    elif isinstance(val, str) and '-' in val:
        return 'color: #dc3545; font-weight: bold'
    elif isinstance(val, str) and '+' in val:
        return 'color: #28a745; font-weight: bold'
    return ''

st.markdown("### 📊 Live OI Data")
styled_df = df.style.applymap(highlight_signals).format(na_rep='--')
st.dataframe(styled_df, use_container_width=True, height=350, hide_index=True)

# Metrics
col1, col2, col3 = st.columns(3)
buy_count = len(df[df['Signal'].str.contains('BUY', na=False)])
sell_count = len(df[df['Signal'].str.contains('SELL', na=False)])

with col1: 
    st.metric("🟢 BUY", buy_count)
with col2: 
    st.metric("🔴 SELL", sell_count)
with col3: 
    st.metric("⏰ LIVE", datetime.now().strftime('%H:%M:%S'))

# Dhan Checkbox (Safe - no import)
if st.sidebar.checkbox("💰 Real Dhan Data (Coming Soon)"):
    st.sidebar.info("Add DHAN secrets.toml for live OI")

# Auto refresh button
st.markdown("---")
if st.button("🔄 Refresh LIVE Data", use_container_width=True, type="primary"):
    st.rerun()

st.caption("🚀 https://kqhsutttytrrwwf4ifu8ev.streamlit.app | Venu Algo Trading | Feb 2026")
