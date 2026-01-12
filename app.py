import streamlit as st
import yfinance as yf
import requests

st.title("Alpha Pro Nifty Trading Bot")
st.markdown("---")

# Telegram Configuration
st.subheader("Telegram Setup")
token = st.text_input("Bot Token (from BotFather)", type="password")
chat_id = st.text_input("Chat ID (your group/channel)", type="password")

def send_telegram_alert(message):
    if token and chat_id:
        url = "https://api.telegram.org/bot" + token + "/sendMessage"
        data = {"chat_id": chat_id, "text": message}
        try:
            requests.post(url, data=data)
            st.success("✅ Alert Sent Successfully!")
            return True
        except:
            st.error("❌ Check Token/Chat ID")
            return False
    else:
        st.warning("⚠️ Enter Token and Chat ID first")
        return False

# Trading Analysis
st.subheader("Live NIFTY Analysis")
index_choice = st.selectbox("Select Index", ["NIFTY 50", "^NSEBANK"])

if st.button("🚀 ANALYZE & GET SIGNALS", type="primary"):
    try:
        # Get live price (SAFE method)
        ticker = yf.Ticker(index_choice)
        hist = ticker.history(period="1d")
        current_price = round(float(hist['Close'][-1]))
        
        # Calculate ATM strike
        step_size = 50 if "NIFTY" in index_choice else 100
        atm_strike = (current_price // step_size) * step_size
        
        # Display live data
        col1, col2, col3 = st.columns(3)
        col1.metric("💰 Current Price", f"₹{current_price}")
        col2.metric("🎯 ATM Strike", f"{atm_strike}")
        col3.metric("📊 Time", "Live")
        
        st.markdown("---")
        
        # Trading Signals (Simple & Reliable)
        if current_price > 25600:
            signal = "🟢 CE BUY"
            option = f"{atm_strike} CE"
            reason = "Bullish Momentum"
            target = current_price + 60
            stoploss = current_price - 30
            
            st.success(signal)
            st.info(f"**Trade:** BUY {option}")
            st.info(f"**Entry:** ₹{current_price}")
            st.info(f"**Target:** ₹{target}")
            st.info(f"**Stoploss:** ₹{stoploss}")
            
            alert_message = f"""🎯 PERFECT ENTRY: NIFTY 50

🟢 Action: BUY {atm_strike} CE
📊 Reason: {reason}
💰 Entry: ₹{current_price}
🎯 Target: ₹{target}
🛑 Stoploss: ₹{stoploss}
🔄 Trailing: 15 pts
🏁 Exit: Reverse Signal or SL"""
            
            if st.button("📱 SEND PERFECT ALERT"):
                send_telegram_alert(alert_message)
                
        elif current_price < 25500:
            signal = "🔴 PE BUY"
            option = f"{atm_strike} PE"
            reason = "Bearish Momentum"
            target = current_price + 60
            stoploss = current_price - 30
            
            st.error(signal)
            st.info(f"**Trade:** BUY {option}")
            st.info(f"**Entry:** ₹{current_price}")
            st.info(f"**Target:** ₹{target}")
            st.info(f"**Stoploss:** ₹{stoploss}")
            
            alert_message = f"""🎯 PERFECT ENTRY: NIFTY 50

🔴 Action: BUY {atm_strike} PE
📊 Reason: {reason}
💰 Entry: ₹{current_price}
🎯 Target: ₹{target}
🛑 Stoploss: ₹{stoploss}
🔄 Trailing: 15 pts
🏁 Exit: Reverse Signal or SL"""
            
            if st.button("📱 SEND PERFECT ALERT"):
                send_telegram_alert(alert_message)
                
        else:
            st.warning("😐 WAIT - Sideways Market")
            
    except Exception as e:
        st.error("📴 Market Closed (9:15 AM - 3:30 PM IST)")

# Auto Refresh Button
st.markdown("---")
if st.button("🔄 REFRESH DATA"):
    st.rerun()

# Instructions
with st.expander("📋 Quick Setup Guide"):
    st.markdown("""
    **1. Create Telegram Bot:**
    - Message @BotFather → /newbot
    - Copy Bot Token
    
    **2. Get Chat ID:**
    - Add bot to group → Send message
    - Visit: `https://api.telegram.org/bot<TOKEN>/getUpdates`
    - Copy "chat":{"id":-xxxxx}
    
    **3. Deploy:**
    - GitHub → New repo "nifty-bot"
    - Upload app.py + requirements.txt
    - share.streamlit.io → Deploy
    
    **4. Mobile App:**
    - Chrome → Deployed URL
    - Add to Home Screen ✅
    """)
