import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime

# Page configuration
st.set_page_config(page_title="🚀 Dual Strike Screener v2.5", layout="wide")

st.title("🚀 Dual Strike Screener v2.5")
st.markdown("**🔥 Live NIFTY Greeks + PCR + Smart Alerts**")

# Sidebar controls
st.sidebar.header("⚙️ Control Panel")
show_alerts = st.sidebar.toggle("📱 Show Alerts", value=True)
refresh_now = st.sidebar.button("🔄 Refresh Dashboard")

# Strategy parameters
INDICES = ["NIFTY", "BANKNIFTY", "FINNIFTY"]
PCR_BULLISH = 0.85
PCR_BEARISH = 1.25

# Live data (Demo mode - No API needed!)
live_data = {
    "NIFTY": {"spot": 24012, "pcr": 0.82, "ce": 24000, "pe": 24000, "ce_price": 85, "pe_price": 78},
    "BANKNIFTY": {"spot": 51234, "pcr": 1.35, "ce": 51200, "pe": 51200, "ce_price": 145, "pe_price": 132},
    "FINNIFTY": {"spot": 23456, "pcr": 0.95, "ce": 23450, "pe": 23450, "ce_price": 67, "pe_price": 71}
}

# Main dashboard grid
cols = st.columns(3)
metrics_data = []

for idx, symbol in enumerate(INDICES):
    with cols[idx]:
        data = live_data[symbol]
        
        # PCR Signal Logic
        pcr = data['pcr']
        if pcr < PCR_BULLISH:
            signal = "🟢 CE BUY"
            delta_color = "normal"
        elif pcr > PCR_BEARISH:
            signal = "🔴 PE BUY"
            delta_color = "inverse"
        else:
            signal = "🟡 WAIT"
            delta_color = "off"
        
        # Main metric card
        st.metric(
            label=f"**{symbol}**",
            value=f"₹{data['spot']:,.0f}",
            delta=f"{signal}\nPCR: {pcr:.2f}"
        )
        
        # Option strikes
        st.caption(f"🟢 CE: {data['ce']}CE ₹{data['ce_price']} | 🔴 PE: {data['pe']}PE ₹{data['pe_price']}")
        
        # Telegram-style alert box
        if show_alerts:
            with st.container(border=True):
                st.markdown(f"""
                **📱 LIVE ALERT**
                ```
                🚀 {symbol} Signal
                📊 Spot: ₹{data['spot']:,}
                ⚖️ PCR: {pcr:.2f} → {signal}
                🟢 CE: {data['ce']}PE ₹{data['pe_price']}
                ⏰ {datetime.now().strftime('%H:%M:%S')}
                ```
                """)
        
        # Store data for analytics
        metrics_data.append({
            'Symbol': symbol,
            'Spot': f"₹{data['spot']:,.0f}",
            'PCR': f"{pcr:.2f}",
            'Signal': signal,
            'CE_Strike': f"{data['ce']}CE",
            'PE_Strike': f"{data['pe']}PE"
        })

# Analytics section
st.divider()
st.subheader("📊 Live Analytics Table")

df = pd.DataFrame(metrics_data)
st.dataframe(df, use_container_width=True, hide_index=True)

# PCR Chart
st.subheader("⚖️ PCR Heatmap")
pcr_data = {row['Symbol']: float(row['PCR'][:-1]) for row in metrics_data}
st.bar_chart(pcr_data)

# Status metrics
col1, col2, col3 = st.columns(3)
col1.metric("Last Update", datetime.now().strftime('%H:%M:%S IST'))
col2.metric("Status", "✅ LIVE")
col3.metric("Indices Scanned", len(INDICES))

# Footer
st.markdown("---")
st.info("""
**Dual Strike Screener v2.5** | 
**Strategy**: PCR < 0.85 = 🟢 CE BUY | PCR > 1.25 = 🔴 PE BUY | 
**Demo Mode**: Real-time simulation ready for live API
""")

if refresh_now:
    st.rerun()
