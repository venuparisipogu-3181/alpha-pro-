import streamlit as st
import pandas as pd
from dhanhq import dhanhq
import requests
from datetime import datetime, timedelta
from streamlit_autorefresh import st_autorefresh

# ---------------- PAGE CONFIG ----------------
st.set_page_config(page_title="Alpha PRO Monitor", layout="wide", page_icon="🏹")

# ---------------- SESSION STATE ----------------
if "monitor_active" not in st.session_state:
    st.session_state.monitor_active = False
if "tracked_trade" not in st.session_state:
    st.session_state.tracked_trade = None

# ---------------- API SETUP ----------------
try:
    dhan = dhanhq(
        st.secrets["DHAN_CLIENT_ID"],
        st.secrets["DHAN_ACCESS_TOKEN"]
    )
except:
    st.error("❌ Dhan Secrets missing")
    st.stop()

# ---------------- AUTO REFRESH (NON BLOCKING) ----------------
st_autorefresh(interval=15000, key="auto_refresh")

# ---------------- UTILITIES ----------------
def next_weekly_expiry():
    today = datetime.today()
    thursday = today + timedelta((3 - today.weekday()) % 7)
    return thursday.strftime("%Y-%m-%d")

@st.cache_data(ttl=10)
def get_option_chain(sec_id, seg, expiry):
    return dhan.option_chain(
        under_security_id=int(sec_id),
        under_exchange_segment=seg,
        expiry=expiry
    )

def calculate_pcr(df):
    ce = df[df["type"] == "CE"]["oi"].sum()
    pe = df[df["type"] == "PE"]["oi"].sum()
    return round(pe / ce, 2) if ce > 0 else 1.0

def score_logic(row, pcr, side):
    score = 0

    oi_chg = row.get("oi_change", 0)
    iv = row.get("iv", 0)

    if oi_chg > 2000:
        score += 40
    elif oi_chg > 1000:
        score += 25

    if 15 <= iv <= 30:
        score += 20

    if side == "CALL" and pcr < 0.9:
        score += 10
    if side == "PUT" and pcr > 1.1:
        score += 10

    return score

def telegram_alert(title, msg):
    token = st.secrets.get("TELEGRAM_BOT_TOKEN")
    chat_id = st.secrets.get("TELEGRAM_CHAT_ID")
    if token and chat_id:
        requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            data={"chat_id": chat_id, "text": msg}
        )

# ---------------- UI ----------------
st.title("🏹 Alpha PRO Monitor")

indices = {
    "NIFTY": {"id": 13, "seg": "IDX_I"},
    "BANKNIFTY": {"id": 25, "seg": "IDX_I"},
    "SENSEX": {"id": 1, "seg": "IDX_I"}
}

side = st.sidebar.selectbox("Option Side", ["CALL", "PUT"])
opt_type = "CE" if side == "CALL" else "PE"
expiry = next_weekly_expiry()

cols = st.columns(3)

# ---------------- SCREENER ----------------
for i, (name, cfg) in enumerate(indices.items()):
    with cols[i]:
        st.subheader(name)

        resp = get_option_chain(cfg["id"], cfg["seg"], expiry)

        if not resp or resp.get("status") != "success":
            st.warning("Option chain unavailable")
            continue

        df = pd.DataFrame(resp["data"])
        if df.empty:
            st.warning("No data")
            continue

        pcr = calculate_pcr(df)
        spot = resp.get("underlyingValue", 0)

        st.metric("SPOT", f"{spot}", f"PCR {pcr}")

        df_side = df[df["type"] == opt_type].copy()
        if df_side.empty:
            st.warning("No strikes")
            continue

        df_side["SCORE"] = df_side.apply(
            lambda x: score_logic(x, pcr, side), axis=1
        )

        df_side = df_side.sort_values("SCORE", ascending=False)
        best = df_side.iloc[0]

        st.success(f"BEST: {best['strike_price']} | SCORE {best['SCORE']}")

        if st.button(f"TRACK {name}", key=name):
            st.session_state.monitor_active = True
            st.session_state.tracked_trade = {
                "name": name,
                "id": cfg["id"],
                "strike": best["strike_price"],
                "type": opt_type,
                "entry": best["last_price"],
                "expiry": expiry
            }

            telegram_alert(
                f"{name} ENTRY",
                f"{best['strike_price']} {opt_type}\nEntry: {best['last_price']}"
            )
            st.rerun()

        st.dataframe(
            df_side[["strike_price", "last_price", "oi_change", "SCORE"]].head(5),
            use_container_width=True
        )

# ---------------- LIVE MONITOR ----------------
if st.session_state.monitor_active:
    st.divider()
    t = st.session_state.tracked_trade
    st.header(f"LIVE: {t['name']} {t['strike']} {t['type']}")

    mon = get_option_chain(t["id"], "IDX_I", t["expiry"])
    if mon and mon.get("status") == "success":
        mdf = pd.DataFrame(mon["data"])
        row = mdf[
            (mdf["strike_price"] == t["strike"]) &
            (mdf["type"] == t["type"])
        ]

        if not row.empty:
            row = row.iloc[0]
            ltp = row["last_price"]
            pnl = round(ltp - t["entry"], 2)

            c1, c2, c3 = st.columns(3)
            c1.metric("ENTRY", t["entry"])
            c2.metric("LTP", ltp, f"{pnl}")
            c3.metric("OI Δ", row["oi_change"])

            if st.button("EXIT TRADE"):
                telegram_alert(
                    f"{t['name']} EXIT",
                    f"{t['strike']} {t['type']}\nExit: {ltp}\nPnL: {pnl}"
                )
                st.session_state.monitor_active = False
                st.rerun()
