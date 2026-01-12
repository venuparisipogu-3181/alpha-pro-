import streamlit as st
import yfinance as yf
import pandas_ta as ta
import requests
import pandas as pd

st.title("Alpha Pro")

token = st.text_input("Bot Token")
chatid = st.text_input("Chat ID")

def send_alert(msg):
    url = "https://api.telegram.org/bot"+token+"/sendMessage"
    data = {"chat_id": chatid, "text": msg}
    requests.post(url, data=data)

index_sel = st.selectbox("Index", ["NIFTY 50", "BANKNIFTY"])
symbols = {"NIFTY 50": "^NSEI", "BANKNIFTY": "^NSEBANK"}

if st.button("ANALYZE"):
    df = yf.download(symbols[index_sel], period="1d")
    df['EMA'] = ta.ema(df['Close'], 20)
    df['RSI'] = ta.rsi(df['Close'], 14)
    
    price = df['Close'].iloc[-1]
    ema = df['EMA'].iloc[-1]
    rsi = df['RSI'].iloc[-1]
    
    step = 50 if "NIFTY" in index_sel else 100
    strike = int(round(price/step)*step)
    
    st.metric("Price", round(price))
    st.metric("RSI", round(rsi,1))
    
    if price > ema and rsi > 55:
        msg = "BUY "+str(strike)+" CE Rs"+str(round(price))
        st.success(msg)
        if st.button("Send Alert"):
            send_alert(msg)
    else:
        st.info("WAIT")
    
    st.line_chart(df[['Close','EMA']].tail(30))
