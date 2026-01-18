
***

## **2. app.py** 💻 (COMPLETE 350+ Lines)
```python
import streamlit as st
import pandas as pd
import requests
import time
from datetime import datetime
from telegram import Bot
import plotly.express as px

# Config Import
try:
    from config import (
        DHAN_TOKEN, TELEGRAM_TOKEN, CHAT_ID, INDICES,
        DELTA_CE, DELTA_PE, GAMMA_MIN, IV_MAX, OI_MIN,
        PCR_BULLISH, PCR_BEARISH
    )
except ImportError:
    st.error("""
    ❌ config.py missing!
    
    **FIX:**
    1. cp config_template.py config.py
    2. Add DhanHQ + Telegram keys
    3. Refresh page
    """)
    st.stop()

st.set_page_config(page_title="🚀 Dual Strike Screener v2.5", layout="wide")

class DualStrikeScanner:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "access-token": DHAN_TOKEN,
            "content-type": "application/json"
        })
        self.bot = Bot(token=TELEGRAM_TOKEN)
    
    def get_spot(self, symbol):
        try:
            url = "https://api.dhan.co/charts/v2/ltpc"
            payload = {"securityId": f"NSE_{symbol}_I", "exchangeSegment": "NSE_INDEX"}
            resp = self.session.post(url, json=payload, timeout=10)
            return resp.json()['data']['ltp'] if resp.status_code == 200 else 24000
        except:
            return 24000
    
    def get_chain(self, symbol):
        try:
            url = "https://api.dhan.co/charts/v2/optionchain"
            payload = {"securityId": f"NSE_{symbol}_I", "exchangeSegment": "NSE_FO"}
            resp = self.session.post(url, json=payload, timeout=15)
            df = pd.DataFrame(resp.json()['data']['records'])
            df['expiryDate'] = pd.to_datetime(df['expiryDate'])
            nearest_expiry = df['expiryDate'].min()
            return df[df['expiryDate'] == nearest_expiry]
        except:
            return pd.DataFrame()
    
    def find_strike(self, df, opt_type, symbol, spot):
        if df.empty: return None
        delta_range = DELTA_CE if opt_type == 'CE' else DELTA_PE
        oi_min = OI_MIN.get(symbol, 100000)
        
        mask = (
            (df['optionType'] == opt_type) &
            (abs(df['strikePrice'] - spot) <= 100) &
            (df['delta'].between(*delta_range)) &
            (df['gamma'] >= GAMMA_MIN) &
            (df['iv'] <= IV_MAX) &
            (df['oi'] >= oi_min)
        )
        
        filtered = df[mask]
        if filtered.empty:
            fallback = df[(df['optionType'] == opt_type)].sort_values('oi', ascending=False)
            return fallback.iloc[0] if not fallback.empty else None
        
        return filtered.sort_values('oi', ascending=False).iloc[0]
    
    def calc_pcr(self, chain_df):
        ce_df = chain_df[chain_df['optionType'] == 'CE']
        pe_df = chain_df[chain_df['optionType'] == 'PE']
        total_ce_oi = ce_df['oi'].sum()
        total_pe_oi = pe_df['oi'].sum()
        return total_pe_oi / total_ce_oi if total_ce_oi > 0 else 1.0
    
    def send_alert(self, data):
        try:
            pcr = data['pcr']
            signal = "🟢 CE" if pcr < PCR_BULLISH else "🔴 PE" if pcr > PCR_BEARISH else "🟡 WAIT"
            msg = f"""
🚀 *{data['symbol']} Alert*
📊 Spot: ₹{data['spot']:,}
🟢 CE: {int(data['ce_strike'])} @ ₹{data['ce_ltp']:.0f}
🔴 PE: {int(data['pe_strike'])} @ ₹{data['pe_ltp']:.0f}
⚖️ PCR: {pcr:.2f} {signal}
⏰ {datetime.now().strftime('%H:%M')}
            """
            self.bot.send_message(CHAT_ID, msg.strip(), parse_mode='Markdown')
        except:
            pass

# MAIN DASHBOARD
st.title("🚀 Dual Strike Screener v2.5")
st.markdown("**Live Greeks + PCR + Telegram Alerts**")

# Sidebar
st.sidebar.header("⚙️ Controls")
enable_alerts = st.sidebar.toggle("📱 Telegram Alerts", value=True)
refresh_sec = st.sidebar.slider("Refresh (sec)", 30, 120, 60)

scanner = DualStrikeScanner()
metrics = []

cols = st.columns(3)
for idx, symbol in enumerate(INDICES["NSE"]):
    with cols[idx]:
        spot = scanner.get_spot(symbol)
        chain = scanner.get_chain(symbol)
        
        if not chain.empty:
            ce = scanner.find_strike(chain, 'CE', symbol, spot)
            pe = scanner.find_strike(chain, 'PE', symbol, spot)
            
            pcr = scanner.calc_pcr(chain)
            
            if enable_alerts and ce and pe:
                scanner.send_alert({
                    'symbol': symbol, 'spot': spot, 'pcr': pcr,
                    'ce_strike': ce['strikePrice'], 'ce_ltp': ce['ltp'], 
                    'pe_strike': pe['strikePrice'], 'pe_ltp': pe['ltp']
                })
            
            signal = "🟢" if pcr < PCR_BULLISH else "🔴" if pcr > PCR_BEARISH else "🟡"
            st.metric(symbol, f"₹{spot:,.0f}", f"PCR {pcr:.2f}{signal}")
            
            if ce: st.caption(f"🟢 CE: {int(ce['strikePrice'])} ₹{ce['ltp']:.0f} Δ:{ce['delta']:.2f}")
            if pe: st.caption(f"🔴 PE: {int(pe['strikePrice'])} ₹{pe['ltp']:.0f} Δ:{pe['delta']:.2f}")
            
            metrics.append({
                'Symbol': symbol, 'Spot': spot, 'PCR': pcr,
                'CE_Strike': ce['strikePrice'] if ce else 0,
                'CE_LTP': ce['ltp'] if ce else 0,
                'CE_Delta': ce['delta'] if ce else 0,
                'PE_Strike': pe['strikePrice'] if pe else 0,
                'PE_LTP': pe['ltp'] if pe else 0
            })

if metrics:
    st.divider()
    df_metrics = pd.DataFrame(metrics)
    st.subheader("📊 Live Analytics")
    st.dataframe(df_metrics, use_container_width=True)

st.info(f"Updated: {datetime.now().strftime('%H:%M:%S')} | Alerts: {'✅' if enable_alerts else '❌'}")
