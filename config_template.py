# 🚀 Dual Strike Screener v2.5 - SETUP INSTRUCTIONS
"""
1️⃣ DhanHQ Token: https://dhanhq.co/developer → API Access Token
2️⃣ Telegram Bot: 
   → @BotFather → /newbot → Copy TOKEN (712345:AAExxx...)
   → @userinfobot → Forward message → Copy CHAT_ID
3️⃣ cp config_template.py config.py → Paste YOUR keys!

⚠️ NEVER commit config.py to GitHub!
"""

# === API KEYS (REPLACE WITH YOURS) ===
DHAN_TOKEN = "YOUR_DHANHQ_ACCESS_TOKEN_HERE"
TELEGRAM_TOKEN = "7123456789:AAExxxYOUR_BOT_TOKEN_HERE"
CHAT_ID = "123456789"  # Your Telegram Chat ID

# === STRATEGY SETTINGS ===
INDICES = {
    "NSE": ["NIFTY", "BANKNIFTY", "FINNIFTY"]
}

# Greeks Filters (Intraday Best)
DELTA_CE = (0.25, 0.50)     # OTM-ATM Calls
DELTA_PE = (-0.50, -0.25)   # OTM-ATM Puts
GAMMA_MIN = 0.03            # ATM Sensitivity
IV_MAX = 35                 # Cheap Premiums Only

# OI Thresholds (High Liquidity)
OI_MIN = {
    "NIFTY": 500000,
    "BANKNIFTY": 200000,
    "FINNIFTY": 100000
}

# PCR Signals
PCR_BULLISH = 0.8      # PCR < 0.8 → CE Buy
PCR_BEARISH = 1.3      # PCR > 1.3 → PE Buy
PCR_NEUTRAL = (0.8, 1.3)  # Sideways
