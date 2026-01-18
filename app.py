import streamlit as st
import pandas as pd
import requests
import time
from datetime import datetime
from telegram import Bot
import plotly.express as px
import numpy as np

# Config Import (User creates config.py from template)
try:
    from config import (
        DHAN_TOKEN, TELEGRAM_TOKEN, CHAT_ID, INDICES, 
        DELTA_CE, DELTA_PE, GAMMA_MIN, IV_MAX, OI_MIN,
        PCR_BULLISH, PCR_BEARISH
    )
except ImportError:
    st.error("""
    ❌ **config.py missing!** 
    
    **Quick Fix:**
    1. `cp config_template.py config.py`
    2. Add your DhanHQ + Telegram keys
    3. Refresh page
    
    📖 See README.md for setup
    """)
    st.stop()

# Page Config
st.set_page_config(
    page_title="🚀 Dual Strike Screener v2.5", 
    page_icon="🚀",
    layout="wide", 
    initial_sidebar_state="expanded"
)

# CSS Styling
st.markdown("""
<style>
    .main-header {font-size: 3rem; color: #1f77b4;}
    .metric-card {background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                  color: white; padding: 1rem; border-radius: 10px;}
</style>
""", unsafe_allow_html=True)

class DualStrikeScanner:
    """Main Scanner Class"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "access-token": DHAN_TOKEN, 
            "content-type": "application/json"
        })
        self.bot = Bot(token=TELEGRAM_TOKEN)
        self.last_alerts = {}
    
    def get_spot_price(self, symbol):
        """DhanHQ Live Spot Price"""
        try:
            url = "https://api.dhan.co/charts/v2/ltpc"
            payload = {
                "securityId": f"NSE_{symbol}_I", 
                "exchangeSegment": "NSE_INDEX"
            }
            resp = self.session.post(url, json=payload, timeout=10)
            if resp.status_code == 200:
                return resp.json()['data']['ltp']
            return 24000  # Fallback
        except:
            return 24000
    
    def get_option_chain(self, symbol):
        """Nearest Weekly Expiry Chain"""
        try:
            url = "https://api.dhan.co/charts/v2/optionchain"
            payload = {
                "securityId": f"NSE_{symbol}_I",
                "exchangeSegment": "NSE_FO"
            }
            resp = self.session.post(url, json=payload, timeout=15)
            
            if resp.status_code != 200:
                return pd.DataFrame()
            
            data = resp.json()['data']['records']
            if not data:
                return pd.DataFrame()
                
            df = pd.DataFrame(data)
            df['expiryDate'] = pd.to_datetime(df['expiryDate'])
            
            # Nearest expiry (weekly/monthly)
            nearest_expiry = df['expiryDate'].min()
            return df[df['expiryDate'] == nearest_expiry]
            
        except Exception as e:
            st.error(f"Chain fetch failed for {symbol}: {e}")
            return pd.DataFrame()
    
    def find_best_strike(self, df, option_type, symbol, spot_price):
        """AI-Powered Strike Selection"""
        if df.empty:
            return None
        
        # Strategy Parameters
        delta_range = DELTA_CE if option_type == 'CE' else DELTA_PE
        oi_threshold = OI_MIN.get(symbol, 100000)
        
        # Main Filter: ATM + Greeks + High OI + Volume
        conditions = (
            (df['optionType'] == option_type) &
            (abs(df['strikePrice'] - spot_price) <= 150) &  # Near ATM
            (df['delta'].between(*delta_range)) &
            (df['gamma'] >= GAMMA_MIN) &
            (df['iv'] <= IV_MAX) &
            (df['oi'] >= oi_threshold) &
            (df['volume'] > 1000)  # Liquidity check
        )
        
        filtered_strikes = df[conditions]
        
        if filtered_strikes.empty:
            # Fallback: ATM + Highest OI
            atm_fallback = df[
                (df['optionType'] == option_type) & 
                (abs(df['strikePrice'] - spot_price) <= 100)
            ].sort_values('oi', ascending=False)
            
            return atm_fallback.iloc[0] if not atm_fallback.empty else None
        
        # Best strike by OI + Volume score
        filtered_strikes['score'] = (
            filtered_strikes['oi'] * 0.6 + 
            filtered_strikes['volume'] * 0.4
        )
        return filtered_strikes.loc[filtered_strikes['score'].idxmax()]
    
    def calculate_pcr(self, chain_df):
        """Total Put-Call Ratio"""
        if chain_df.empty:
            return 1.0
        
        ce_oi = chain_df[chain_df['optionType'] == 'CE']['oi'].sum()
        pe_oi = chain_df[chain_df['optionType'] == 'PE']['oi'].sum()
        return pe_oi / ce_oi if ce_oi > 0 else 1.0
    
    def get_pcr_signal(self, pcr):
        """PCR Trading Signal"""
        if pcr < PCR_BULLISH:
            return "🟢 CE బై", "BULLISH"
        elif pcr > PCR_BEARISH:
            return "🔴 PE బై", "BEARISH"
        else:
            return "🟡 వెయిట్", "NEUTRAL"
    
    def send_telegram_alert(self, data):
        """Smart Bi-lingual Alerts"""
        symbol = data['symbol']
        if symbol in self.last_alerts and (datetime.now() - self.last_alerts[symbol]).seconds < 300:
            return  # 5 min cooldown
        
        try:
            pcr_signal, sentiment = self.get_pcr_signal(data['pcr'])
            profit_potential = round((50 * abs(data['ce_delta'])) / data['ce_ltp'] * 100, 1)
            
            msg = f"""
🚀 **{symbol} Auto Strike Alert** 🚀

📊 **Spot**: ₹{data['spot']:,}
⚖️ **PCR**: {data['pcr']:.2f} {pcr_signal}

🟢 **CALL OPTION**
🎯 Strike: {int(data['ce_strike'])}
💰 LTP: ₹{data['ce_ltp']:.0f} 
📈 Delta: {data['ce_delta']:.2f} | Gamma: {data['ce_gamma']:.3f}

🔴 **PUT OPTION**  
🎯 Strike: {int(data['pe_strike'])}
💰 LTP: ₹{data['pe_ltp']:.0f}
📈 Delta: {data['pe_delta']:.2f} | Gamma: {data['pe_gamma']:.3f}

💹 **OI**: CE {data['ce_oi']/1000:.0f}K | PE {data['pe_oi']/1000:.0f}K
🎯 **Profit Potential**: {profit_potential}% ↑
⏰ **Time**: {datetime.now().strftime('%H:%M:%S')}

#DualStrike #Options #NSE
            """
            
            self.bot.send_message(CHAT_ID, msg.strip(), parse_mode='Markdown')
            self.last_alerts[symbol] = datetime.now()
            st.success(f"✅ Telegram alert sent for {symbol}")
            
        except Exception as e:
            st.error(f"Telegram Error: {e}")

# === MAIN APPLICATION ===
def main():
    st.title("🚀 Dual Strike Screener v2.5")
    st.markdown("**🔥 Live Greeks + PCR + AI Strike Selection + Telegram Alerts**")
    
    # Sidebar Controls
    st.sidebar.header("⚙️ Scanner Controls")
    enable_alerts = st.sidebar.toggle("📱 Send Telegram Alerts", value=True)
    auto_refresh = st.sidebar.toggle("🔄 Auto Refresh", value=True)
    refresh_interval = st.sidebar.slider("Refresh Interval", 30, 300, 60)
    
    # Strategy Preview
    st.sidebar.markdown("---")
    st.sidebar.subheader("🎯 Current Strategy")
    st.sidebar.info(f"""
    **Greeks Filters:**
    • CE Δ: {DELTA_CE[0]:.2f} - {DELTA_CE[1]:.2f}
    • PE Δ: {DELTA_PE[0]:.2f} - {DELTA_PE[1]:.2f}  
    • γ ≥ {GAMMA_MIN}
    • IV ≤ {IV_MAX}%
    
    **PCR Signals:**
    • < {PCR_BULLISH} → 🟢 CE Buy
    • > {PCR_BEARISH} → 🔴 PE Buy
    """)
    
    # Initialize Scanner
    scanner = DualStrikeScanner()
    metrics_data = []
    
    # Main Dashboard Grid (3x2)
    col1, col2, col3 = st.columns(3)
    
    for idx, symbol in enumerate(INDICES["NSE"]):
        col = [col1, col2, col3][idx % 3]
        
        with col:
            # Live Data Fetch
            with st.spinner(f"Scanning {symbol}..."):
                spot_price = scanner.get_spot_price(symbol)
                chain_df = scanner.get_option_chain(symbol)
            
            if not chain_df.empty and spot_price > 0:
                # Find Best Strikes
                ce_strike = scanner.find_best_strike(chain_df, 'CE', symbol, spot_price)
                pe_strike = scanner.find_best_strike(chain_df, 'PE', symbol, spot_price)
                
                # PCR Analysis
                pcr = scanner.calculate_pcr(chain_df)
                pcr_signal, sentiment = scanner.get_pcr_signal(pcr)
                
                # Telegram Alert Trigger
                if enable_alerts and ce_strike and pe_strike:
                    scanner.send_telegram_alert({
                        'symbol': symbol, 'spot': spot_price, 'pcr': pcr,
                        'ce_strike': ce_strike['strikePrice'], 'ce_ltp': ce_strike['ltp'],
                        'ce_delta': ce_strike['delta'], 'ce_gamma': ce_strike.get('gamma', 0),
                        'ce_oi': chain_df[chain_df['optionType'] == 'CE']['oi'].sum(),
                        'pe_strike': pe_strike['strikePrice'], 'pe_ltp': pe_strike['ltp'],
                        'pe_delta': pe_strike['delta'], 'pe_gamma': pe_strike.get('gamma', 0),
                        'pe_oi': chain_df[chain_df['optionType'] == 'PE']['oi'].sum()
                    })
                
                # Live Metrics Card
                st.markdown(f"""
                <div class="metric-card">
                    <h3 style='margin:0'>{symbol}</h3>
                    <h1 style='margin:5px 0'>₹{spot_price:,.0f}</h1>
                    <h4 style='margin:5px 0'>{pcr_signal} | PCR {pcr:.2f}</h4>
                </div>
                """, unsafe_allow_html=True)
                
                # Strike Details
                if ce_strike:
                    profit_ce = round(50 * ce_strike['delta'] / ce_strike['ltp'] * 100, 1)
                    st.caption(f"🟢 CE {int(ce_strike['strikePrice'])} ₹{ce_strike['ltp']:.0f} Δ:{ce_strike['delta']:.2f} ({profit_ce}%)")
                
                if pe_strike:
                    profit_pe = round(50 * abs(pe_strike['delta']) / pe_strike['ltp'] * 100, 1)
                    st.caption(f"🔴 PE {int(pe_strike['strikePrice'])} ₹{pe_strike['ltp']:.0f} Δ:{pe_strike['delta']:.2f} ({profit_pe}%)")
                
                # Data for Analytics
                metrics_data.append({
                    'Symbol': symbol,
                    'Spot': spot_price,
                    'PCR': round(pcr, 2),
                    'Signal': sentiment,
                    'CE_Strike': int(ce_strike['strikePrice']) if ce_strike else 0,
                    'CE_LTP': round(ce_strike['ltp'], 0) if ce_strike else 0,
                    'CE_Delta': round(ce_strike['delta'], 2) if ce_strike else 0,
                    'PE_Strike': int(pe_strike['strikePrice']) if pe_strike else 0,
                    'PE_LTP': round(pe_strike['ltp'], 0) if pe_strike else 0
                })
    
    # Analytics Dashboard
    if metrics_data:
        st.divider()
        st.subheader("📊 Live Analytics Dashboard")
        
        # Metrics Table
        df_metrics = pd.DataFrame(metrics_data)
        st.dataframe(df_metrics, use_container_width=True, hide_index=True)
        
        # PCR Sentiment Chart
        fig = px.bar(
            df_metrics, x='Symbol', y='PCR', 
            title="⚖️ PCR Sentiment Heatmap",
            color='PCR', 
            color_continuous_scale='RdYlGn_r',
            labels={'PCR': 'Put-Call Ratio'},
            height=400
        )
        fig.update_layout(showlegend=False, xaxis_title="Index", yaxis_title="PCR")
        st.plotly_chart(fig, use_container_width=True)
    
    # Footer
    st.divider()
    col1, col2, col3 = st.columns(3)
    with col1:
        st.info(f"**Last Update**: {datetime.now().strftime('%d %b %H:%M:%S')}")
    with col2:
        st.success(f"**Telegram**: {'✅ ACTIVE' if enable_alerts else '❌ OFF'}")
    with col3:
        st.caption(f"**Strategy**: {len(INDICES['NSE'])} Indices | v2.5 Pro")
    
    # Auto Refresh
    if auto_refresh:
        time.sleep(refresh_interval)
        st.rerun()

if __name__ == "__main__":
    main()
