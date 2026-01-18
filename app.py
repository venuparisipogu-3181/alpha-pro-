import streamlit as st
import pandas as pd
import requests
import time
from datetime import datetime, date
from telegram import Bot
import logging
import plotly.express as px
import plotly.graph_objects as go

# Config Import
try:
    from config import *
except ImportError:
    st.error("❌ config.py ఫైల్ లేకపోతుంది! DhanHQ/Telegram keys add చేయండి.")
    st.stop()

# Streamlit Settings
st.set_page_config(page_title="🚀 Dual Strike Screener v2.5", layout="wide", initial_sidebar_state="expanded")
logging.basicConfig(level=logging.INFO)

class MultiIndexScanner:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({"access-token": DHAN_TOKEN, "content-type": "application/json"})
        self.bot = Bot(token=TELEGRAM_TOKEN)
    
    @st.cache_data(ttl=30)
    def get_spot_price(self, symbol, exchange):
        """Live Spot Price"""
        try:
            exch_seg = "NSE_INDEX" if exchange == "NSE" else "BSE_INDEX"
            url = "https://api.dhan.co/charts/v2/ltpc"
            payload = {"securityId": f"{exchange}_{symbol}_I", "exchangeSegment": exch_seg}
            resp = self.session.post(url, json=payload, timeout=10)
            return resp.json()['data']['ltp'] if resp.status_code == 200 else 0
        except:
            return 0
    
    @st.cache_data(ttl=60)
    def get_option_chain(self, symbol, exchange):
        """Nearest Expiry Option Chain"""
        try:
            url = "https://api.dhan.co/charts/v2/optionchain"
            exch_seg = "NSE_FO" if exchange == "NSE" else "BSE_FO"
            payload = {"securityId": f"{exchange}_{symbol}_I", "exchangeSegment": exch_seg}
            resp = self.session.post(url, json=payload, timeout=15)
            
            if resp.status_code != 200:
                return pd.DataFrame(), "N/A"
            
            df = pd.DataFrame(resp.json()['data']['records'])
            if df.empty:
                return df, "N/A"
            
            df['expiryDate'] = pd.to_datetime(df['expiryDate'])
            nearest_expiry = df['expiryDate'].min()
            filtered_df = df[df['expiryDate'] == nearest_expiry]
            
            return filtered_df, nearest_expiry.strftime('%d %b')
        except Exception as e:
            st.error(f"Chain Error {symbol}: {e}")
            return pd.DataFrame(), "N/A"
    
    def find_best_strike(self, df, opt_type, symbol, spot_price):
        """AI-Powered Strike Selection"""
        if df.empty:
            return None
        
        delta_range = DELTA_CE if opt_type == 'CE' else DELTA_PE
        oi_threshold = OI_MIN.get(symbol, 100000)
        
        # Filter Logic
        atm_mask = abs(df['strikePrice'] - spot_price) <= 100
        delta_mask = df['delta'].between(*delta_range)
        gamma_mask = df['gamma'] >= GAMMA_MIN
        iv_mask = df['iv'] <= IV_MAX
        oi_mask = df['oi'] >= oi_threshold
        
        filtered = df[atm_mask & delta_mask & gamma_mask & iv_mask & oi_mask & (df['optionType'] == opt_type)]
        
        if filtered.empty:
            # Fallback: ATM + High OI
            fallback = df[(df['optionType'] == opt_type) & atm_mask].sort_values('oi', ascending=False)
            return fallback.iloc[0].to_dict() if not fallback.empty else None
        
        return filtered.sort_values('oi', ascending=False).iloc[0].to_dict()
    
    def calculate_pcr(self, ce_df, pe_df):
        """Total & Strike PCR"""
        total_ce_oi = ce_df['oi'].sum()
        total_pe_oi = pe_df['oi'].sum()
        return total_pe_oi / total_ce_oi if total_ce_oi > 0 else 0
    
    def send_telegram_alert(self, data):
        """Smart Telegram Alerts"""
        try:
            pcr = data['pcr']
            signal = "🟢 CE" if pcr < PCR_BULLISH else "🔴 PE" if pcr > PCR_BEARISH else "🟡 WAIT"
            
            msg = f"""
🚀 *{data['symbol']} Alert* 🚀
📊 Spot: ₹{data['spot']:,}
🟢 CE: {int(data['ce_strike'])} @ ₹{data['ce_ltp']:.0f} Δ:{data['ce_delta']:.2f}
🔴 PE: {int(data['pe_strike'])} @ ₹{data['pe_ltp']:.0f} Δ:{data['pe_delta']:.2f}
⚖️ PCR: {pcr:.2f} → {signal}
⏰ {datetime.now().strftime('%H:%M')}
#Options #AutoStrike
            """
            self.bot.send_message(CHAT_ID, msg.strip(), parse_mode='Markdown')
        except:
            pass

# === DASHBOARD ===
st.title("🚀 Dual Strike Screener v2.5")
st.markdown("**Live Greeks + PCR + Auto Alerts**")

# Sidebar Controls
st.sidebar.header("⚙️ Scanner Settings")
enable_alerts = st.sidebar.toggle("📱 Telegram Alerts", value=True)
auto_refresh = st.sidebar.toggle("🔄 Auto Refresh", value=True)
refresh_sec = st.sidebar.slider("Refresh (sec)", 30, 300, 60)

# Initialize Scanner
scanner = MultiIndexScanner()

# Main Metrics Grid
if auto_refresh:
    for seconds in range(refresh_sec):
        time.sleep(1)
    st.rerun()

cols = st.columns(len(INDICES["NSE"]))
metrics_data = []

for idx, symbol in enumerate(INDICES["NSE"]):
    with cols[idx]:
        spot = scanner.get_spot_price(symbol, "NSE")
        chain, expiry = scanner.get_option_chain(symbol, "NSE")
        
        if not chain.empty:
            ce_strike = scanner.find_best_strike(chain, 'CE', symbol, spot)
            pe_strike = scanner.find_best_strike(chain, 'PE', symbol, spot)
            
            ce_df = chain[chain['optionType'] == 'CE']
            pe_df = chain[chain['optionType'] == 'PE']
            pcr = scanner.calculate_pcr(ce_df, pe_df)
            
            # Telegram Alert
            if enable_alerts and ce_strike and pe_strike:
                scanner.send_telegram_alert({
                    'symbol': symbol, 'spot': spot, 'pcr': pcr,
                    'ce_strike': ce_strike['strikePrice'], 'ce_ltp': ce_strike['ltp'], 'ce_delta': ce_strike['delta'],
                    'pe_strike': pe_strike['strikePrice'], 'pe_ltp': pe_strike['ltp'], 'pe_delta': pe_strike['delta']
                })
            
            # Display Metrics
            st.metric(f"**{symbol}**", f"₹{spot:,.0f}", f"Exp: {expiry}")
            st.caption(f"🟢 CE: {int(ce_strike['strikePrice'])} ₹{ce_strike['ltp']:.0f} Δ:{ce_strike['delta']:.2f}")
            st.caption(f"🔴 PE: {int(pe_strike['strikePrice'])} ₹{pe_strike['ltp']:.0f} Δ:{pe_strike['delta']:.2f}")
            st.caption(f"⚖️ PCR: **{pcr:.2f}** {'🟢' if pcr<PCR_BULLISH else '🔴' if pcr>PCR_BEARISH else '🟡'}")
            
            metrics_data.append({
                'Symbol': symbol, 'Spot': spot, 'Expiry': expiry, 'PCR': pcr,
                'CE_Strike': ce_strike['strikePrice'], 'CE_LTP': ce_strike['ltp'], 'CE_Delta': ce_strike['delta'],
                'PE_Strike': pe_strike['strikePrice'], 'PE_LTP': pe_strike['ltp'], 'PE_Delta': pe_strike['delta']
            })

# Analytics Table
if metrics_data:
    st.divider()
    st.subheader("📊 Live Analytics Table")
    df_metrics = pd.DataFrame(metrics_data)
    st.dataframe(df_metrics, use_container_width=True)
    
    # PCR Chart
    fig = px.bar(df_metrics, x='Symbol', y='PCR', title="PCR Sentiment", 
                 color='PCR', color_continuous_scale='RdYlGn_r')
    st.plotly_chart(fig, use_container_width=True)

st.info(f"**Updated**: {datetime.now().strftime('%d %b %H:%M:%S')} | Alerts: {'✅' if enable_alerts else '❌'}")
