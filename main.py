from flask import Flask
import threading
import os

app = Flask('')

@app.route('/')
def home():
    return "Bot is Alive!"

def keep_alive():
    port = int(os.environ.get('PORT', 8080))
    t = threading.Thread(target=lambda: app.run(host='0.0.0.0', port=port))
    t.start()

# ==============================================================================
# 📌 PROJECT: INSTAGRAM SMM BOT (OWNER BOT ARCHITECTURE)
# ⚙️ HOSTING MODE: 24/7 FREE HOSTING COMPATIBLE (KOYEB / RENDER / RAILWAY)
# 📝 DESCRIPTION: 
#    This bot handles automated SMM orders (Bot Followers, Real Followers, Likes)
#    using Inline Buttons. It includes an Admin Approval System, automated 
#    Receipt Box creation, and background Delay-Timers that automatically 
#    delete payment chat history and send a Completion Message after delivery.
# ==============================================================================

import asyncio
from datetime import datetime
from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup

# ⚠️ --- ENTER YOUR CONFIGURATION HERE ---
API_TOKEN = '8642149587:AAEQCxPaeUE_-rgXQ9ZeHxaWhAZqXVwWveQ'
  # Replace with your Bot token from BotFather
ADMIN_ID = 7616127905
              # Replace with your Telegram User ID
QR_CODE_URL = 'https://ibb.co/kg2jT6ZF'


  # Replace with your QR code image link
# --------------------------------------------------

bot = Bot(token=API_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)

class OrderStates(StatesGroup):
    waiting_for_payment = State()

# Service Configuration and Delivery Duration (in seconds)
SERVICES = {
    "bot": {"name": "🤖 Bot Followers", "time": "2 Hours and 45 Minutes", "delay": 9900},
    "real": {"name": "🔥 Real Followers", "time": "7 Hours and 8 Minutes", "delay": 25680},
    "likes": {"name": "❤️ Likes", "time": "3 Hours and 18 Minutes", "delay": 11880}
}

def get_main_menu():
    keyboard = InlineKeyboardMarkup(row_width=1)
    keyboard.add(
        InlineKeyboardButton("🤖 Bot Followers", callback_data="menu_bot"),
        InlineKeyboardButton("🔥 Real Followers", callback_data="menu_real"),
        InlineKeyboardButton("❤️ Likes", callback_data="menu_likes")
    )
    return keyboard

@dp.message_handler(commands=['start'])
async def send_welcome(message: types.Message):
    welcome_text = (
        "🚀 Welcome to Owner Bot 🌟\n\n"
        "🥃 Hey! Thanks for reaching out.\n\n"
        "❗️ I’m currently busy or offline at the moment.\n"
        "✉️ Please leave your message, and I’ll respond as soon as I’m available.\n\n"
        "⏳ Your patience is greatly appreciated.\n"
        "━━━━━━━━━━━━━━━\n\n"
        "📣 𝗨𝗣𝗗𝗔𝗧Ｅ𝖘 & 𝗣𝗥ＩＣＥ 𝗟ＩＳ𝐓\n\n"
        "➡️ @Bot_Owner_Official\n\n"
        "━━━━━━━━━━━━━━━\n\n"
        "✅ Latest Updates\n"
        "✅ Service Information\n"
        "✅ Price List\n"
        "✅ New Announcements\n\n"
        "⚪️ Thanks for contacting Owner Bot\n"
        "🦁 Have a great day!"
    )
    await message.answer(welcome_text, reply_markup=get_main_menu())

@dp.callback_query_handler(lambda c: c.data.startswith('menu_'))
async def show_sub_menu(callback_query: types.CallbackQuery):
    service_type = callback_query.data.split('_')[1]
    keyboard = InlineKeyboardMarkup(row_width=2)
    
    if service_type == "bot":
        text = "🔹 [ 🤖 Bot Followers ] (Low Speed ⏰ | No refill 🚫 | Delivery Time: 2 Hours and 45 Minutes):"
        prices = [("1k Bot — ₹49", "49"), ("2k Bot — ₹79", "79"), ("3k Bot — ₹100", "100"), 
                  ("4k Bot — ₹120", "120"), ("5k Bot — ₹140", "140"), ("6k Bot — ₹160", "160"),
                  ("7k Bot — ₹180", "180"), ("8k Bot — ₹200", "200"), ("9k Bot — ₹220", "220"), ("10k Bot — ₹250", "250")]
    elif service_type == "real":
        text = "🔹 [ 🔥 Real Followers ] (Fast Delivery ⏰ | Refill 💵 | Delivery Time: 7 Hours and 8 Minutes):"
        prices = [("1k Real — ₹100", "100"), ("2k Real — ₹145", "145"), ("3k Real — ₹195", "195"), 
                  ("4k Real — ₹245", "245"), ("5k Real — ₹290", "290")]
    else:
        text = "🔹 [ ❤️ Likes ] (Lifetime 💯 | Fast delivery 📮 | Delivery Time: 3 Hours and 18 Minutes):"
        prices = [("1000 likes — ₹8", "8"), ("2000 likes — ₹13", "13"), ("3000 likes — ₹18", "18"),
                  ("4000 likes — ₹23", "23"), ("5000 likes — ₹28", "28"), ("6000 likes — ₹33", "33"),
                  ("7000 likes — ₹38", "38"), ("8000 likes — ₹43", "43"), ("9000 likes — ₹48", "48"), ("10000 likes — ₹60", "60")]

    for label, val in prices:
        keyboard.insert(InlineKeyboardButton(label, callback_data=f"buy_{service_type}_{label}"))
    keyboard.add(InlineKeyboardButton("➕ More...", callback_data="more"), InlineKeyboardButton("🔙 Back to Main Menu", callback_data="back_main"))
    
    await bot.edit_message_text(text, callback_query.from_user.id, callback_query.message.message_id, reply_markup=keyboard)

@dp.callback_query_handler(lambda c: c.data == 'back_main')
async def back_to_main(callback_query: types.CallbackQuery):
    await bot.edit_message_text(callback_query.message.text, callback_query.from_user.id, callback_query.message.message_id, reply_markup=get_main_menu())

@dp.callback_query_handler(lambda c: c.data.startswith('buy_'))
async def process_purchase(callback_query: types.CallbackQuery, state: FSMContext):
    _, s_type, p_name = callback_query.data.split('_')
    await state.update_data(s_type=s_type, p_name=p_name)
    
    qr_msg = await bot.send_photo(callback_query.from_user.id, QR_CODE_URL, 
                         caption="Please send your Instagram URL (Profile Link) along with the payment screenshot here.")
    
    await state.update_data(qr_msg_id=qr_msg.message_id)
    await OrderStates.waiting_for_payment.set()

@dp.message_handler(state=OrderStates.waiting_for_payment, content_types=['photo', 'text'])
async def handle_payment_submission(message: types.Message, state: FSMContext):
    data = await state.get_data()
    
    if message.photo and message.caption:
        admin_kb = InlineKeyboardMarkup().add(InlineKeyboardButton("✅ Approve", callback_data=f"ap_{message.from_user.id}_{data['s_type']}_{data['p_name']}_{message.message_id}_{data['qr_msg_id']}"))
        await bot.send_photo(ADMIN_ID, message.photo[-1].file_id, caption=f"New Order Request!\nUser: @{message.from_user.username}\nDetails: {data['p_name']}\nLink: {message.caption}", reply_markup=admin_kb)
        await message.answer("Processing your request... Please wait for Admin approval.")
        await state.finish()
    else:
        await message.answer("Please send the photo WITH the Instagram URL as caption.")

@dp.callback_query_handler(lambda c: c.data.startswith('ap_'))
async def approve_order(callback_query: types.CallbackQuery):
    _, u_id, s_type, p_name, u_msg_id, qr_id = callback_query.data.split('_')
    u_id, u_msg_id, qr_id = int(u_id), int(u_msg_id), int(qr_id)
    
    user = await bot.get_chat(u_id)
    start_time = datetime.now().strftime("%Y-%m-%d %H:%M")
    srv = SERVICES[s_type]
    
    receipt = (
        "━━━━━━━━━━━━━━━━━━━━\n"
        "⚡️ ORDER ACTIVATED SUCCESSFULLY ⚡️\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        f"👤 Customer: @{user.username}\n"
        f"🛒 Service: {srv['name']}\n"
        f"📈 Quantity/Package: {p_name}\n\n"
        f"🕒 Start Time: {start_time}\n"
        f"⏳ Estimated Delivery: {srv['time']}\n"
        "🟢 Status: Processing...\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "🤖 Thank you for purchasing! Your order is being delivered safely."
    )
    
    rec_msg = await bot.send_message(u_id, receipt)
    await callback_query.answer("Order Approved!")
    await bot.edit_message_caption(ADMIN_ID, callback_query.message.message_id, caption="Approved ✅")

    asyncio.create_task(schedule_completion(u_id, srv, p_name, [qr_id, u_msg_id, rec_msg.message_id]))

async def schedule_completion(user_id, srv, p_name, messages_to_delete):
    await asyncio.sleep(srv['delay'])
    
    for msg_id in messages_to_delete:
        try: await bot.delete_message(user_id, msg_id)
        except: pass
        
    completion_text = (
        "━━━━━━━━━━━━━━━━━━━━\n"
        "🎉 YOUR ORDER IS COMPLETED 🎉\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        "✨ Dear Customer, your service has been fully delivered!\n\n"
        "📊 Summary of Service:\n"
        "🔹 Platform: Instagram\n"
        f"🔹 Service Type: {p_name}\n"
        "🔹 Status: 100% Completed ✅\n\n"
        "🤝 Thank you for choosing our SMM service. Hope to see you again soon!\n"
        "━━━━━━━━━━━━━━━"
    )
    await bot.send_message(user_id, completion_text, reply_markup=get_main_menu())

if __name__ == '__main__':
    from aiogram import executor
    keep_alive()
    executor.start_polling(dp, skip_updates=True)

