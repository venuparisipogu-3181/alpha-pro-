import streamlit as st
import pandas as pd
import requests
import time
from datetime import datetime
from telegram import Bot

# --- CONFIG/SECRETS LOADING ---
try:
    from config import *
except ImportError:
    DHAN_TOKEN = st.secrets.get("DHAN_TOKEN", "MISSING")
    TELEGRAM_TOKEN = st.secrets.get("TELEGRAM_TOKEN", "MISSING")
    CHAT_ID = st.secrets.get("CHAT_ID", "MISSING")
    from config_template import INDICES, DELTA_CE, DELTA_PE, GAMMA_MIN, IV_MAX, OI_MIN

st.set_page_config(page_title="Dual Strike Screener", layout="wide", page_icon="🚀")
bot = Bot(token=TELEGRAM_TOKEN)

class DhanScanner:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({"access-token": DHAN_TOKEN, "content-type": "application/json"})
        self.last_alerts = {}

    def get_market_data(self, symbol, exchange):
        try:
            # LTP Fetch
            url_ltp = "https://api.dhan.co/charts/v2/ltpc"
            payload_ltp = {"securityId": f"{exchange}_{symbol}_I", "exchangeSegment": f"{exchange}_INDEX"}
            spot = self.session.post(url_ltp, json=payload_ltp, timeout=5).json()['data']['ltp']

            # Option Chain Fetch
            url_oc = "https://api.dhan.co/charts/v2/optionchain"
            payload_oc = {"securityId": f"{exchange}_{symbol}_I", "exchangeSegment": f"{exchange}_FO"}
            resp = self.session.post(url_oc, json=payload_oc, timeout=10).json()
            df = pd.DataFrame(resp['data']['records'])
            df['expiryDate'] = pd.to_datetime(df['expiryDate'])
            nearest_exp = df[df['expiryDate'].dt.date >= datetime.now().date()]['expiryDate'].min()
            return spot, df[df['expiryDate'] == nearest_exp], nearest_exp.strftime('%d-%b')
        except: return 0, pd.DataFrame(), "N/A"

    def find_best_strike(self, df, opt_type):
        if df.empty: return None
        delta_range = DELTA_CE if opt_type == 'CE' else DELTA_PE
        mask = (df['optionType'] == opt_type) & (df['delta'].between(min(delta_range), max(delta_range)))
        filtered = df[mask]
        if filtered.empty: return df[df['optionType'] == opt_type].iloc[0].to_dict()
        return filtered.sort_values('oi', ascending=False).iloc[0].to_dict()

# --- UI LOGIC ---
st.title("📈 Dual Strike Live PCR Screener")
st.sidebar.header("Controls")
run_telegram = st.sidebar.toggle("Enable Telegram Alerts", value=True)
refresh_rate = st.sidebar.slider("Refresh Rate (Seconds)", 30, 300, 60)

scanner = DhanScanner()
placeholder = st.empty()

while True:
    with placeholder.container():
        all_metrics = []
        cols = st.columns(4)
        c_idx = 0
        
        for exch, symbols in INDICES.items():
            for sym in symbols:
                spot, chain, exp = scanner.get_market_data(sym, exch)
                if not chain.empty:
                    ce = scanner.find_best_strike(chain, 'CE')
                    pe = scanner.find_best_strike(chain, 'PE')
                    pcr = round(chain[chain['optionType']=='PE']['oi'].sum() / chain[chain['optionType']=='CE']['oi'].sum(), 2)
                    
                    with cols[c_idx % 4]:
                        st.metric(f"{sym}", f"₹{spot}", f"PCR: {pcr}")
                        st.caption(f"🟢 CE: {int(ce['strikePrice'])} | ₹{ce['ltp']}")
                        st.caption(f"🔴 PE: {int(pe['strikePrice'])} | ₹{pe['ltp']}")
                        st.markdown("---")
                    
                    all_metrics.append({"Symbol": sym, "Spot": spot, "PCR": pcr, "Exp": exp})
                    
                    # Alert Logic
                    if run_telegram:
                        sentiment = "🐂 BULLISH" if pcr >= 1.25 else ("🐻 BEARISH" if pcr <= 0.75 else "")
                        if sentiment and scanner.last_alerts.get(sym) != sentiment:
                            msg = f"{sentiment} *{sym}*\nSpot: ₹{spot} | PCR: `{pcr}`\n🟢 CE: {int(ce['strikePrice'])} @ ₹{ce['ltp']}\n🔴 PE: {int(pe['strikePrice'])} @ ₹{pe['ltp']}"
                            try:
                                bot.send_message(CHAT_ID, msg, parse_mode='Markdown')
                                scanner.last_alerts[sym] = sentiment
                            except: pass
                    c_idx += 1
        
        st.subheader("📊 Summary")
        st.dataframe(pd.DataFrame(all_metrics), use_container_width=True)
        st.info(f"Last Updated: {datetime.now().strftime('%H:%M:%S')}")

    time.sleep(refresh_rate)
    st.rerun()
