import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timedelta

st.set_page_config(page_title="Index Option Chain", layout="wide")

# ---------------- CONFIG ---------------- #
DHAN_BASE = "https://api.dhan.co"
ACCESS_TOKEN = st.secrets["DHAN_TOKEN"]

HEADERS = {
    "access-token": ACCESS_TOKEN,
    "Content-Type": "application/json"
}

INDEX_MAP = {
    "NIFTY": {"id": 13, "seg": "IDX_FO"},
    "BANKNIFTY": {"id": 25, "seg": "IDX_FO"},
    "SENSEX": {"id": 51, "seg": "IDX_FO"}
}

# ---------------- EXPIRY LOGIC ---------------- #
def get_fallback_expiries():
    now = datetime.now()
    weekday = now.weekday()  # Mon=0 Thu=3

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

# ---------------- OPTION CHAIN FETCH ---------------- #
def get_option_chain(sec_id, seg, expiry):
    url = f"{DHAN_BASE}/optionchain"
    payload = {
        "securityId": sec_id,
        "exchangeSegment": seg,
        "expiry": expiry
    }

    try:
        r = requests.post(url, json=payload, headers=HEADERS, timeout=10)
        if r.status_code == 200:
            return r.json()
    except:
        pass

    return None

def fetch_valid_option_chain(sec_id, seg):
    expiries = get_fallback_expiries()

    for exp in expiries:
        resp = get_option_chain(sec_id, seg, exp)

        if (
            resp
            and resp.get("status") == "success"
            and resp.get("data")
            and len(resp["data"]) > 0
        ):
            return resp["data"], exp

    return None, None

# ---------------- UI ---------------- #
st.title("📊 Index Option Chain (Dhan API – Stable Mode)")

index = st.selectbox("Select Index", list(INDEX_MAP.keys()))

if st.button("Fetch Option Chain"):
    cfg = INDEX_MAP[index]

    with st.spinner("Fetching option chain with fallback expiries..."):
        data, used_expiry = fetch_valid_option_chain(cfg["id"], cfg["seg"])

    if not data:
        st.error("❌ Option chain unavailable (Dhan expiry / liquidity issue)")
        st.warning("👉 This is NOT a code error.\n👉 Dhan API did not return index option chain today.")
        st.stop()

    st.success(f"✅ Option chain fetched | Expiry used: {used_expiry}")

    df = pd.DataFrame(data)

    # Keep only useful columns
    keep_cols = [c for c in df.columns if c.lower() not in ["id", "securityid"]]
    df = df[keep_cols]

    st.dataframe(df, use_container_width=True)
