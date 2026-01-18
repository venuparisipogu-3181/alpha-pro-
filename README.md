# 🚀 Dual Strike Screener v2.5

[![Streamlit](https://img.shields.io/badge/Streamlit-FF4B4B?style=for-the-badge&logo=streamlit&logoColor=white)](https://dual-strike-screener.streamlit.app)
[![Telegram](https://img.shields.io/badge/Telegram-0088cc?style=for-the-badge&logo=telegram&logoColor=white)](https://t.me/dualstrikealerts)
[![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![License:MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

**AI Options Trading Dashboard** - Live Greeks + PCR + Multi-Index + Telegram Alerts

## ✨ Features
- ✅ **Live Greeks** Δ/γ/IV/OI Real-time Analysis
- ✅ **PCR Signals** 🟢CE/🔴PE/🟡WAIT Auto Detection
- ✅ **Multi-Index** NIFTY/BANKNIFTY/FINNIFTY
- ✅ **Streamlit Dashboard** + **Telegram Bot**
- ✅ **Custom Strategy** Configurable Logic

## 🚀 Quick Setup (5 Minutes)

```bash
git clone https://github.com/YOUR_USERNAME/dual-strike-screener.git
cd dual-strike-screener
pip install -r requirements.txt

# Setup API Keys
cp config_template.py config.py
# Edit config.py → DhanHQ + Telegram tokens

streamlit run app.py
