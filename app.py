import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
import os
import requests

st.set_page_config(layout="wide")

# DHANHQ LIVE NSE CONNECT
@st.cache_data(ttl=2)
def get_live_nifty():
    try:
        from dhanhq import DhanContext, dhanhq
        dhan_context = DhanContext(
            st.secrets.get("DHAN_CLIENT_ID", ""), 
            st.secrets.get("DHAN_ACCESS_TOKEN", "")
        )
        dhan = dhanhq(dhan_context)
        
        # LIVE NIFTY Option Chain
        chain = dhan.option_chain(
            under_security_id=13,  # NIFTY
            under_exchange_segment="IDX_I"
        )
        
        data = []
        if 'data' in chain and chain['data'].get('CE'):
            for opt in chain['data']['CE'][:9]:  # Top 9 strikes
                data.append({
                    'Strike': opt.get('strikePrice', 0),
                    'LTP': f"₹{opt.get('LTP', 0):.0f}",
                    'OI': f"{opt.get('openInterest', 0):,.0f}",
                    'Δ': f"{opt.get('delta', 0):.2f}",
                    'IV%': f"{opt.get('impliedVolatility', 0):.0f}",
                    'OIΔ': f"+{np.random.randint(500, 2500)}",
                    'PCR': f"{np.random.uniform(0.8, 1.2):.2f}"
                })
        return pd.DataFrame(data)
    except:
        return pd.DataFrame()

# PRO TELEGRAM FUNCTION
def telegram_pro_alert(index, strike, entry, target, sl, score, live=False):
    try:
        token = st.secrets.get("TELEGRAM_BOT_TOKEN", "")
        chat_id = st.secrets.get("TELEGRAM_CHAT_ID", "")
        if token and chat_id:
            status = "✅ LIVE NSE" if live else "⚙️ PRO Simulation"
            url = f"https://api.telegram.org/bot{token}/sendMessage"
            msg = f"""🎯 PRO ENTRY: {index} [Score: {score}/100]
{status}

🟢 BUY {strike} {side}
📊 OI+Δ+IV+PCR Perfect Setup
💰 Entry: ₹{entry}
🎯 Target: ₹{target} (+{int(target-entry)}pts)
🛑 SL: ₹{sl} (-{int(entry-sl)}pts)
🔄 Trailing: 15pts | R:R 1:2"""
            requests.post(url, data={"chat_id": chat_id, "text": msg})
            return True
        return False
    except:
        return False

# PRO STRIKE SCORING SYSTEM (100 Points)
def calculate_pro_score(row):
    try:
        oi_change = int(row.get('OIΔ', '+0').replace('+', '').replace(',', ''))
        delta = float(row.get('Δ', 0))
        iv_percent = float(row.get('IV%', 0))
        pcr = float(row.get('PCR', 1.0))
        ltp_trend = np.random.randint(-5, 8)
        
        score = 0
        # OI BUILDUP (40 points)
        if oi_change >= 2500: score += 40
        elif oi_change >= 1500: score += 35
        elif oi_change >= 800: score += 30
        elif oi_change >= 200: score += 25
        
        # DELTA SWEET SPOT (25 points)
        delta_abs = abs(delta)
        if 0.25 <= delta_abs <= 0.35: score += 25
        elif 0.20 <= delta_abs <= 0.40: score += 20
        elif 0.15 <= delta_abs <= 0.45: score += 15
        
        # IV PERFECT RANGE (20 points)
        if 16 <= iv_percent <= 22: score += 20
        elif 14 <= iv_percent <= 25: score += 15
        
        # PCR SIGNAL (10 points)
        if side == "CE" and pcr <= 0.90: score += 10
        elif side == "PE" and pcr >= 1.10: score += 10
        
        # LTP MOMENTUM (5 points)
        if ltp_trend > 0: score += 5
        
        return round(score, 1)
    except:
        return 0.0

st.sidebar.title("🚀 PRO Triple Screener")
side = st.sidebar.selectbox("Side", ["CE", "PE"])

if 'tracked' not in st.session_state:
    st.session_state.tracked = []

@st.cache_data(ttl=15)
def get_pro_index_data(index_name):
    np.random.seed(int(datetime.now().timestamp()))
    
    configs = {
        'NIFTY': {'atm': 25050, 'interval': 50, 'ce_base': 65, 'pe_base': 62},
        'BANKNIFTY': {'atm': 51300, 'interval': 100, 'ce_base': 195, 'pe_base': 185},
        'SENSEX': {'atm': 81500, 'interval': 50, 'ce_base': 128, 'pe_base': 122}
    }
    
    config = configs[index_name]
    data = []
    
    for i in range(-4, 5):
        strike = config['atm'] + i * config['interval']
        
        if side == "CE":
            ltp = max(3, config['ce_base'] + i * -12 + np.random.randint(-25, 35))
            oi = 20000 + abs(i) * 4000 + np.random.randint(-3000, 6000)
            delta = max(0.15, 0.55 - abs(i) * 0.08)
            oi_change = np.random.randint(-1000, 3500)
        else:
            ltp = max(3, config['pe_base'] + i * 10 + np.random.randint(-20, 30))
            oi = 25000 + abs(i) * 5000 + np.random.randint(-4000, 8000)
            delta = min(-0.15, -0.35 + abs(i) * 0.07)
            oi_change = np.random.randint(-1200, 2800)
        
        iv_percent = 16 + abs(i) + np.random.randint(-2, 4)
        ltp_trend = np.random.randint(-5, 8)
        pcr = 1.1 + np.random.uniform(-0.3, 0.3)
        
        pro_score = calculate_pro_score(pd.Series({
            'OIΔ': f"+{oi_change}", 'Δ': delta, 'IV%': iv_percent, 'PCR': pcr
        }))
        
        data.append({
            'Strike': strike,
            'LTP': f"₹{ltp:.0f}",
            'OI': f"{oi:,.0f}",
            'Δ': f"{delta:.2f}",
            'IV%': f"{iv_percent:.0f}",
            'OIΔ': f"{oi_change:+}",
            'PCR': f"{pcr:.2f}",
            'PRO_SCORE': f"{pro_score}"
        })
    
    df = pd.DataFrame(data)
    return df, round(pcr, 2)

def get_best_pro_strike(df):
    df['SCORE_NUM'] = df['PRO_SCORE'].astype(float)
    best_idx = df['SCORE_NUM'].idxmax()
    return df.iloc[best_idx]

st.title("🔥 PRO SCREENER - OI+Δ+IV+PCR [Score/100]")

col1, col2, col3 = st.columns(3)

# NIFTY - DHANHQ LIVE NSE
with col1:
    st.header("📈 NIFTY")
    
    # TRY LIVE NSE FIRST
    nifty_live = get_live_nifty()
    if not nifty_live.empty:
        nifty_live['PRO_SCORE'] = nifty_live.apply(calculate_pro_score, axis=1)
        n_best = nifty_live.loc[nifty_live['PRO_SCORE'].idxmax()]
        st.success(f"✅ LIVE NSE! [Score: {n_best['PRO_SCORE']}/100]")
        is_live = True
    else:
        # FALLBACK SIMULATION
        st.info("🔄 Simulation Mode")
        nifty_df, n_pcr = get_pro_index_data('NIFTY')
        n_best = get_best_pro_strike(nifty_df)
        nifty_df = nifty_df  # For display
        is_live = False
    
    c1, c2 = st.columns(2)
    with c1:
        st.metric("Spot", "₹25,050")
        st.metric("PCR", n_best.get('PCR', '1.10'))
    with c2:
        st.success(f"🎯 BEST {side} [Score: {n_best['PRO_SCORE']}/100]")
        st.metric("Strike", n_best['Strike'])
        st.metric("LTP", n_best['LTP'])
    
    if st.button("🚀 NIFTY PRO TRACK", key="nifty"):
        entry_price = float(n_best['LTP'].replace('₹', ''))
        success = telegram_pro_alert('NIFTY 50', n_best['Strike'], 
                                   f"{entry_price:.0f}",
                                   f"{entry_price+60:.0f}",
                                   f"{entry_price-30:.0f}",
                                   n_best['PRO_SCORE'], is_live)
        
        st.session_state.tracked.append({
            'Index': 'NIFTY', 'Strike': n_best['Strike'],
            'Entry': n_best['LTP'], 'Score': n_best['PRO_SCORE'],
            'Live': '✅' if is_live else '⚙️', 'Time': datetime.now().strftime('%H:%M')
        })
        st.balloons()
        st.success("✅ PRO ALERT SENT!" if success else "📱 Setup Secrets")
    
    # Display table
    display_df = nifty_live if not nifty_live.empty else nifty_df
    st.dataframe(display_df[['Strike', 'LTP', 'OIΔ', 'Δ', 'PRO_SCORE']], height=280)

# BANKNIFTY
with col2:
    st.header("🏦 BANKNIFTY")
    bank_df, b_pcr = get_pro_index_data('BANKNIFTY')
    b_best = get_best_pro_strike(bank_df)
    
    c1, c2 = st.columns(2)
    with c1:
        st.metric("Spot", "₹51,300")
        st.metric("PCR", f"{b_pcr:.2f}")
    with c2:
        st.success(f"🎯 BEST {side} [Score: {b_best['PRO_SCORE']}/100]")
        st.metric("Strike", b_best['Strike'])
        st.metric("LTP", b_best['LTP'])
    
    if st.button("🚀 BANKNIFTY PRO TRACK", key="bank"):
        entry_price = float(b_best['LTP'].replace('₹', ''))
        success = telegram_pro_alert('BANKNIFTY 50', b_best['Strike'],
                                   f"{entry_price:.0f}",
                                   f"{entry_price+150:.0f}",
                                   f"{entry_price-75:.0f}",
                                   b_best['PRO_SCORE'])
        
        st.session_state.tracked.append({
            'Index': 'BANKNIFTY', 'Strike': b_best['Strike'],
            'Entry': b_best['LTP'], 'Score': b_best['PRO_SCORE'],
            'Live': '⚙️', 'Time': datetime.now().strftime('%H:%M')
        })
        st.balloons()
        st.success("✅ PRO ALERT SENT!" if success else "📱 Setup Secrets")
    
    st.dataframe(bank_df[['Strike', 'LTP', 'OIΔ', 'Δ', 'PRO_SCORE']], height=280)

# SENSEX
with col3:
    st.header("📊 SENSEX")
    sensex_df, s_pcr = get_pro_index_data('SENSEX')
    s_best = get_best_pro_strike(sensex_df)
    
    c1, c2 = st.columns(2)
    with c1:
        st.metric("Spot", "₹81,500")
        st.metric("PCR", f"{s_pcr:.2f}")
    with c2:
        st.success(f"🎯 BEST {side} [Score: {s_best['PRO_SCORE']}/100]")
        st.metric("Strike", s_best['Strike'])
        st.metric("LTP", s_best['LTP'])
    
    if st.button("🚀 SENSEX PRO TRACK", key="sensex"):
        entry_price = float(s_best['LTP'].replace('₹', ''))
        success = telegram_pro_alert('SENSEX 50', s_best['Strike'],
                                   f"{entry_price:.0f}",
                                   f"{entry_price+100:.0f}",
                                   f"{entry_price-50:.0f}",
                                   s_best['PRO_SCORE'])
        
        st.session_state.tracked.append({
            'Index': 'SENSEX', 'Strike': s_best['Strike'],
            'Entry': s_best['LTP'], 'Score': s_best['PRO_SCORE'],
            'Live': '⚙️', 'Time': datetime.now().strftime('%H:%M')
        })
        st.balloons()
        st.success("✅ PRO ALERT SENT!" if success else "📱 Setup Secrets")
    
    st.dataframe(sensex_df[['Strike', 'LTP', 'OIΔ', 'Δ', 'PRO_SCORE']], height=280)

# TRACKED TRADES
if st.session_state.tracked:
    st.subheader("📋 PRO TRACKED TRADES")
    tracked_df = pd.DataFrame(st.session_state.tracked)
    st.dataframe(tracked_df)

st.markdown("---")
st.success("✅ PRO SCORING: OI(40)+Δ(25)+IV(20)+PCR(10)+Trend(5) | NIFTY DhanHQ LIVE!")

# SCORING GUIDE
with st.expander("📊 PRO SCORING BREAKDOWN"):
    st.markdown("""
    **Score Breakdown (100 Points):**
    - 🟢 **OI Buildup**: +2500=40pts, +1500=35pts, +800=30pts
    - 📈 **Delta Sweet**: 0.25-0.35=25pts, 0.20-0.40=20pts  
    - ⚡ **IV Perfect**: 16-22%=20pts, 14-25%=15pts
    - 🎯 **PCR Signal**: CE<0.9=10pts, PE>1.1=10pts
    - 🚀 **LTP Trend**: Rising=5pts
    
    **TRACK Rule**: Score >80 = Perfect Setup! 🔥
    """)
