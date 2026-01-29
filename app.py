import streamlit as st
import pandas as pd
from dhanhq import dhanhq
from datetime import datetime, timedelta
import time
import requests

# ---------------- CONFIG ----------------
st.set_page_config("Alpha PRO Monitor", "🏹", layout="wide")

# ---------------- SECRETS ----------------
try:
    dhan = dhanhq(
        st.secrets["DHAN_CLIENT_ID"],
        st.secrets["DHAN_ACCESS_TOKEN"]
    )
except:
    st.error("❌ DHAN secrets missing")
    st.stop()

# ---------------- SESSION ----------------
if "active" not in st.session_state:
    st.session_state.active = False
if "trade" not in st.session_state:
    st.session_state.trade = None

# ---------------- INDICES ----------------
INDICES = {
    "NIFTY": {"id": 13, "seg": "IDX_I"},
    "BANKNIFTY": {"id": 25, "seg": "IDX_I"},
    "SENSEX": {"id": 1, "seg": "IDX_I"},
}

# ---------------- EXPIRY LOGIC (CRITICAL) ----------------
def get_fallback_expiries():
    now = datetime.now()
    weekday = now.weekday()  # Thu = 3

    base = now + timedelta((3 - weekday) % 7)
    expiries = []

    if weekday == 3:  # expiry day
        expiries.append(base + timedelta(days=7))
        expiries.append(base + timedelta(days=14))
    else:
        expiries.append(base)
        expiries.append(base + timedelta(days=7))
        expiries.append(base + timedelta(days=14))

    return [e.strftime("%Y-%m-%d") for e in expiries]

def fetch_option_chain_safe(sec_id, seg):
    for exp in get_fallback_expiries():
        try:
            resp = dhan.option_chain(
                under_security_id=int(sec_id),
                under_exchange_segment=seg,
                expiry=exp
            )
            if resp and resp.get("status") == "success" and resp.get("data"):
                return resp, exp
        except:
            continue
    return None, None

# ---------------- HELPERS ----------------
def calculate_pcr(df):
    ce = df[df["type"] == "CE"]["oi"].sum()
    pe = df[df["type"] == "PE"]["oi"].sum()
    return round(pe / ce, 2) if ce > 0 else 1

def score_row(row, pcr, side):
    score = 0
    if row.get("oi_change", 0) >= 2000:
        score += 40
    if 15 <= row.get("iv", 0) <= 22:
        score += 20
    if (side == "CALL" and pcr < 0.9) or (side == "PUT" and pcr > 1.1):
        score += 20
    return score

def telegram_alert(msg):
    try:
        requests.post(
            f"https://api.telegram.org/bot{st.secrets['TELEGRAM_BOT_TOKEN']}/sendMessage",
            data={"chat_id": st.secrets["TELEGRAM_CHAT_ID"], "text": msg}
        )
    except:
        pass

# ---------------- UI ----------------
st.title("🏹 Alpha PRO Monitor (Expiry-Safe)")

side = st.sidebar.selectbox("Option Side", ["CALL", "PUT"])
otype = "CE" if side == "CALL" else "PE"

cols = st.columns(3)

for i, (name, cfg) in enumerate(INDICES.items()):
    with cols[i]:
        st.subheader(name)

        resp, used_expiry = fetch_option_chain_safe(cfg["id"], cfg["seg"])

        if not resp:
            st.error("❌ Option chain unavailable (Dhan expiry issue)")
            continue

        df = pd.DataFrame(resp["data"])
        pcr = calculate_pcr(df)
        spot = resp.get("underlyingValue", 0)

        st.metric("SPOT", spot, f"PCR {pcr}")
        st.caption(f"Using Expiry: {used_expiry}")

        side_df = df[df["type"] == otype].copy()
        side_df["SCORE"] = side_df.apply(
            lambda x: score_row(x, pcr, side), axis=1
        )

        side_df = side_df.sort_values("SCORE", ascending=False)
        best = side_df.iloc[0]

        st.success(f"BEST: {best['strike_price']} | SCORE {best['SCORE']}")

        if st.button(f"TRACK {name}", key=name):
            st.session_state.active = True
            st.session_state.trade = {
                "name": name,
                "id": cfg["id"],
                "seg": cfg["seg"],
                "expiry": used_expiry,
                "strike": best["strike_price"],
                "type": otype,
                "entry": best["last_price"]
            }
            telegram_alert(f"{name} ENTRY {best['strike_price']} {otype}")
            st.experimental_rerun()

        st.dataframe(
            side_df[["strike_price", "last_price", "oi_change", "SCORE"]].head(5),
            use_container_width=True
        )

# ---------------- LIVE MONITOR ----------------
if st.session_state.active:
    st.divider()
    t = st.session_state.trade

    st.header(f"LIVE: {t['name']} {t['strike']} {t['type']}")

    resp, _ = fetch_option_chain_safe(t["id"], t["seg"])

    if resp:
        df = pd.DataFrame(resp["data"])
        row = df[
            (df["strike_price"] == t["strike"]) &
            (df["type"] == t["type"])
        ].iloc[0]

        pnl = row["last_price"] - t["entry"]

        c1, c2, c3 = st.columns(3)
        c1.metric("ENTRY", t["entry"])
        c2.metric("LTP", row["last_price"], f"{pnl:+.2f}")
        c3.metric("OI CHG", row["oi_change"])

        if st.button("EXIT"):
            telegram_alert(f"{t['name']} EXIT {row['last_price']}")
            st.session_state.active = False
            st.experimental_rerun()

# ---------------- AUTO REFRESH ----------------
st.info("Auto refresh every 20 seconds")
time.sleep(20)
st.experimental_rerun()
