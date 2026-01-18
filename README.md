# 🚀 Dual Strike Screener v2.5

[![Streamlit](https://img.shields.io/badge/Streamlit-FF4B4B?style=for-the-badge&logo=streamlit&logoColor=white)](http://localhost:8501)
[![Telegram](https://img.shields.io/badge/Telegram-0088cc?style=for-the-badge&logo=telegram&logoColor=white)](https://t.me/yourbot)
[![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)

**Live Options Greeks + PCR + AI Strike Selection + Telegram Alerts**

## ✨ Features
- 🟢 **Live Greeks** (Delta/Gamma/IV/OI)
- 🟢 **PCR Signals** (CE/PE/WAIT)
- 🟢 **Multi-Index** (NIFTY/BANKNIFTY)
- 🟢 **Streamlit Dashboard**
- 🟢 **Telegram Auto Alerts**

## 🚀 5-Minute Setup
```bash
git clone YOUR_REPO_URL
cd dual-strike-screener
pip install -r requirements.txt
cp config_template.py config.py
# Edit config.py → Add DhanHQ + Telegram keys
streamlit run app.py
