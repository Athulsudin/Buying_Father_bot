import os
import asyncio
import threading
from flask import Flask
from datetime import datetime, timezone, timedelta
from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
import logging
logging.basicConfig(level=logging.ERROR)
from aiogram import executor

# --- Flask Server for 24/7 Uptime (Render / Keep Alive) ---
app = Flask('')
@app.route('/')
def home(): return "Bot is Alive!"

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
API_TOKEN = '8642149587:AAG6RS5Zz-rdNLcl22D7GjiWdAmdypcoxbM'
ADMIN_ID = 7616127905
QR_URL = 'https://ibb.co/kg2jT6ZF'

# Indian Standard Time (IST) Zone (+5:30)
IST = timezone(timedelta(hours=5, minutes=30))

bot = Bot(token=API_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)

class OrderStates(StatesGroup):
    wait_quantity = State()
    wait_payment_and_url = State()
    wait_admin_time = State()
    in_support = State()

SERVICES = {
    "bot": {"name": "🤖 Bot Followers"},
    "real": {"name": "🔥 Real Followers"},
    "likes": {"name": "❤️ Likes"}
}

def get_main_menu():
    kb = InlineKeyboardMarkup(row_width=1)
    for k, v in SERVICES.items():
        kb.add(InlineKeyboardButton(v['name'], callback_data=f"m_{k}"))
    kb.add(InlineKeyboardButton("💬 Chat to Admin", callback_data="chat_admin"))
    return kb

@dp.message_handler(commands=['start'])
async def start(msg: types.Message, state: FSMContext):
    try:
        if msg.from_user.id == ADMIN_ID: 
            return
        try:
            await state.finish()
        except Exception:
            pass
        
        welcome_text = (
            "🚀 Welcome to Owner Bot 🌟\n\n"
            "🥃 Hey! Thanks for reaching out.\n\n"
            "❗️ I’m currently busy or offline at the moment.\n"
            "✉️ Please leave your message, and I’ll respond as soon as I’m available.\n\n"
            "⏳ Your patience is greatly appreciated.\n"
            "━━━━━━━━━━━━━━━\n\n"
            "📣 𝗨𝗣𝗗𝗔𝗧𝗘𝖘 & 𝗣𝗥𝗜𝗖𝗘 𝗟𝗜𝗦𝗧\n\n"
            "➡️ @Bot_Owner_Official\n\n"
            "━━━━━━━━━━━━━━━\n\n"
            "✅ Latest Updates\n"
            "✅ Service Information\n"
            "✅ Price List\n"
            "✅ New Announcements\n\n"
            "⚪️ Thanks for contacting Owner Bot\n"
            "🦁 Have a great day!"
        )
        await msg.answer(welcome_text, reply_markup=get_main_menu())
    except Exception as e:
        print(f"Error in start command: {e}")

# --- Service Selection Handler ---
@dp.callback_query_handler(lambda c: c.data and c.data.startswith('m_'))
async def svc(cq: types.CallbackQuery, state: FSMContext):
    try:
        await cq.answer()
        s_type = cq.data.split('_')[1]
        if s_type not in SERVICES:
            await cq.message.answer("⚠️ Invalid service selected. Please try again from the menu.", reply_markup=get_main_menu())
            return
            
        await OrderStates.wait_quantity.set()
        await state.update_data(service=s_type)
        
        kb = InlineKeyboardMarkup(row_width=1)
        kb.add(InlineKeyboardButton("📌 More...", callback_data=f"more_{s_type}"))
        
        if s_type == "bot":
            text = "🔹 [ 🤖 Bot Followers ] (Low Speed ⏰ | No refill 🚫 | Delivery Time: 2 Hours and 45 Minutes):\n\nPrices:\n1k Bot — ₹49\n2k Bot — ₹79\n3k Bot — ₹100\n4k Bot — ₹120\n5k Bot — ₹140\n6k Bot — ₹160\n7k Bot — ₹180\n8k Bot — ₹200\n9k Bot — ₹220\n10k Bot — ₹250\n\n**Please enter your required quantity (e.g., 500, 1000):**"
        elif s_type == "real":
            text = "🔹 [ 🔥 Real Followers ] (Fast Delivery ⏰ | Refill 💵 | Delivery Time: 7 Hours and 8 Minutes):\n\nPrices:\n1k Real — ₹100\n2k Real — ₹145\n3k Real — ₹195\n4k Real — ₹245\n5k Real — ₹290\n\n**Please enter your required quantity (e.g., 1000, 2000):**"
        else:
            text = "🔹 [ ❤️ Likes ] (Lifetime 💯 | Fast delivery 📮 | Delivery Time: 3 Hours and 18 Minutes):\n\nPrices:\n1000 likes — ₹8\n2000 likes — ₹13\n3000 likes — ₹18\n4000 likes — ₹23\n5000 likes — ₹28\n6000 likes — ₹33\n7000 likes — ₹38\n8000 likes — ₹43\n9000 likes — ₹48\n10000 likes — ₹60\n\n**Please enter your required quantity (e.g., 1000, 2000):**"
            
        await bot.send_message(cq.from_user.id, text, reply_markup=kb)
    except Exception as e:
        print(f"Error in svc handler: {e}")

# --- More Button Handler ---
@dp.callback_query_handler(lambda c: c.data and c.data.startswith('more_'))
async def more_options(cq: types.CallbackQuery, state: FSMContext):
    try:
        await cq.answer()
        await OrderStates.in_support.set()
        
        cancel_kb = InlineKeyboardMarkup(row_width=1)
        cancel_kb.add(InlineKeyboardButton("❌ Cancel Support", callback_data="cancel_support"))
        
        await bot.send_message(
            cq.from_user.id,
            "💬 **More Package / Direct Support**\n\n"
            "If you need more packages or custom requests, please chat directly with the admin here.\n"
            "Send your message below, and our admin will assist you shortly.",
            reply_markup=cancel_kb
        )
    except Exception as e:
        print(f"Error in more_options: {e}")

# --- Main Menu 'Chat to Admin' Button Handler ---
@dp.callback_query_handler(lambda c: c.data == 'chat_admin')
async def start_support(cq: types.CallbackQuery, state: FSMContext):
    try:
        await cq.answer()
        await OrderStates.in_support.set()
        
        cancel_kb = InlineKeyboardMarkup(row_width=1)
        cancel_kb.add(InlineKeyboardButton("❌ Cancel Support", callback_data="cancel_support"))
        
        await bot.send_message(
            cq.from_user.id,
            "💬 **Chat to Admin Mode Activated**\n\n"
            "You can now send your message here, and it will be forwarded directly to the admin.\n\n"
            "Click the button below to exit.",
            reply_markup=cancel_kb
        )
    except Exception as e:
        print(f"Error in start_support: {e}")

@dp.callback_query_handler(lambda c: c.data == 'cancel_support', state=OrderStates.in_support)
async def cancel_support(cq: types.CallbackQuery, state: FSMContext):
    try:
        await cq.answer("Support closed.")
        await state.finish()
        await bot.send_message(cq.from_user.id, "You are back to the main menu. Choose a service:", reply_markup=get_main_menu())
    except Exception as e:
        print(f"Error in cancel_support: {e}")

# --- Quantity Received -> Send QR Code with Live 5-Min Countdown ---
@dp.message_handler(state=OrderStates.wait_quantity)
async def handle_quantity(msg: types.Message, state: FSMContext):
    try:
        if msg.text and msg.text.isdigit():
            await state.update_data(quantity=msg.text, url_verified=False)
            await OrderStates.wait_payment_and_url.set()
            
            initial_caption = (
                f"📦 **Quantity:** {msg.text}\n\n"
                f"📲 Please scan the QR code above for payment.\n"
                f"Step 1: Send your **Instagram Profile/Post URL** first.\n"
                f"Step 2: Send the **Payment Screenshot** after.\n\n"
                "⏳ Time Remaining: 05:00"
            )
            try:
                qr_msg = await bot.send_photo(msg.chat.id, QR_URL, caption=initial_caption)
            except Exception:
                qr_msg = await msg.answer(initial_caption)

            async def live_countdown_timer(chat_id, message_id):
                for remaining in range(299, -1, -1):
                    await asyncio.sleep(1)
                    try:
                        current_state = await dp.current_state(user=chat_id).get_state()
                        if current_state != 'OrderStates:wait_payment_and_url':
                            return
                        
                        if remaining % 5 == 0 or remaining < 10:
                            mins, secs = divmod(remaining, 60)
                            time_str = f"{mins:02d}:{secs:02d}"
                            data_dict = await dp.current_state(user=chat_id).get_data()
                            qty = data_dict.get('quantity', 'N/A')
                            updated_caption = (
                                f"📦 **Quantity:** {qty}\n\n"
                                f"📲 Please scan the QR code above for payment.\n"
                                f"Step 1: Send your **Instagram URL** first.\n"
                                f"Step 2: Send the **Payment Screenshot** after.\n\n"
                                f"⏳ Time Remaining: {time_str}"
                            )
                            try:
                                await bot.edit_message_caption(chat_id=chat_id, message_id=message_id, caption=updated_caption)
                            except Exception:
                                pass
                    except Exception:
                        pass
                
                try:
                    current_state = await dp.storage.get_state(chat=chat_id, user=chat_id)
                    if current_state == 'OrderStates:wait_payment_and_url':
                        await dp.storage.finish(chat=chat_id, user=chat_id)
                        try:
                            await bot.delete_message(chat_id=chat_id, message_id=message_id)
                        except Exception:
                            pass
                        await bot.send_message(
                            chat_id,
                            "⚠️ **Time expired!** The QR scanner has been automatically deleted. Please start again from the menu.",
                            reply_markup=get_main_menu()
                        )
                except Exception:
                    pass

            asyncio.create_task(live_countdown_timer(msg.chat.id, qr_msg.message_id))
        else:
            await msg.answer("⚠️ Please enter a valid numerical quantity (e.g. 500, 1000):")
    except Exception as e:
        print(f"Error in handle_quantity: {e}")

# --- Handle Payment Details with Strict Validation for URL and Screenshot ---
@dp.message_handler(state=OrderStates.wait_payment_and_url, content_types=['photo', 'text', 'video', 'document'])
async def handle_payment_and_url(msg: types.Message, state: FSMContext):
    try:
        data = await state.get_data()
        uid = msg.from_user.id
        s_type = data.get('service', 'bot')
        qty = data.get('quantity', 'N/A')
        url_verified = data.get('url_verified', False)
        
        username = f"@{msg.from_user.username}" if msg.from_user.username else "Private Account / No Username"
        first_name = msg.from_user.first_name or "User"
        profile_link = f"tg://user?id={uid}"
        
        # 1. Handling Text (Instagram URL Validation)
        if msg.text:
            text_content = msg.text.strip()
            if "instagram.com" in text_content.lower() or "instagr.am" in text_content.lower():
                await state.update_data(url=text_content, url_verified=True)
                await msg.answer("✅ **Instagram URL Verified Successfully!**\n\n📸 Now please send your **Payment Screenshot**.")
                return
            else:
                await msg.answer(
                    "❌ **Invalid Link!**\n"
                    "⚠️ Please send a valid **Instagram URL** (e.g., https://instagram.com/...)."
                )
                return

        # 2. Handling Photo (Payment Screenshot Validation)
        elif msg.photo:
            if not url_verified:
                await msg.answer(
                    "❌ **Action Required!**\n"
                    "⚠️ Please send your **Instagram URL** first before sending the payment screenshot."
                )
                return
            
            url_data = data.get('url', 'Not Provided')
            
            admin_box = (
                "━━━━━━━━━━━━━━━━━━\n"
                "📥 **NEW ORDER RECEIVED**\n"
                "━━━━━━━━━━━━━━━━━━\n"
                f"👤 **Name:** [{first_name}]({profile_link})\n"
                f"🏷 **Username:** {username}\n"
                f"🆔 **User ID:** `{uid}`\n"
                f"🛒 **Service:** {SERVICES.get(s_type, {}).get('name', 'Service')}\n"
                f"📊 **Quantity:** {qty}\n"
                f"🔗 **URL:** {url_data}\n"
                "━━━━━━━━━━━━━━━━━━"
            )
            try:
                sent_box = await bot.send_message(ADMIN_ID, admin_box, parse_mode="Markdown", disable_web_page_preview=True)
                await msg.forward(ADMIN_ID)
            except Exception:
                sent_box = await bot.send_message(ADMIN_ID, admin_box)
                await msg.forward(ADMIN_ID)
            
            ap_markup = InlineKeyboardMarkup(row_width=1)
            ap_markup.add(
                InlineKeyboardButton("✅ Approve", callback_data=f"ap_{uid}_{sent_box.message_id}"),
                InlineKeyboardButton("❌ Reject", callback_data=f"rj_{uid}_{sent_box.message_id}")
            )
            await bot.send_message(ADMIN_ID, "👇 To approve, click 'Approve' and reply with your custom delivery time:", reply_markup=ap_markup)
            
            await msg.answer("✅ **Payment Screenshot Verified & Received!** Admin will verify and process your order shortly.")
            await state.finish()
        else:
            await msg.answer(
                "❌ **Invalid Format!**\n"
                "⚠️ Please send a valid Instagram URL (text) or a payment screenshot (image)."
            )
    except Exception as e:
        print(f"Error in handle_payment_and_url: {e}")

# --- Admin Action: Approve / Reject ---
@dp.callback_query_handler(lambda c: c.data and (c.data.startswith('ap_') or c.data.startswith('rj_')))
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
        await bot.send_message(ADMIN_ID, f"✍️ Reply to this message with the custom delivery time for User ID `{u_id}` (Example: `10m`, `1h`, `2 Hours`):")
        
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
            "🤖 *Your order is being handled safely & securely.*"
        )
        
        user_messages_to_delete = []
        try:
            rec_msg = await bot.send_message(u_id, receipt)
            user_messages_to_delete.append(rec_msg.message_id)
        except Exception:
            return
            
        await msg.reply(f"✅ Successfully set delivery time as: **{custom_time}**")
        
        try:
            await bot.edit_message_text(f"✅ **Order Approved** | Delivery Time: {custom_time}", ADMIN_ID, orig_msg_id)
        except Exception:
            pass
            
        async def finish_and_delete():
            await asyncio.sleep(15)
            
            comp_text = (
                "━━━━━━━━━━━━━━━━━━\n"
                "🎉 **ORDER COMPLETION NOTICE** 🎉\n"
                "━━━━━━━━━━━━━━━━━━\n\n"
                "✨ Dear Valued Customer,\n"
                "Your requested service has been **fully delivered** successfully!\n\n"
                "🔹 **Status:** 100% Completed ✅\n"
                "🤝 **Thank you for trusting us!**\n"
                "━━━━━━━━━━━━━━━━━━"
            )
            
            completed_time_ist = datetime.now(IST).strftime('%Y-%m-%d %H:%M')
            admin_completion_notice = (
                "━━━━━━━━━━━━━━━━━━\n"
                "✅ **ORDER COMPLETED NOTIFICATION**\n"
                "━━━━━━━━━━━━━━━━━━\n"
                f"🆔 **User ID:** `{u_id}`\n"
                f"⏱ **Completed At:** {completed_time_ist}\n"
                "📌 **Status:** Successfully Finished & Delivered!\n"
                "━━━━━━━━━━━━━━━━━━"
            )
            
            try:
                sent_final = await bot.send_message(
                    u_id, 
                    f"{comp_text}\n\n👇 **Main Menu:**", 
                    reply_markup=get_main_menu()
                )
                
                await bot.send_message(ADMIN_ID, admin_completion_notice)
                
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

# --- Support Message Handler (Silent Forwarding) ---
@dp.message_handler(state=OrderStates.in_support, content_types=['text', 'photo', 'video', 'document'])
async def customer_support_message(msg: types.Message):
    try:
        user_id = msg.from_user.id
        username = f"@{msg.from_user.username}" if msg.from_user.username else "Private Account / No Username"
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

# --- Global Admin Reply Handler (Crash-Proof Swipe Reply) ---
@dp.message_handler(content_types=['text', 'photo', 'video', 'document'])
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
                    
                    await msg.reply("✅ Reply sent successfully to user!")
                else:
                    await msg.reply("❌ Could not find User ID from this message. Make sure you are replying to a support/order header box.")
            except Exception as e:
                await msg.reply(f"❌ Error sending reply: {e}")
            return
    except Exception as e:
        print(f"Global message handler error: {e}")

# --- Crash-Proof & Auto Recovery Loop with Maximum Exception Guards ---
if __name__ == '__main__':
    keep_alive()
    while True:
        try:
            print("Bot is running with ultimate crash-proof protection...")
            executor.start_polling(
                dp, 
                skip_updates=True, 
                relax=0.01, 
                timeout=20, 
                allowed_updates=types.AllowedUpdates.all()
            )
        except Exception as e:
            print(f"Caught critical crash: {e}. Auto-restarting instantly in 1 second...")
            import time
            time.sleep(1)



