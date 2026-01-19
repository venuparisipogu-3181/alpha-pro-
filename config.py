#!/usr/bin/env python3
"""
Dual Strike Screener - API Configuration Template
🚀 Copy this to config.py and add your API keys
"""

# DhanHQ API (get from dhanhq.co/developer)
DHAN_TOKEN = "YOUR_DHANHQ_ACCESS_TOKEN"

# Telegram Bot (get from @BotFather + @userinfobot)
TELEGRAM_TOKEN = "7123456789:AAExxxxxxxxxxxxxxxxxx"
CHAT_ID = "123456789"

# Trading Strategy Settings
INDICES = {
    "NSE": ["NIFTY", "BANKNIFTY", "FINNIFTY"]
}

# Greeks Filters
DELTA_CE = (0.25, 0.50)      # Call options delta range
DELTA_PE = (-0.50, -0.25)    # Put options delta range
GAMMA_MIN = 0.03             # Minimum gamma
IV_MAX = 35                  # Maximum implied volatility
OI_MIN = {
    "NIFTY": 500000,
    "BANKNIFTY": 200000,
    "FINNIFTY": 300000
}

# PCR Signals
PCR_BULLISH = 0.85           # PCR < 0.85 → CE BUY
PCR_BEARISH = 1.25           # PCR > 1.25 → PE BUY
