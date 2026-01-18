import streamlit as st
import pandas as pd
import requests
import time
from datetime import datetime
from telegram import Bot

# Config ఇంపోర్ట్ చేయడం
try:
    from config import *
except ImportError:
    st.error("❌ config.py దొరకలేదు! GitHub README ఫాలో అవ్వండి.")
    st.stop()

st.set_page_config(page_title="Dhan Live Screener", layout="wide")
bot = Bot(token=TELEGRAM_TOKEN)

class DhanScanner:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({"access-token": DHAN_TOKEN, "content-type": "application/json"})
        self.last_alerts = {}

    def fetch_market_data(self, symbol, exchange):
        try:
            # 1. Spot Price Fetch
            exch_seg = "NSE_INDEX" if exchange == "NSE" else "BSE_INDEX"
            url_ltp = "https://api.dhan.co/charts/v2/ltpc"
            resp_ltp = self.session.post(url_ltp, json={"securityId": f"{exchange}_{symbol}_I", "exchangeSegment": exch_seg}).json()
            spot = resp_ltp['data']['ltp']

            # 2. Option Chain Fetch
            url_oc = "https://api.dhan.co/charts/v2/optionchain"
            exch_fo = "NSE_FO" if exchange == "NSE" else "BSE_FO"
            resp_oc = self.session.post(url_oc, json={"securityId": f"{exchange}_{symbol}_I", "exchangeSegment": exch_fo}).json()
            df = pd.DataFrame(resp_oc['data']['records'])
            
            # Expiry Filtering
            df['expiryDate'] = pd.to_datetime(df['expiryDate'])
            nearest_expiry = df[df['expiryDate'].dt.date >= datetime.now().date()]['expiryDate'].min()
            return spot, df[df['expiryDate'] == nearest_expiry], nearest_expiry.strftime('%d-%b')
        except:
            return 0, pd.DataFrame(), "N/A"

    def select_best_strike(self, df, opt_type):
        delta_range = DELTA_CE if opt_type == 'CE' else DELTA_PE
        mask = (df['optionType'] == opt_type) & (df['delta'].between(min(delta_range), max(delta_range)))
        res = df[mask]
        if not res.empty:
            return res.sort_values('oi', ascending=False).iloc[0].to_dict()
        return None

# UI Layout
st.title("🛡️ Dhan HQ - Multi-Index PCR Streaming")
placeholder = st.empty()
scanner = DhanScanner()

while True:
    with placeholder.container():
        all_data = []
        cols = st.columns(4)
        col_idx = 0
        
        for exch, symbols in INDICES.items():
            for sym in symbols:
                spot, chain, exp = scanner.fetch_market_data(sym, exch)
                if not chain.empty:
                    ce_strike = scanner.select_best_strike(chain, 'CE')
                    pe_strike = scanner.select_best_strike(chain, 'PE')
                    
                    # PCR Calculation
                    total_pe_oi = chain[chain['optionType']=='PE']['oi'].sum()
                    total_ce_oi = chain[chain['optionType']=='CE']['oi'].sum()
                    pcr = round(total_pe_oi / total_ce_oi, 2) if total_ce_oi > 0 else 0
                    
                    with cols[col_idx % 4]:
                        st.subheader(f"{sym}")
                        st.metric("Spot", f"₹{spot}", f"PCR: {pcr}")
                        if ce_strike and pe_strike:
                            st.write(f"🟢 CE: {int(ce_strike['strikePrice'])} | ₹{ce_strike['ltp']}")
                            st.write(f"🔴 PE: {int(pe_strike['strikePrice'])} | ₹{pe_strike['ltp']}")
                    
                    all_data.append({"Symbol": sym, "Spot": spot, "PCR": pcr, "Expiry": exp})
                    
                    # Telegram Alert Logic
                    alert_key = f"{sym}_{exp}"
                    sentiment = "🐂 BULLISH" if pcr > 1.25 else ("🐻 BEARISH" if pcr < 0.75 else "")
                    if sentiment and scanner.last_alerts.get(alert_key) != sentiment:
                        msg = f"{sentiment} Signal! *{sym}*\nSpot: {spot}\nPCR: {pcr}"
                        bot.send_message(CHAT_ID, msg, parse_mode='Markdown')
                        scanner.last_alerts[alert_key] = sentiment
                    col_idx += 1
        
        st.divider()
        st.subheader("📊 Live Chain Analytics")
        st.dataframe(pd.DataFrame(all_data), use_container_width=True)
        st.caption(f"Last Updated: {datetime.now().strftime('%H:%M:%S')}")
        
    time.sleep(60) # ప్రతి నిమిషానికి ఒకసారి అప్‌డేట్
    st.rerun()
