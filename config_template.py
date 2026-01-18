# Rename this file to config.py and add your tokens
DHAN_TOKEN = "ఇక్కడ_మీ_TOKEN_రాయండి"
TELEGRAM_TOKEN = "ఇక్కడ_మీ_BOT_TOKEN_రాయండి"
CHAT_ID = "ఇక్కడ_మీ_CHAT_ID_రాయండి"

# Index Support
INDICES = {
    "NSE": ["NIFTY", "BANKNIFTY", "FINNIFTY"],
    "BSE": ["SENSEX"]
}

# Strategy Logic
DELTA_CE = (0.25, 0.50)
DELTA_PE = (-0.50, -0.25)
GAMMA_MIN = 0.03
IV_MAX = 35
OI_MIN = {"NIFTY": 500000, "BANKNIFTY": 200000}
