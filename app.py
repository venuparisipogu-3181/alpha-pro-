import streamlit as st
import pandas as pd
import requests
from datetime import datetime
from telegram import Bot
from telegram.error import TelegramError

try:
    from config import *
except ImportError:
    st.error("❌ config.py missing! cp config_template.py config.py")
    st.stop()

st.set_page_config(page_title="Dual Strike Screener", layout="wide")

class Scanner:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({"access-token": DHAN_TOKEN})
        self.bot = Bot(token=TELEGRAM_TOKEN) if TELEGRAM_TOKEN != "your_token" else None

# Main dashboard code (same logic as before but fixed loops)
st.title("🚀 Dual Strike Screener")
# ... rest of working code
