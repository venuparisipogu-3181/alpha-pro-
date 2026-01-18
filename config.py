# API Credentials
DHAN_TOKEN = "ఇక్కడ_మీ_DHAN_TOKEN"
TELEGRAM_TOKEN = "ఇక్కడ_మీ_BOT_TOKEN"
CHAT_ID = "ఇక్కడ_మీ_CHAT_ID"

# Multi-Index Support
INDICES = {
    "NSE": ["NIFTY", "BANKNIFTY", "FINNIFTY"],
    "BSE": ["SENSEX"]
}

# Strategy Thresholds
DELTA_CE = (0.25, 0.50)
DELTA_PE = (-0.50, -0.25) 
GAMMA_MIN = 0.03
IV_MAX = 35
OI_MIN = {
    "NIFTY": 500000,
    "BANKNIFTY": 200000,
    "FINNIFTY": 300000,
    "SENSEX": 100000
}
