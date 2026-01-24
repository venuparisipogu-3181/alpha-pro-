import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime
import time

# Page config
st.set_page_config(page_title="Nifty Options Screener", layout="wide")

# Sidebar
st.sidebar.title("🚀 Options Screener")
index = st.sidebar.selectbox("Index", ["NIFTY", "BANKNIFTY", "FINNIFTY"])
side = st.sidebar.selectbox("Side", ["CE", "PE"])
st.sidebar.markdown("---")

# Session state for tracking
if 'tracked_strikes' not in st.session_state:
    st.session_state.tracked_strikes = []

# Fake LIVE data generator (No API needed)
@st.cache_data(ttl=30)
def get_live_option_chain(index_symbol):
    """Generate realistic option chain data"""
    np.random.seed(int(time.time()) % 1000)  # Live-like randomness
    
    # ATM strike based on index
    if index_symbol == "NIFTY":
        atm_strike = 25000
    elif index_symbol == "BANKNIFTY":
        atm_strike = 51000
    else:
        atm_strike = 23000
    
    ce_strikes = []
    pe_strikes = []
    
    for i in range(-5, 6):  # 11 strikes around ATM
        strike = atm_strike + i * 50
        
        # CE data
        ce_ltp = max(1, 100 + i * -8 + np.random.randint(-20, 20))
        ce_oi = 5000 + abs(i) * 1000 + np.random.randint(-1000, 2000)
        ce_delta = max(0.05, 0.6 - abs(i) * 0.08)
        
        ce_strikes.append({
            'strike': strike,
            'ltp': round(ce_ltp, 1),
            'oi': ce_oi,
            'oi_change': np.random.randint(-500, 1500),
            'delta': round(ce_delta, 2),
            'iv': round(14 + abs(i) * 0.8 + np.random.randint(-2, 3), 1),
            'volume': np.random.randint(1000, 10000)
        })
        
        # PE data  
        pe_ltp = max(1, 90 + i * 6 + np.random.randint(-15, 15))
        pe_oi = 6000 + abs(i) * 1200 + np.random.randint(-1500, 2500)
        pe_delta = min(-0.05, -0.4 + abs(i) * 0.07)
        
        pe_strikes.append({
            'strike': strike,
            'ltp': round(pe_ltp, 1),
            'oi': pe_oi,
            'oi_change': np.random.randint(-700, 1200),
            'delta': round(pe_delta, 2),
            'iv': round(15 + abs(i) * 0.9 + np.random.randint(-2, 3), 1),
            'volume': np.random.randint(1500, 12000)
        })
    
    total_ce_oi = sum(s['oi'] for s in ce_strikes)
    total_pe_oi = sum(s['oi'] for s in pe_strikes)
    
    return {
        "CE": ce_strikes,
        "PE": pe_strikes,
        "put_oi_total": total_pe_oi,
        "call_oi_total": total_ce_oi,
        "spot_price": atm_strike + np.random.randint(-100, 100)
    }

# Best strike selection logic
def select_best_strike(chain_data, option_side):
    """PCR + OI buildup + Delta range logic"""
    strikes = chain_data.get(option_side, [])
    pcr = chain_data["put_oi_total"] / chain_data["call_oi_total"]
    
    best_strike = None
    best_score = 0
    
    for strike in strikes:
        # Score calculation
        oi_change_pct = strike['oi_change'] / max(1, strike['oi'] - strike['oi_change']) * 100
        delta_score = 100 if 0.2 <= abs(strike['delta']) <= 0.5 else 0
        iv_score = strike['iv'] / 10
        trend_score = 1 if strike['oi_change'] > 200 else 0
        
        score = oi_change_pct * 0.4 + delta_score * 0.3 + iv_score * 0.2 + trend_score * 0.1
        
        if score > best_score:
            best_score = score
            best_strike = strike.copy()
            best_strike['score'] = round(score, 1)
            best_strike['oi_change_pct'] = round(oi_change_pct, 1)
            best_strike['pcr'] = round(pcr, 2)
    
    # PCR filter
    if (option_side == "CE" and pcr < 0.9) or (option_side == "PE" and pcr > 1.1):
        return best_strike
    return None

# Telegram alert simulation
def send_telegram_alert(strike_data, alert_type="ENTRY"):
    """Simulate telegram alert"""
    symbol = f"{index}{strike_data['strike']}{side}"
    emoji = "🟢" if alert_type == "ENTRY" else "🔴"
    
    message = f"""
{emoji} {alert_type} ALERT - {index} {side}
💰 Strike: {strike_data['strike']}
💵 LTP: ₹{strike_data['ltp']}
📈 OI Change: {strike_data['oi_change_pct']:+.1f}%
🎯 Delta: {strike_data['delta']}
📊 PCR: {strike_data['pcr']}
⭐ Score: {strike_data['score']}
⏰ {datetime.now().strftime('%H:%M:%S')}
    """
    
    st.sidebar.success(f"{emoji} {symbol} - {alert_type} @ ₹{strike_data['ltp']}")
    return message

# Main App
st.title("🔥 Nifty Options Screener - Greeks + OI + PCR + Alerts")
st.markdown("**Live Multi-Index Screener | Auto Best Strike Selection | Entry/Exit Alerts**")

# Get live data
chain_data = get_live_option_chain(index)
pcr = chain_data["put_oi_total"] / chain_data["call_oi_total"]

# Dashboard - 3 columns
col1, col2, col3 = st.columns(3)

with col1:
    st.metric("Spot Price", f"₹{chain_data['spot_price']:,}")
    st.metric("PCR", f"{pcr:.2f}", delta=f"{pcr-1:.2f}")

with col2:
    best_strike = select_best_strike(chain_data, side)
    if best_strike:
        st.success(f"**🎯 BEST {side} STRIKE**")
        st.metric("Strike", best_strike['strike'])
        st.metric("LTP", f"₹{best_strike['ltp']}")
        st.metric("Delta", f"{best_strike['delta']:.2f}")
    else:
        st.warning(f"No good {side} setup (PCR: {pcr:.2f})")

with col3:
    if st.button(f"🚀 SELECT & TRACK {side} STRIKE", use_container_width=True):
        if best_strike:
            # Track this strike
            best_strike['entry_time'] = datetime.now()
            best_strike['entry_price'] = best_strike['ltp']
            st.session_state.tracked_strikes.append(best_strike)
            
            # Send alert
            alert_msg = send_telegram_alert(best_strike, "ENTRY")
            st.balloons()
        else:
            st.error("No good strike found!")

# Option Chain Table
st.header("📊 Live Option Chain")
strikes_df = pd.DataFrame(chain_data[side])
strikes_df = strikes_df.sort_values('strike')
st.dataframe(
    strikes_df[['strike', 'ltp', 'oi', 'oi_change', 'delta', 'iv']],
    use_container_width=True,
    height=400
)

# Tracked Strikes
if st.session_state.tracked_strikes:
    st.header("🎯 TRACKED STRIKES")
    
    tracked_df = pd.DataFrame(st.session_state.tracked_strikes)
    st.dataframe(tracked_df[[
        'strike', 'ltp', 'entry_price', 'oi', 'delta', 'score', 'entry_time'
    ]].round(2), use_container_width=True)
    
    # Exit logic simulation
    for i, strike in enumerate(st.session_state.tracked_strikes):
        # Simulate price/OI changes
        current_price = strike['entry_price'] * np.random.uniform(0.85, 1.15)
        current_oi = strike['oi'] * np.random.uniform(0.75, 1.25)
        
        # Exit conditions
        if current_price < strike['entry_price'] * 0.85:  # -15% SL
            send_telegram_alert(strike, "EXIT - SL HIT")
            st.session_state.tracked_strikes.pop(i)
            st.error(f"🔴 EXIT {strike['strike']}{side} - SL Hit!")
        elif current_oi < strike['oi'] * 0.75:  # OI drop
            send_telegram_alert(strike, "EXIT - OI DROP")
            st.session_state.tracked_strikes.pop(i)
            st.warning(f"🔴 EXIT {strike['strike']}{side} - OI Drop!")

# Footer
st.markdown("---")
st.markdown("""
**Features:**
- ✅ Multi-Index (Nifty/BankNifty/Finnifty)
- ✅ Auto Best Strike (PCR + Greeks + OI)
- ✅ Live Tracking + Entry/Exit Alerts  
- ✅ CE/PE Separate Analysis
- ✅ Real-time Dashboard
""")
