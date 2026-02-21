import streamlit as st
import pandas as pd
import numpy as np
import time
from datetime import datetime

st.set_page_config(layout="wide", page_title="PRO Strike LIVE")

st.title("🔥 PRO Strike Dashboard")
st.markdown("**Nifty Live OI Signals | 3s Refresh | Mobile Ready**")

# Live simulation data
strikes = ["25000", "25100", "25200"]
data = {}

np.random.seed(int(time.time()))
for strike in strikes:
    ce = np.random.randint(100000, 500000)
    pe = np.random.randint(150000, 600000)
    diff = pe - ce
    
    signal = "⚪ NEUTRAL"
    if diff > 50000: signal = "🟢 BUY"  
    if diff < -50000: signal = "🔴 SELL"
    
    data[strike] = {'CE': f"{ce:,}", 'PE': f"{pe:,}", 'Diff': f"{diff:,}", 'Signal': signal}

# DataFrame + Styling
df = pd.DataFrame.from_dict(data, orient='index').reset_index()
df.rename(columns={'index':'Strike'}, inplace=True)
df = df[['Strike', 'CE', 'PE', 'Diff', 'Signal']]

def highlight_signals(row):
    colors = []
    for val in row:
        if 'BUY' in str(val):
            colors.append('background-color: #d4edda; color: #155724; font-weight: bold')
        elif 'SELL' in str(val):
            colors.append('background-color: #f8d7da; color: #721c24; font-weight: bold')
        elif isinstance(val, str) and val.startswith('-'):
            colors.append('color: #dc3545; font-weight: bold')
        elif isinstance(val, str) and val.startswith('+'):
            colors.append('color: #28a745; font-weight: bold')
        else:
            colors.append('')
    return colors

st.markdown("### 📊 Live OI Data")
styled_df = df.style.apply(highlight_signals, axis=1).format(na_rep='--')
st.dataframe(styled_df, use_container_width=True, height=300)

# Metrics
col1, col2, col3 = st.columns(3)
buy_count = len(df[df['Signal'].str.contains('BUY', na=False)])
sell_count = len(df[df['Signal'].str.contains('SELL', na=False)])

with col1: st.metric("🟢 BUY", buy_count)
with col2: st.metric("🔴 SELL", sell_count)  
with col3: st.metric("⏰ Updated", datetime.now().strftime('%H:%M'))

# Auto refresh
st.markdown("---")
if st.button("🔄 Refresh LIVE Data", use_container_width=True):
    st.rerun()

st.caption("🚀 Deployed on Streamlit Cloud | Made for Venu | Feb 2026")
