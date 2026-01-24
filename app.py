import os
import asyncio
import nest_asyncio
nest_asyncio.apply()

# PRO ALERT FUNCTION
async def pro_alert(index, strike, entry, target, sl):
    try:
        token = os.getenv("TELEGRAM_BOT_TOKEN")
        chat_id = os.getenv("TELEGRAM_CHAT_ID")
        if token and chat_id:
            from telegram import Bot
            bot = Bot(token=token)
            msg = f"""🎯 PERFECT ENTRY: {index}

🟢 Action: BUY {strike} CE
📊 Reason: EMA Support + PCR 1.15
💰 Entry: {entry}
🎯 Target: {target}
🛑 Stoploss: {sl}
🔄 Trailing: 15.0 pts
🏁 Exit: Reverse Signal or SL"""
            await bot.send_message(chat_id=chat_id, text=msg)
            return True
        return False
    except:
        return False

def run_pro_alert(index, strike, entry, target, sl):
    try:
        loop = asyncio.get_event_loop()
        return loop.run_until_complete(pro_alert(index, strike, entry, target, sl))
    except:
        return asyncio.run(pro_alert(index, strike, entry, target, sl))

if st.button("🚀 NIFTY TRACK", key="nifty_btn"):
    strike_num = n_best['Strike']
    entry_price = float(n_best['LTP'].replace('₹', ''))
    target = f"{entry_price + 60:.0f}"
    sl = f"{entry_price - 30:.0f}"
    
    success = run_pro_alert('NIFTY 50', strike_num, f"{entry_price:.0f}", target, sl)
    
    st.session_state.tracked.append({
        'Index': 'NIFTY', 'Strike': n_best['Strike'], 
        'Entry': n_best['LTP'], 'Score': n_best['Score'],
        'Time': datetime.now().strftime('%H:%M')
    })
    st.balloons()
    st.success("✅ NIFTY PRO ALERT!" if success else "📱 Add Secrets")

if st.button("🚀 BANKNIFTY TRACK", key="bank_btn"):
    strike_num = b_best['Strike']
    entry_price = float(b_best['LTP'].replace('₹', ''))
    target = f"{entry_price + 150:.0f}"
    sl = f"{entry_price - 75:.0f}"
    
    success = run_pro_alert('BANKNIFTY 50', strike_num, f"{entry_price:.0f}", target, sl)
    
    st.session_state.tracked.append({
        'Index': 'BANKNIFTY', 'Strike': b_best['Strike'], 
        'Entry': b_best['LTP'], 'Score': b_best['Score'],
        'Time': datetime.now().strftime('%H:%M')
    })
    st.balloons()
    st.success("✅ BANKNIFTY PRO ALERT!" if success else "📱 Add Secrets")
if st.button("🚀 SENSEX TRACK", key="sensex_btn"):
    strike_num = s_best['Strike']
    entry_price = float(s_best['LTP'].replace('₹', ''))
    target = f"{entry_price + 100:.0f}"
    sl = f"{entry_price - 50:.0f}"
    
    success = run_pro_alert('SENSEX 50', strike_num, f"{entry_price:.0f}", target, sl)
    
    st.session_state.tracked.append({
        'Index': 'SENSEX', 'Strike': s_best['Strike'], 
        'Entry': s_best['LTP'], 'Score': s_best['Score'],
        'Time': datetime.now().strftime('%H:%M')
    })
    st.balloons()
    st.success("✅ SENSEX PRO ALERT!" if success else "📱 Add Secrets")
