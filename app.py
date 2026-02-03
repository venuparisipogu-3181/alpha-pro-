import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
from streamlit_autorefresh import st_autorefresh
import requests

# ---------------- PAGE CONFIG ----------------
st.set_page_config(
    page_title="PRO Strike Dashboard (Cloud Safe)",
    layout="wide"
)

# ---------------- TELEGRAM ----------------
def telegram_alert(title, message):
    try:
        token = st.secrets.get("TELEGRAM_BOT_TOKEN", "")
        chat_id = st.secrets.get("TELEGRAM_CHAT_ID", "")
        if not token or not chat_id:
            return
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        requests.post(url, data={"chat_id": chat_id, "text": f"🚨 {title}\n\n{message}"})
    except:
        pass

# ---------------- SESSION STATE ----------------
if "monitor" not in st.session_state:
    st.session_state.monitor = False
if "entry_price" not in st.session_state:
    st.session_state.entry_price = 100
if "strike" not in st.session_state:
    st.session_state.strike = 25000
if "side" not in st.session_state:
    st.session_state.side = "CE"

# ---------------- SCORE LOGIC ----------------
def pro_score(oi_change, delta, iv):
    score = 0
    if oi_change > 2000:
        score += 40
    if 0.25 <= abs(delta) <= 0.40:
        score += 30
    if 15 <= iv <= 25:
        score += 30
    return score

# ---------------- DATA (SIMULATION – HONEST) ----------------
def get_index_data(name):
    base = {"NIFTY": 25000, "BANKNIFTY": 51000, "SENSEX": 81500}[name]
    step = {"NIFTY": 50, "BANKNIFTY": 100, "SENSEX": 50}[name]

    rows = []
    for i in range(-3, 4):
        strike = base + i * step
        ltp = max(5, 100 - abs(i) * 15 + np.random.randint(-10, 10))
        oi_change = np.random.randint(-1500, 3500)
        delta = round(0.5 - abs(i) * 0.1, 2)
        iv = np.random.randint(15, 25)
        score = pro_score(oi_change, delta, iv)

        rows.append({
            "Strike": strike,
            "LTP": ltp,
            "OI Δ": oi_change,
            "Delta": delta,
            "IV": iv,
            "Score": score
        })

    df = pd.DataFrame(rows)
    best = df.loc[df["Score"].idxmax()]
    return df, best

# ---------------- HEADER ----------------
st.title("🔥 PRO Strike Dashboard (Cloud Safe)")
st.caption("⚠️ Simulation only – No live NSE data")

side = st.selectbox("Option Type", ["CE", "PE"])

# ---------------- SCREENER ----------------
c1, c2, c3 = st.columns(3)

for col, name in zip([c1, c2, c3], ["NIFTY", "BANKNIFTY", "SENSEX"]):
    with col:
        st.subheader(name)
        df, best = get_index_data(name)
        st.success(f"BEST {side} → {best['Strike']} | Score {best['Score']}")
        st.metric("LTP", f"₹{best['LTP']}")
        if st.button(f"START {name}", key=name):
            st.session_state.monitor = True
            st.session_state.entry_price = best["LTP"]
            st.session_state.strike = best["Strike"]
            st.session_state.side = side
            telegram_alert(
                f"{name} ENTRY",
                f"{best['Strike']} {side}\nEntry ₹{best['LTP']}"
            )
        st.dataframe(df, use_container_width=True, height=250)

# ---------------- LIVE MONITOR ----------------
st.divider()
st.header("🔴 Live Monitor")

if st.session_state.monitor:
    # SAFE AUTO REFRESH (2 sec)
    st_autorefresh(interval=2000, key="live_refresh")

    entry = st.session_state.entry_price
    strike = st.session_state.strike
    side = st.session_state.side

    # Simulated movement
    ltp = max(5, entry + np.random.randint(-25, 40))
    oi_change = np.random.randint(-2000, 3000)

    target = entry + 60
    sl = entry - 30

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Strike", f"{strike} {side}")
    m2.metric("LTP", f"₹{ltp}", f"{ltp-entry:+}")
    m3.metric("TARGET", f"₹{target}")
    m4.metric("SL", f"₹{sl}")

    if ltp >= target:
        st.success("🎯 TARGET HIT – SELL")
        telegram_alert("TARGET HIT", f"{strike} {side} @ {ltp}")
        st.session_state.monitor = False

    elif ltp <= sl:
        st.error("🛑 STOPLOSS HIT – EXIT")
        telegram_alert("STOPLOSS HIT", f"{strike} {side} @ {ltp}")
        st.session_state.monitor = False

    elif oi_change < -1000:
        st.error("🔴 OI COLLAPSE – EMERGENCY EXIT")
        telegram_alert("OI COLLAPSE", f"{strike} {side}")
        st.session_state.monitor = False

    st.metric("OI Change", oi_change)

    if st.button("STOP MONITOR"):
        st.session_state.monitor = False

else:
    st.info("No active trade")

st.divider()
st.success("✅ Cloud-Safe | No buffering | No infinite loops")
