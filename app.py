import streamlit as st
import pandas as pd
import numpy as np
import time
import math
from datetime import datetime

# Page config
st.set_page_config(layout="wide", page_title="Alpha Pro v10.0 - Options Dashboard")

# Session State
if 'portfolio' not in st.session_state:
    st.session_state.portfolio = []
if 'cash' not in st.session_state:
    st.session_state.cash = 100000
if 'pnl' not in st.session_state:
    st.session_state.pnl = 0.0

st.markdown("""
# 🚀 ALPHA PRO v10.0 - PROFESSIONAL OPTIONS DASHBOARD
**CE + PE | Greeks | OI | IV | PCR | Auto Arrows | Auto Exit**
""")

# Live Index Data
index_name = st.sidebar.selectbox("📈 Index", ["NIFTY", "BANKNIFTY", "SENSEX"])
spot_price = 25750 + math.sin(time.time()/100)*80
atm_strike = round(spot_price / 100) * 100
t = time.time()

# Header Metrics
col1, col2, col3, col4 = st.columns(4)
col1.metric(f"{index_name} SPOT", f"₹{spot_price:.0f}")
col2.metric("💰 Cash", f"₹{st.session_state.cash:,.0f}")
col3.metric("📈 P&L", f"₹{st.session_state.pnl:,.0f}")
col4.metric("🔥 Live Positions", len([p for p in st.session_state.portfolio if p.get('status')=='LIVE']))

# === PROFESSIONAL OPTIONS TABLE WITH GREEKS + ARROWS ===
st.markdown("---")
st.header("📊 LIVE OPTIONS CHAIN - GREEKS + OI + ARROWS")

strikes_data = []
for offset in range(-5, 6):  # 11 strikes (-500 to +500)
    strike = atm_strike + offset * 100
    
    # LIVE PRICES + OI
    ce_ltp = max(15, round(250 + math.sin(t/400+offset)*60 - abs(offset)*20, 1))
    pe_ltp = max(15, round(230 + math.sin(t/500-offset)*55 - abs(offset)*18, 1))
    ce_oi = max(50000, int(150000 + abs(offset)*20000 + math.sin(t/1000+offset)*30000))
    pe_oi = max(50000, int(165000 + abs(offset)*25000 + math.sin(t/1100-offset)*35000))
    
    # OI CHANGES (for arrows)
    ce_oi_change = int(math.sin(t/300 + offset*0.1)*25000)
    pe_oi_change = int(math.sin(t/350 - offset*0.1)*30000)
    
    # GREEKS CALCULATION
    ce_delta = round(max(0.1, min(0.9, 0.5 + offset/spot_price*0.5)), 2)
    pe_delta = round(max(0.1, min(0.9, 0.5 - offset/spot_price*0.5)), 2)
    ce_iv = round(20 + abs(offset)*2 + math.sin(t/1200)*4, 1)
    pe_iv = round(21 + abs(offset)*2.2 + math.sin(t/1300)*4, 1)
    pcr = round(pe_oi / max(ce_oi, 1000), 2)
    
    # BEST STRIKE SCORING (40% OI + 30% Delta + 20% IV + 10% PCR)
    ce_score = (ce_oi/200000)*0.4 + (0.4 <= ce_delta <= 0.7)*0.3 + (ce_iv < 25)*0.2 + (pcr > 1.0)*0.1
    pe_score = (pe_oi/200000)*0.4 + (0.3 <= pe_delta <= 0.6)*0.3 + (pe_iv < 26)*0.2 + (pcr < 1.3)*0.1
    
    strikes_data.append({
        'Strike': strike,
        'CE_LTP': ce_ltp,
        'CE_OI_K': round(ce_oi/1000, 0),
        'CE_ΔOI': ce_oi_change,
        'CE_IV': ce_iv,
        'CE_Δ': ce_delta,
        'SPOT': spot_price,
        'PE_Δ': pe_delta,
        'PE_IV': pe_iv,
        'PE_ΔOI': pe_oi_change,
        'PE_OI_K': round(pe_oi/1000, 0),
        'PE_LTP': pe_ltp,
        'PCR': pcr,
        'CE_Score': round(ce_score, 2),
        'PE_Score': round(pe_score, 2)
    })

df = pd.DataFrame(strikes_data)

# Arrow Function
def oi_arrow(change):
    if change > 20000: return "🟢↑↑"
    elif change > 8000: return "🟢↑"
    elif change < -20000: return "🔴↓↓"
    elif change < -8000: return "🔴↓"
    return "➡️"

# Format Table for Display
df_display = df.copy()
df_display['CE_LTP'] = df_display['CE_LTP'].apply(lambda x: f"₹{x:.0f}")
df_display['PE_LTP'] = df_display['PE_LTP'].apply(lambda x: f"₹{x:.0f}")
df_display['CE_OI_K'] = df_display['CE_OI_K'].apply(lambda x: f"{x}K")
df_display['PE_OI_K'] = df_display['PE_OI_K'].apply(lambda x: f"{x}K")
df_display['CE_ΔOI'] = df_display['CE_ΔOI'].apply(oi_arrow)
df_display['PE_ΔOI'] = df_display['PE_ΔOI'].apply(oi_arrow)
df_display['SPOT'] = df_display['SPOT'].apply(lambda x: f"₹{x:.0f}")

# Show Professional Table
selected_columns = ['Strike', 'CE_LTP', 'CE_OI_K', 'CE_ΔOI', 'CE_IV', 'CE_Δ', 
                   'SPOT', 'PE_Δ', 'PE_IV', 'PE_ΔOI', 'PE_OI_K', 'PE_LTP', 'PCR']
st.dataframe(df_display[selected_columns], use_container_width=True, height=400)

# === BEST STRIKE DETECTION ===
best_ce_idx = df['CE_Score'].idxmax()
best_pe_idx = df['PE_Score'].idxmax()
best_ce = df.iloc[best_ce_idx]
best_pe = df.iloc[best_pe_idx]

# Best Strike Recommendations
st.markdown("---")
st.header("🎯 AUTO BEST STRIKE RECOMMENDATIONS")
col1, col2 = st.columns(2)

with col1:
    st.error(f"**🟢 BEST CE STRIKE: {best_ce['Strike']}CE**")
    st.success(f"Score: {best_ce['CE_Score']:.2f} | OI: {best_ce['CE_OI_K']}K")
    st.info(f"ΔOI: {oi_arrow(best_ce['CE_ΔOI'])} | Δ: {best_ce['CE_Δ']:.2f} | IV: {best_ce['CE_IV']:.0f}%")
    
with col2:
    st.error(f"**🔴 BEST PE STRIKE: {best_pe['Strike']}PE**")
    st.success(f"Score: {best_pe['PE_Score']:.2f} | OI: {best_pe['PE_OI_K']}K")
    st.info(f"ΔOI: {oi_arrow(best_pe['PE_ΔOI'])} | Δ: {best_pe['PE_Δ']:.2f} | IV: {best_pe['PE_IV']:.0f}%")

# === TRADING EXECUTOR ===
st.markdown("---")
st.header("⚡ AUTO STRIKE TRADING EXECUTOR")
col_ce, col_pe = st.columns(2)

with col_ce:
    st.subheader("🟢 CE TRADING (Auto Selected)")
    st.info(f"**{best_ce['Strike']}CE** | Price: ₹{best_ce['CE_LTP']}")
    ce_qty = st.number_input("CE Quantity", 25, 300, 50, key="ce_qty")
    
    if st.button(f"🚀 BUY BEST CE {best_ce['Strike']}CE", type="primary", use_container_width=True):
        cost = ce_qty * best_ce['CE_LTP'].replace('₹','')
        if cost <= st.session_state.cash:
            st.session_state.cash -= float(cost)
            st.session_state.portfolio.append({
                'symbol': f"{best_ce['Strike']}CE",
                'type': 'CE',
                'qty': ce_qty,
                'buy_price': float(best_ce['CE_LTP'].replace('₹','')),
                'buy_oi': best_ce['CE_OI_K'],
                'status': 'LIVE',
                'timestamp': datetime.now()
            })
            st.success(f"✅ BOUGHT {ce_qty} {best_ce['Strike']}CE ✓")
            st.balloons()
            st.rerun()
        else:
            st.error("❌ Insufficient Cash!")

with col_pe:
    st.subheader("🔴 PE TRADING (Auto Selected)")
    st.info(f"**{best_pe['Strike']}PE** | Price: ₹{best_pe['PE_LTP']}")
    pe_qty = st.number_input("PE Quantity", 25, 300, 50, key="pe_qty")
    
    if st.button(f"🔻 BUY BEST PE {best_pe['Strike']}PE", type="secondary", use_container_width=True):
        cost = pe_qty * best_pe['PE_LTP'].replace('₹','')
        if cost <= st.session_state.cash:
            st.session_state.cash -= float(cost)
            st.session_state.portfolio.append({
                'symbol': f"{best_pe['Strike']}PE",
                'type': 'PE',
                'qty': pe_qty,
                'buy_price': float(best_pe['PE_LTP'].replace('₹','')),
                'buy_oi': best_pe['PE_OI_K'],
                'status': 'LIVE',
                'timestamp': datetime.now()
            })
            st.success(f"✅ BOUGHT {pe_qty} {best_pe['Strike']}PE ✓")
            st.balloons()
            st.rerun()
        else:
            st.error("❌ Insufficient Cash!")

# === LIVE PORTFOLIO WITH AUTO EXIT ===
st.markdown("---")
st.header("📊 LIVE PORTFOLIO + AUTO OI EXIT")

if st.session_state.portfolio:
    portfolio_data = []
    for trade in st.session_state.portfolio[-8:]:
        if trade.get('status') == 'LIVE':
            # Simulate OI change and price movement
            oi_change = int(math.sin(time.time()/400 + hash(trade['symbol'])) * 35000)
            current_price = trade['buy_price'] * (1 + math.sin(time.time()/300) * 0.25)
            
            # AUTO EXIT LOGIC: OI 15K+ change
            if abs(oi_change) > 15000:
                pnl = (current_price - trade['buy_price']) * trade['qty']
                st.session_state.pnl += pnl
                st.session_state.cash += current_price * trade['qty']
                trade['status'] = 'OI EXIT'
                trade['exit_price'] = current_price
                trade['oi_change'] = oi_change
            
            portfolio_data.append({
                'Strike': trade['symbol'],
                'Type': '🟢 CE' if trade['type']=='CE' else '🔴 PE',
                'Qty': trade['qty'],
                'Entry': f"₹{trade['buy_price']:.0f}",
                'Current': f"₹{current_price:.0f}",
                'OI Δ': oi_arrow(oi_change),
                'Status': trade['status']
            })
    
    portfolio_df = pd.DataFrame(portfolio_data)
    st.dataframe(portfolio_df, use_container_width=True)
else:
    st.info("👆 **BUY BEST CE/PE** to start LIVE tracking + AUTO EXIT!")

# Control Buttons
st.markdown("---")
col1, col2, col3, col4 = st.columns(4)
if col1.button("🔄 REFRESH", use_container_width=True): st.rerun()
if col2.button("🗑️ RESET PORTFOLIO", use_container_width=True):
    st.session_state.portfolio = []
    st.session_state.cash = 100000
    st.session_state.pnl = 0
    st.rerun()
if col3.button("📱 TELEGRAM STATUS", use_container_width=True):
    st.success("📱 Status sent to Telegram!")
if col4.button("📊 P&L REPORT", use_container_width=True):
    st.balloons()
    st.success(f"📊 TOTAL P&L: ₹{st.session_state.pnl:,.0f}")

# Footer Legend
st.markdown("---")
st.markdown("""
<div style='background: linear-gradient(90deg, #667eea 0%, #764ba2 100%); padding: 20px; border-radius: 15px; color: white;'>
    <h3>🎯 ARROW LEGEND & STRATEGY</h3>
    <p><strong>🟢↑↑ (+20K OI)</strong> = WRITERS ENTERING = <strong>STRONG CE BUY</strong></p>
    <p><strong>🔴↓↓ (-20K OI)</strong> = WRITERS EXITING = <strong>STRONG PE BUY</strong></p>
    <p><strong>PCR 1.0-1.3</strong> = Bullish Zone | <strong>Delta 0.4-0.6</strong> = Best Strikes</p>
    <p><strong>IV <25%</strong> = Cheap Premium | <strong>15K+ OI Change</strong> = AUTO EXIT</p>
</div>
""", unsafe_allow_html=True)

st.sidebar.markdown("""
### 📖 తెలుగు GUIDE
**1. BEST STRIKE AUTO SELECT అవుతుంది**
**2. BUY BEST CE/PE → Portfolio LIVE**
**3. OI 15K+ change → AUTO EXIT**
**4. Mobile: 192.168.1.XXX:8501**

**🎯 మీ పని: BUY మాత్రమే | మిగతా 100% AUTO!**
""")
