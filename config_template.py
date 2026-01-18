# 🚀 Dual Strike Screener - API KEYS TEMPLATE
"""
SETUP:
1. DhanHQ: dhanhq.co/developer → Token
2. Telegram: @BotFather → /newbot
3. @userinfobot → Chat ID
4. cp config_template.py config.py → Add keys
"""

DHAN_TOKEN = "YOUR_DHANHQ_TOKEN"
TELEGRAM_TOKEN = "7123456789:AAExxxYOUR_BOT_TOKEN"
CHAT_ID = "123456789"

INDICES = {"NSE": ["NIFTY", "BANKNIFTY"]}
DELTA_CE = (0.25, 0.50)
DELTA_PE = (-0.50, -0.25)
GAMMA_MIN = 0.03
IV_MAX = 35
OI_MIN = {"NIFTY": 500000, "BANKNIFTY": 200000}
PCR_BULLISH = 0.8
PCR_BEARISH = 1.3
