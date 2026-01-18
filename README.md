# 🚀 Dual Strike Screener v2.5

[![Streamlit](https://img.shields.io/badge/Streamlit-FF4B4B?style=for-the-badge&logo=streamlit&logoColor=white)](https://dual-strike-screener.streamlit.app)
[![Telegram](https://img.shields.io/badge/Telegram-0088cc?style=for-the-badge&logo=telegram&logoColor=white)](https://t.me/dualstrikebot)
[![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

**AI-Powered Options Trading Dashboard** with Live Greeks, PCR Analysis, Multi-Index Support & Telegram Alerts

## ✨ Features
- ✅ **Live Greeks** (Delta, Gamma, IV, OI Analysis)
- ✅ **PCR Signals** (Bullish/Bearish/Neutral)
- ✅ **Multi-Index** (NIFTY, BANKNIFTY, FINNIFTY)
- ✅ **Streamlit Dashboard** + **Real-time Alerts**
- ✅ **Custom Strategy Logic** (Configurable)

## 📱 Live Demo
[![Dashboard](screenshots/dashboard.png)](https://dual-strike-screener.streamlit.app)

## 🚀 Quick Start (5 Minutes)

```bash
# 1. Clone
git clone https://github.com/YOUR_USERNAME/dual-strike-screener.git
cd dual-strike-screener

# 2. Install
pip install -r requirements.txt

# 3. Setup API Keys
cp config_template.py config.py
# Edit config.py → Add DhanHQ + Telegram tokens

# 4. Run
streamlit run app.py
