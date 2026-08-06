import os
import asyncio
import threading
import re
import logging
import json
from flask import Flask
from datetime import datetime, timezone, timedelta
from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram import executor

logging.basicConfig(level=logging.ERROR)

# --- Database for Persistent Users and Dynamic Configs ---
USERS_FILE = "users.json"
CONFIG_FILE = "config.json"

def load_users():
    if os.path.exists(USERS_FILE):
        try:
            with open(USERS_FILE, "r") as f:
                return set(json.load(f))
        except Exception:
            return set()
    return set()

def save_user(user_id):
    users = load_users()
    if user_id not in users:
        users.add(user_id)
        with open(USERS_FILE, "w") as f:
            json.dump(list(users), f)

# Default Services Data
DEFAULT_SERVICES = {
    "bot": {
        "title": "🔹 [ 🤖 Bot Followers ]\n*(Low Speed ⏰ | No refill 🚫 | Delivery Time: {time})*",
        "delivery_time": "2 Hours and 45 Minutes",
        "plans": [
            {"qty": "1000", "price": 49, "text": "🤖 1k Bot — ₹{price}"},
            {"qty": "2000", "price": 79, "text": "🤖 2k Bot — ₹{price}"},
            {"qty": "3000", "price": 100, "text": "🤖 3k Bot — ₹{price}"},
            {"qty": "4000", "price": 120, "text": "🤖 4k Bot — ₹{price}"},
            {"qty": "5000", "price": 140, "text": "🤖 5k Bot — ₹{price}"},
            {"qty": "6000", "price": 160, "text": "🤖 6k Bot — ₹{price}"},
            {"qty": "7000", "price": 180, "text": "🤖 7k Bot — ₹{price}"},
            {"qty": "8000", "price": 200, "text": "🤖 8k Bot — ₹{price}"},
            {"qty": "9000", "price": 220, "text": "🤖 9k Bot — ₹{price}"},
            {"qty": "10000", "price": 250, "text": "🤖 10k Bot — ₹{price}"}
        ]
    },
    "real": {
        "title": "🔹 [ 🔥 Real Followers ]\n*(Fast Delivery ⏰ | Refill 💵 | Delivery Time: {time})*",
        "delivery_time": "7 Hours and 8 Minutes",
        "plans": [
            {"qty": "1000", "price": 100, "text": "🔥 1k Real — ₹{price}"},
            {"qty": "2000", "price": 145, "text": "🔥 2k Real — ₹{price}"},
            {"qty": "3000", "price": 195, "text": "🔥 3k Real — ₹{price}"},
            {"qty": "4000", "price": 245, "text": "🔥 4k Real — ₹{price}"},
            {"qty": "5000", "price": 290, "text": "🔥 5k Real — ₹{price}"}
        ]
    },
    "likes": {
        "title": "🔹 [ ❤️ Likes ]\n*(Lifetime 💯 | Fast delivery 📮 | Delivery Time: {time})*",
        "delivery_time": "3 Hours and 18 Minutes",
        "plans": [
            {"qty": "1000", "price": 8, "text": "❤️ 1000 Likes — ₹{price}"},
            {"qty": "2000", "price": 13, "text": "❤️ 2000 Likes — ₹{price}"},
            {"qty": "3000", "price": 18, "text": "❤️ 3000 Likes — ₹{price}"},
            {"qty": "4000", "price": 23, "text": "❤️ 4000 Likes — ₹{price}"},
            {"qty": "5000", "price": 28, "text": "❤️ 5000 Likes — ₹{price}"},
            {"qty": "6000", "price": 33, "text": "❤️ 6000 Likes — ₹{price}"},
            {"qty": "7000", "price": 38, "text": "❤️ 7000 Likes — ₹{price}"},
            {"qty": "8000", "price": 43, "text": "❤️ 8000 Likes — ₹{price}"},
            {"qty": "9000", "price": 48, "text": "❤️ 9000 Likes — ₹{price}"},
            {"qty": "10000", "price": 60, "text": "❤️ 10000 Likes — ₹{price}"}
        ]
    }
}

def load_services():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as f:
                return json.load(f)
        except Exception:
            return DEFAULT_SERVICES
    return DEFAULT_SERVICES

def save_services(data):
    with open(CONFIG_FILE, "w") as f:
        json.dump(data, f, indent=4)

SERVICES_DATA = load_services()

# --- Flask Server for 24/7 Uptime ---
app = Flask('')
@app.route('/')
def home(): 
    return "Bot is Alive!"

def keep_alive():
    def run_flask():
        try:
            port = int(os.environ.get('PORT', 10000))
            app.run(host='0.0.0.0', port=port, use_reloader=False, debug=False, threaded=True)
        except Exception as e:
            print(f"Flask internal error: {e}")
            
    t = threading.Thread(target=run_flask, daemon=True)
    t.start()

# --- Configurations ---
bot = Bot(token="8642149587:AAGCDZqRoYxFAGGMKjLAAQZQG0S_BGdfQGw")
ADMIN_ID = 7616127905
QR_URL = 'https://ibb.co/kg2jT6ZF'
PAYMENT_PROOF_CHANNEL = 'https://t.me/+hLxD0623ZEs1M2I1'

IST = timezone(timedelta(hours=5, minutes=30))

storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)

class OrderStates(StatesGroup):
    wait_screenshot = State()
    wait_url = State()
    wait_admin_time = State()
    in_support = State()

# --- Keyboards ---
def get_main_menu():
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(InlineKeyboardButton("🛒 Shop Now", callback_data="buy_now"))
    kb.add(
        InlineKeyboardButton("🔑 My Orders", callback_data="my_orders"),
        InlineKeyboardButton("👤 Your Profile", callback_data="your_profile")
    )
    kb.add(
        InlineKeyboardButton("📢 Pay Proof ↗️", url=PAYMENT_PROOF_CHANNEL),
        InlineKeyboardButton("💬 Support", callback_data="chat_admin")
    )
    kb.add(InlineKeyboardButton("🎬 How to Use Bot", callback_data="how_to_use"))
    return kb

def get_services_menu():
    kb = InlineKeyboardMarkup(row_width=1)
    kb.add(
        InlineKeyboardButton("🤖 Bot Followers", callback_data="svc_bot"),
        InlineKeyboardButton("🔥 Real Followers", callback_data="svc_real"),
        InlineKeyboardButton("❤️ Likes", callback_data="svc_likes"),
        InlineKeyboardButton("🔙 Back to Main Menu", callback_data="back_to_main")
    )
    return kb

def get_welcome_text(first_name):
    return (
        "═══════════════════════\n"
        "🚀 **WELCOME TO ELITE HACKERS** 🌟\n"
        "═══════════════════════\n\n"
        f"👋 Welcome to our official store bot, **{first_name}**!\n\n"
        "👇 Select an option from below:"
    )

# --- Start Command ---
@dp.message_handler(commands=['start'], state='*')
async def start(msg: types.Message, state: FSMContext):
    try:
        user_id = msg.from_user.id
        save_user(user_id)
        
        if user_id == ADMIN_ID:
            await msg.answer("👨‍💻 **Admin Commands:**\n\n• `/broadcast <message>` - Send updates to all users\n• `/setprice <category> <index> <new_price>` - Change price\n• `/settime <category> <new_time>` - Change delivery time", parse_mode="Markdown")
            return

        await state.finish()
        first_name = msg.from_user.first_name or "User"
        username = f"@{msg.from_user.username}" if msg.from_user.username else "No Username"
        profile_link = f"tg://user?id={user_id}"

        admin_notify = (
            "━━━━━━━━━━━━━━━━━━\n"
            "🔔 **NEW USER STARTED BOT**\n"
            "━━━━━━━━━━━━━━━━━━\n"
            f"👤 **Name:** [{first_name}]({profile_link})\n"
            f"🏷 **Username:** {username}\n"
            f"🆔 **User ID:** `{user_id}`\n"
            "━━━━━━━━━━━━━━━━━━"
        )
        try:
            await bot.send_message(ADMIN_ID, admin_notify, parse_mode="Markdown", disable_web_page_preview=True)
        except Exception:
            pass

        await msg.answer(get_welcome_text(first_name), reply_markup=get_main_menu(), parse_mode="Markdown")
    except Exception as e:
        print(f"Error in start command: {e}")

# --- Navigation Handlers ---
@dp.callback_query_handler(lambda c: c.data == 'back_to_main', state='*')
async def back_to_main_handler(cq: types.CallbackQuery, state: FSMContext):
    try:
        await state.finish()
        await cq.answer()
        first_name = cq.from_user.first_name or "User"
        try:
            await cq.message.edit_text(get_welcome_text(first_name), reply_markup=get_main_menu(), parse_mode="Markdown")
        except Exception:
            await cq.message.delete()
            await bot.send_message(cq.from_user.id, get_welcome_text(first_name), reply_markup=get_main_menu(), parse_mode="Markdown")
    except Exception as e:
        print(f"Error in back_to_main: {e}")

@dp.callback_query_handler(lambda c: c.data == 'my_orders', state='*')
async def my_orders_handler(cq: types.CallbackQuery):
    await cq.answer()
    kb = InlineKeyboardMarkup().add(InlineKeyboardButton("🔙 Back to Main Menu", callback_data="back_to_main"))
    text = "🔑 **My Orders**\n\n📌 You currently have no active or previous orders."
    await cq.message.edit_text(text, reply_markup=kb, parse_mode="Markdown")

@dp.callback_query_handler(lambda c: c.data == 'your_profile', state='*')
async def your_profile_handler(cq: types.CallbackQuery):
    await cq.answer()
    u = cq.from_user
    kb = InlineKeyboardMarkup().add(InlineKeyboardButton("🔙 Back to Main Menu", callback_data="back_to_main"))
    text = (
        "👤 **YOUR PROFILE**\n\n"
        f"📛 **Name:** {u.first_name}\n"
        f"🏷 **Username:** @{u.username if u.username else 'N/A'}\n"
        f"🆔 **User ID:** `{u.id}`"
    )
    await cq.message.edit_text(text, reply_markup=kb, parse_mode="Markdown")

@dp.callback_query_handler(lambda c: c.data == 'how_to_use', state='*')
async def how_to_use_handler(cq: types.CallbackQuery):
    await cq.answer()
    kb = InlineKeyboardMarkup().add(InlineKeyboardButton("🔙 Back to Main Menu", callback_data="back_to_main"))
    text = (
        "🎬 **HOW TO USE THE BOT**\n\n"
        "1️⃣ Tap on **🛒 Shop Now**.\n"
        "2️⃣ Select your desired service (Followers / Likes).\n"
        "3️⃣ Select a package/plan.\n"
        "4️⃣ Scan the QR code and make payment.\n"
        "5️⃣ Send the payment screenshot to the bot.\n"
        "6️⃣ Send your Instagram account link.\n\n"
        "⚡ Admin will verify and process your order instantly!"
    )
    await cq.message.edit_text(text, reply_markup=kb, parse_mode="Markdown")

@dp.callback_query_handler(lambda c: c.data == 'back_to_shop', state='*')
async def back_to_shop_handler(cq: types.CallbackQuery, state: FSMContext):
    try:
        await state.finish()
        await cq.answer()
        try:
            await cq.message.edit_text("🛍 **Select Your Instagram Service**\n\n*Choose an option below:*", reply_markup=get_services_menu(), parse_mode="Markdown")
        except Exception:
            await cq.message.delete()
            await bot.send_message(cq.from_user.id, "🛍 **Select Your Instagram Service**\n\n*Choose an option below:*", reply_markup=get_services_menu(), parse_mode="Markdown")
    except Exception as e:
        print(f"Error in back_to_shop: {e}")

@dp.callback_query_handler(lambda c: c.data == 'buy_now', state='*')
async def buy_now_handler(cq: types.CallbackQuery):
    try:
        await cq.answer()
        try:
            await cq.message.edit_text("🛍 **Select Your Instagram Service**\n\n*Choose an option below:*", reply_markup=get_services_menu(), parse_mode="Markdown")
        except Exception:
            await bot.send_message(cq.from_user.id, "🛍 **Select Your Instagram Service**\n\n*Choose an option below:*", reply_markup=get_services_menu(), parse_mode="Markdown")
    except Exception as e:
        print(f"Error in buy_now: {e}")

@dp.callback_query_handler(lambda c: c.data and c.data.startswith('svc_'), state='*')
async def show_service_plans(cq: types.CallbackQuery):
    try:
        await cq.answer()
        s_type = cq.data.split('_')[1]
        if s_type not in SERVICES_DATA:
            return
            
        s_info = SERVICES_DATA[s_type]
        kb = InlineKeyboardMarkup(row_width=1)
        
        for idx, plan in enumerate(s_info['plans']):
            btn_text = plan['text'].format(price=plan['price'])
            kb.add(InlineKeyboardButton(btn_text, callback_data=f"plan_{s_type}_{idx}"))
            
        kb.add(InlineKeyboardButton("🔙 Back to Shop", callback_data="back_to_shop"))
        
        title_text = s_info['title'].format(time=s_info.get('delivery_time', 'Standard'))
        caption_text = f"{title_text}\n\n**Choose a plan 📥**"
        
        try:
            await cq.message.edit_text(caption_text, reply_markup=kb, parse_mode="Markdown")
        except Exception:
            await bot.send_message(cq.from_user.id, caption_text, reply_markup=kb, parse_mode="Markdown")
    except Exception as e:
        print(f"Error in show_service_plans: {e}")

# --- Plan Selection & Timer ---
@dp.callback_query_handler(lambda c: c.data and c.data.startswith('plan_'), state='*')
async def select_plan_handler(cq: types.CallbackQuery, state: FSMContext):
    try:
        await cq.answer()
        parts = cq.data.split('_')
        s_type = parts[1]
        idx = int(parts[2])
        
        plan_info = SERVICES_DATA[s_type]['plans'][idx]
        qty = plan_info['qty']
        price = plan_info['price']
        
        await OrderStates.wait_screenshot.set()
        await state.update_data(service=s_type, quantity=qty, price=price)
        
        qr_kb = InlineKeyboardMarkup(row_width=1)
        qr_kb.add(InlineKeyboardButton("🔙 Back to Shop", callback_data="back_to_shop"))

        initial_caption = (
            f"📦 **Quantity:** {qty}\n"
            f"💰 **Amount to Pay:** ₹{price}\n\n"
            f"📲 Please scan the QR code above for payment.\n\n"
            f"📍 **Step 1:** Send your **Payment Screenshot** first.\n"
            f"📍 **Step 2:** Send your **Instagram URL** after.\n\n"
            "⏳ Time Remaining: 05:00"
        )
        
        try:
            qr_msg = await bot.send_photo(cq.from_user.id, QR_URL, caption=initial_caption, reply_markup=qr_kb, parse_mode="Markdown")
        except Exception:
            qr_msg = await bot.send_message(cq.from_user.id, initial_caption, reply_markup=qr_kb, parse_mode="Markdown")

        async def live_countdown_timer(chat_id, message_id):
            for remaining in range(299, -1, -1):
                await asyncio.sleep(1)
                try:
                    current_state = await dp.current_state(user=chat_id).get_state()
                    if current_state != 'OrderStates:wait_screenshot':
                        return
                    
                    if remaining % 5 == 0 or remaining < 10:
                        mins, secs = divmod(remaining, 60)
                        time_str = f"{mins:02d}:{secs:02d}"
                        data_dict = await dp.current_state(user=chat_id).get_data()
                        q_val = data_dict.get('quantity', qty)
                        p_val = data_dict.get('price', price)
                        updated_caption = (
                            f"📦 **Quantity:** {q_val}\n"
                            f"💰 **Amount to Pay:** ₹{p_val}\n\n"
                            f"📲 Please scan the QR code above for payment.\n\n"
                            f"📍 **Step 1:** Send your **Payment Screenshot** first.\n"
                            f"📍 **Step 2:** Send your **Instagram URL** after.\n\n"
                            f"⏳ Time Remaining: {time_str}"
                        )
                        try:
                            await bot.edit_message_caption(chat_id=chat_id, message_id=message_id, caption=updated_caption, reply_markup=qr_kb, parse_mode="Markdown")
                        except Exception:
                            pass
                except Exception:
                    pass
            
            try:
                current_state = await dp.storage.get_state(chat=chat_id, user=chat_id)
                if current_state == 'OrderStates:wait_screenshot':
                    await dp.storage.finish(chat=chat_id, user=chat_id)
                    try:
                        await bot.delete_message(chat_id=chat_id, message_id=message_id)
                    except Exception:
                        pass
                    await bot.send_message(
                        chat_id,
                        "⚠️ **Time expired!** The QR code session has ended. Please start again from the menu.",
                        reply_markup=get_main_menu(),
                        parse_mode="Markdown"
                    )
            except Exception:
                pass

        asyncio.create_task(live_countdown_timer(cq.from_user.id, qr_msg.message_id))
    except Exception as e:
        print(f"Error in select_plan_handler: {e}")

# --- Step 1: Payment Screenshot Verification ---
@dp.message_handler(state=OrderStates.wait_screenshot, content_types=types.ContentTypes.ANY)
async def process_screenshot(msg: types.Message, state: FSMContext):
    try:
        if msg.photo:
            photo_id = msg.photo[-1].file_id
            await state.update_data(photo_id=photo_id)
            await OrderStates.wait_url.set()
            await msg.answer("✅ **Payment Screenshot Verified!**\n\n🔗 Now, please send your **Instagram Profile/Post URL**:", parse_mode="Markdown")
        else:
            await msg.answer("❌ **Invalid Format!**\n\n⚠️ Please send a valid **Payment Screenshot (Image/Photo)**. Text, documents, or other media are not accepted.", parse_mode="Markdown")
    except Exception as e:
        print(f"Error in process_screenshot: {e}")

# --- Step 2: Instagram URL Verification & Admin Alert ---
@dp.message_handler(state=OrderStates.wait_url, content_types=types.ContentTypes.ANY)
async def process_url(msg: types.Message, state: FSMContext):
    try:
        if not msg.text:
            await msg.answer("❌ **Invalid Input!**\n\n⚠️ Please send a valid text link (e.g., https://instagram.com/...).", parse_mode="Markdown")
            return

        text_content = msg.text.strip()
        if "instagram.com" in text_content.lower() or "instagr.am" in text_content.lower():
            data = await state.get_data()
            uid = msg.from_user.id
            s_type = data.get('service', 'bot')
            qty = data.get('quantity', 'N/A')
            photo_id = data.get('photo_id')
            
            username = f"@{msg.from_user.username}" if msg.from_user.username else "No Username"
            first_name = msg.from_user.first_name or "User"
            profile_link = f"tg://user?id={uid}"
            service_name = SERVICES_DATA.get(s_type, {}).get('title', 'Service').split('\n')[0]

            admin_box = (
                "━━━━━━━━━━━━━━━━━━\n"
                "📥 **NEW ORDER RECEIVED**\n"
                "━━━━━━━━━━━━━━━━━━\n"
                f"👤 **Name:** [{first_name}]({profile_link})\n"
                f"🏷 **Username:** {username}\n"
                f"🆔 **User ID:** `{uid}`\n"
                f"🛒 **Service:** {service_name}\n"
                f"📊 **Quantity:** {qty}\n"
                f"🔗 **URL:** {text_content}\n"
                "━━━━━━━━━━━━━━━━━━"
            )

            try:
                sent_box = await bot.send_message(ADMIN_ID, admin_box, parse_mode="Markdown", disable_web_page_preview=True)
                await bot.send_photo(ADMIN_ID, photo_id, caption=f"📸 Payment Screenshot from ID: `{uid}`", parse_mode="Markdown")
            except Exception:
                sent_box = await bot.send_message(ADMIN_ID, admin_box)
                await bot.send_photo(ADMIN_ID, photo_id)

            ap_markup = InlineKeyboardMarkup(row_width=1)
            ap_markup.add(
                InlineKeyboardButton("✅ Approve", callback_data=f"ap_{uid}_{sent_box.message_id}"),
                InlineKeyboardButton("❌ Reject", callback_data=f"rj_{uid}_{sent_box.message_id}")
            )
            await bot.send_message(ADMIN_ID, "👇 To approve, click 'Approve' and reply with delivery time:", reply_markup=ap_markup)

            await msg.answer("✅ **Payment Screenshot & Instagram URL Verified!**\n\nAdmin will process your order shortly.", parse_mode="Markdown")
            await state.finish()
        else:
            await msg.answer("❌ **Invalid Instagram Link!**\n\n⚠️ Please send a correct Instagram Profile or Post URL (e.g., https://instagram.com/username).", parse_mode="Markdown")
    except Exception as e:
        print(f"Error in process_url: {e}")

# --- Support Mode Handlers ---
@dp.callback_query_handler(lambda c: c.data == 'chat_admin', state='*')
async def start_support(cq: types.CallbackQuery, state: FSMContext):
    try:
        await cq.answer()
        await OrderStates.in_support.set()
        cancel_kb = InlineKeyboardMarkup(row_width=1).add(InlineKeyboardButton("❌ Cancel Support", callback_data="cancel_support"))
        await bot.send_message(
            cq.from_user.id,
            "💬 **Support Mode Activated**\n\nSend your message here. It will be forwarded to the admin.\n\nClick below to exit support mode.",
            reply_markup=cancel_kb,
            parse_mode="Markdown"
        )
    except Exception as e:
        print(f"Error in start_support: {e}")

@dp.callback_query_handler(lambda c: c.data == 'cancel_support', state=OrderStates.in_support)
async def cancel_support(cq: types.CallbackQuery, state: FSMContext):
    try:
        await cq.answer("Support closed.")
        await state.finish()
        await bot.send_message(cq.from_user.id, "You are back to the main menu:", reply_markup=get_main_menu())
    except Exception as e:
        print(f"Error in cancel_support: {e}")

# --- ADMIN FEATURE 1: Broadcast Command ---
@dp.message_handler(commands=['broadcast'], state='*')
async def broadcast_cmd(msg: types.Message):
    if msg.from_user.id != ADMIN_ID:
        return

    reply = msg.reply_to_message
    users = load_users()
    count = 0

    if reply:
        for u_id in users:
            try:
                await reply.copy_to(u_id)
                count += 1
                await asyncio.sleep(0.05)
            except Exception:
                pass
    else:
        text = msg.get_args()
        if not text:
            await msg.reply("⚠️ **Usage:**\nReply to a message/photo with `/broadcast`\nOR type `/broadcast Your Message Here`", parse_mode="Markdown")
            return

        for u_id in users:
            try:
                await bot.send_message(u_id, text, parse_mode="Markdown")
                count += 1
                await asyncio.sleep(0.05)
            except Exception:
                pass

    await msg.reply(f"📢 **Broadcast completed successfully!**\nSent to {count} user(s).", parse_mode="Markdown")

# --- ADMIN FEATURE 2: Set Price Command ---
@dp.message_handler(commands=['setprice'], state='*')
async def set_price_cmd(msg: types.Message):
    if msg.from_user.id != ADMIN_ID:
        return

    args = msg.get_args().split()
    if len(args) < 3:
        await msg.reply("⚠️ **Usage:** `/setprice <category> <index> <new_price>`\nExample: `/setprice bot 0 55`", parse_mode="Markdown")
        return

    cat, idx, new_price = args[0].lower(), int(args[1]), int(args[2])

    if cat in SERVICES_DATA and idx < len(SERVICES_DATA[cat]['plans']):
        SERVICES_DATA[cat]['plans'][idx]['price'] = new_price
        save_services(SERVICES_DATA)
        await msg.reply(f"✅ **Price updated successfully!**\n{cat.capitalize()} plan #{idx} price changed to ₹{new_price}", parse_mode="Markdown")
    else:
        await msg.reply("❌ Invalid category or plan index.", parse_mode="Markdown")

# --- ADMIN FEATURE 3: Set Delivery Time Command ---
@dp.message_handler(commands=['settime'], state='*')
async def set_time_cmd(msg: types.Message):
    if msg.from_user.id != ADMIN_ID:
        return

    args = msg.get_args().split(maxsplit=1)
    if len(args) < 2:
        await msg.reply("⚠️ **Usage:** `/settime <category> <new_time>`\nExample: `/settime bot 1 Hour and 30 Minutes`", parse_mode="Markdown")
        return

    cat, new_time = args[0].lower(), args[1]

    if cat in SERVICES_DATA:
        SERVICES_DATA[cat]['delivery_time'] = new_time
        save_services(SERVICES_DATA)
        await msg.reply(f"✅ **Delivery time updated!**\n{cat.capitalize()} delivery time set to: {new_time}", parse_mode="Markdown")
    else:
        await msg.reply("❌ Invalid category. Choose from: bot, real, likes", parse_mode="Markdown")

# --- Admin Actions: Approve / Reject ---
@dp.callback_query_handler(lambda c: c.data and (c.data.startswith('ap_') or c.data.startswith('rj_')), state='*')
async def admin_actions(cq: types.CallbackQuery, state: FSMContext):
    try:
        if cq.from_user.id != ADMIN_ID: 
            return
        parts = cq.data.split('_')
        if len(parts) < 3:
            return
        action = parts[0]
        u_id = int(parts[1])
        box_msg_id = int(parts[2])
        
        if action == 'rj':
            try:
                await bot.send_message(u_id, "❌ Your payment/details were rejected. Please check and try again.")
            except Exception:
                pass
            await cq.answer("Order Rejected")
            try:
                await bot.edit_message_text("❌ Order Rejected.", ADMIN_ID, cq.message.message_id)
            except Exception:
                pass
            return
            
        await cq.answer()
        await bot.send_message(ADMIN_ID, f"✍️ Reply to this message with the estimated delivery time for User ID `{u_id}` (Example: `10m`, `1h`, `2 Hours`):", parse_mode="Markdown")
        
        admin_state = Dispatcher.get_current().current_state(user=ADMIN_ID, chat=ADMIN_ID)
        await admin_state.set_state(OrderStates.wait_admin_time)
        await admin_state.update_data(target_uid=u_id, orig_msg_id=cq.message.message_id, box_msg_id=box_msg_id)
    except Exception as e:
        print(f"Error in admin_actions: {e}")

@dp.message_handler(state=OrderStates.wait_admin_time)
async def get_admin_time(msg: types.Message, state: FSMContext):
    try:
        if msg.from_user.id != ADMIN_ID: 
            return
        data = await state.get_data()
        u_id = data.get('target_uid')
        orig_msg_id = data.get('orig_msg_id')
        box_msg_id = data.get('box_msg_id')
        custom_time = msg.text
        
        try:
            await state.finish()
        except Exception:
            pass
        
        start_time = datetime.now(IST).strftime("%Y-%m-%d %H:%M")
        
        receipt = (
            "━━━━━━━━━━━━━━━━━━\n"
            "⚡ **ORDER ACTIVATED SUCCESSFULLY** ⚡\n"
            "━━━━━━━━━━━━━━━━━━\n\n"
            f"⏱ **Start Time:** {start_time}\n"
            f"⏳ **Estimated Delivery Time:** {custom_time}\n"
            f"🟢 **Status:** Processing in progress...\n\n"
            "━━━━━━━━━━━━━━━━━━\n"
            "🤖 *Your order is being processed safely.*"
        )
        
        user_messages_to_delete = []
        try:
            rec_msg = await bot.send_message(u_id, receipt, parse_mode="Markdown")
            user_messages_to_delete.append(rec_msg.message_id)
        except Exception:
            return
            
        await msg.reply(f"✅ Delivery time set as: **{custom_time}**", parse_mode="Markdown")
        
        try:
            await bot.edit_message_text(f"✅ **Order Approved** | Delivery Time: {custom_time}", ADMIN_ID, orig_msg_id, parse_mode="Markdown")
        except Exception:
            pass

        async def finish_and_delete():
            delay_seconds = 60
            try:
                t_str = custom_time.strip().lower()
                total_seconds = 0
                if 'd' in t_str or 'day' in t_str:
                    match_d = re.search(r'(\d+)\s*(?:d|day)', t_str)
                    if match_d:
                        total_seconds += int(match_d.group(1)) * 86400
                if 'h' in t_str or 'hour' in t_str:
                    match_h = re.search(r'(\d+)\s*(?:h|hour)', t_str)
                    if match_h:
                        total_seconds += int(match_h.group(1)) * 3600
                if 'm' in t_str or 'min' in t_str:
                    match_m = re.search(r'(\d+)\s*(?:m|min)', t_str)
                    if match_m:
                        total_seconds += int(match_m.group(1)) * 60
                if total_seconds == 0 and t_str.isdigit():
                    total_seconds = int(t_str) * 60
                elif total_seconds > 0:
                    delay_seconds = total_seconds
                else:
                    delay_seconds = 60
            except Exception:
                delay_seconds = 60

            await asyncio.sleep(delay_seconds)

            completed_time_ist = datetime.now(IST).strftime('%Y-%m-%d %H:%M')
            comp_text = (
                "━━━━━━━━━━━━━━━━━━\n"
                "✅ **ORDER DELIVERED / COMPLETED** ✅\n"
                "━━━━━━━━━━━━━━━━━━\n\n"
                f"⏱ **Completed At:** {completed_time_ist}\n"
                "🎉 Your order has been successfully delivered!\n\n"
                "Thank you for choosing us! 🌟"
            )

            admin_completion_notice = (
                "━━━━━━━━━━━━━━━━━━\n"
                "✅ **ORDER COMPLETED NOTIFICATION**\n"
                "━━━━━━━━━━━━━━━━━━\n"
                f"🆔 **User ID:** `{u_id}`\n"
                f"⏱ **Completed At:** {completed_time_ist}\n"
                "📌 **Status:** Finished & Delivered!\n"
                "━━━━━━━━━━━━━━━━━━"
            )
            
            try:
                await bot.send_message(
                    u_id, 
                    f"{comp_text}\n\n👇 **Main Menu:**", 
                    reply_markup=get_main_menu(),
                    parse_mode="Markdown"
                )
                
                await bot.send_message(ADMIN_ID, admin_completion_notice, parse_mode="Markdown")
                
                for m_id in user_messages_to_delete:
                    try:
                        await bot.delete_message(chat_id=u_id, message_id=m_id)
                    except Exception:
                        pass
                
                try:
                    await bot.delete_message(chat_id=ADMIN_ID, message_id=box_msg_id)
                except Exception:
                    pass
                    
            except Exception as e:
                print(f"Error in finish task: {e}")

        asyncio.create_task(finish_and_delete())
    except Exception as e:
        print(f"Error in get_admin_time: {e}")

# --- Forward Support Messages ---
@dp.message_handler(state=OrderStates.in_support, content_types=types.ContentTypes.ANY)
async def customer_support_message(msg: types.Message):
    try:
        user_id = msg.from_user.id
        username = f"@{msg.from_user.username}" if msg.from_user.username else "No Username"
        first_name = msg.from_user.first_name or "User"
        profile_link = f"tg://user?id={user_id}"
        
        header = (
            "━━━━━━━━━━━━━━━━━━\n"
            "💬 **SUPPORT MESSAGE**\n"
            "━━━━━━━━━━━━━━━━━━\n"
            f"👤 **Name:** [{first_name}]({profile_link})\n"
            f"🏷 **Username:** {username}\n"
            f"🆔 **User ID:** `{user_id}`\n"
            "━━━━━━━━━━━━━━━━━━"
        )
        try:
            await bot.send_message(ADMIN_ID, header, parse_mode="Markdown", disable_web_page_preview=True)
            await msg.forward(ADMIN_ID)
        except Exception:
            await bot.send_message(ADMIN_ID, header)
            await msg.forward(ADMIN_ID)
    except Exception as e:
        print(f"Support forward error: {e}")

# --- Global Admin Reply Handler ---
@dp.message_handler(content_types=types.ContentTypes.ANY)
async def global_message_handler(msg: types.Message):
    try:
        if msg.from_user.id == ADMIN_ID and msg.reply_to_message:
            try:
                replied_msg = msg.reply_to_message
                txt = replied_msg.text or replied_msg.caption or ""
                
                uid = None
                for line in txt.split('\n'):
                    if "🆔" in line and "ID:" in line:
                        clean_line = line.replace("🆔", "").replace("User ID:", "").replace("ID:", "").strip().replace("`", "")
                        uid = int(clean_line)
                        break
                
                if uid:
                    if msg.text:
                        await bot.send_message(uid, f"👨‍💻 **Admin Reply:**\n\n{msg.text}")
                    elif msg.photo:
                        await bot.send_photo(uid, msg.photo[-1].file_id, caption=f"👨‍💻 **Admin Reply:**\n\n{msg.caption or ''}")
                    elif msg.video:
                        await bot.send_video(uid, msg.video.file_id, caption=f"👨‍💻 **Admin Reply:**\n\n{msg.caption or ''}")
                    elif msg.document:
                        await bot.send_document(uid, msg.document.file_id, caption=f"👨‍💻 **Admin Reply:**\n\n{msg.caption or ''}")
                    
                    await msg.reply("✅ Reply sent successfully!")
                else:
                    await msg.reply("❌ Could not find User ID from this message. Please reply to a valid notification box.")
            except Exception as e:
                await msg.reply(f"❌ Error sending reply: {e}")
            return
    except Exception as e:
        print(f"Global message handler error: {e}")

# --- Execution Loop ---
if __name__ == '__main__':
    keep_alive()
    while True:
        try:
            print("Bot is running smoothly...")
            executor.start_polling(
                dp, 
                skip_updates=True, 
                relax=0.01, 
                timeout=20, 
                allowed_updates=types.AllowedUpdates.all()
            )
        except Exception as e:
            print(f"Crash prevented: {e}. Auto-restarting in 1 second...")
            import time
            time.sleep(1)
