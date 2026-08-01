import os
import asyncio
import threading
from flask import Flask
from datetime import datetime
from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram import executor

# --- Flask Server for 24/7 Uptime (Render / Keep Alive) ---
app = Flask('')
@app.route('/')
def home(): return "Bot is Alive!"

def keep_alive():
    port = int(os.environ.get('PORT', 10000))
    threading.Thread(target=lambda: app.run(host='0.0.0.0', port=port)).start()

# --- Configurations ---
API_TOKEN = '8642149587:AAEQCxPaEUe_-rgXQZeHxawhAZqXWwVveQ'
ADMIN_ID = 7616127905
QR_URL = 'https://ibb.co/kg2jT6ZF'

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

def menu_keyboard():
    kb = InlineKeyboardMarkup(row_width=1)
    for k, v in SERVICES.items():
        kb.add(
            InlineKeyboardButton(v['name'], callback_data=f"m_{k}"),
            InlineKeyboardButton("📌 More", callback_data=f"more_{k}")
        )
    kb.add(InlineKeyboardButton("💬 Chat to Admin", callback_data="chat_admin"))
    return kb

@dp.message_handler(commands=['start'])
async def start(msg: types.Message, state: FSMContext):
    if msg.from_user.id == ADMIN_ID: return
    await state.finish()
    await msg.answer("✨ **Welcome to Our Service Bot!**\n\nPlease choose a service or contact support below:", reply_markup=menu_keyboard())

# --- Service Selection Handler ---
@dp.callback_query_handler(lambda c: c.data.startswith('m_'))
async def svc(cq: types.CallbackQuery, state: FSMContext):
    await cq.answer()
    s_type = cq.data.split('_')[1]
    await OrderStates.wait_quantity.set()
    await state.update_data(service=s_type)
    await bot.send_message(cq.from_user.id, f"🛒 **Selected Service:** {SERVICES[s_type]['name']}\n\nPlease enter your required quantity (e.g., 500, 1000):")

# --- More Button Handler ---
@dp.callback_query_handler(lambda c: c.data.startswith('more_'))
async def more_options(cq: types.CallbackQuery, state: FSMContext):
    await cq.answer()
    await OrderStates.in_support.set()
    
    cancel_kb = InlineKeyboardMarkup(row_width=1)
    cancel_kb.add(InlineKeyboardButton("❌ Close Support", callback_data="cancel_support"))
    
    await bot.send_message(
        cq.from_user.id,
        "💬 **Please direct contact admin**\n\n"
        "You can send your queries here, and our admin will assist you shortly.\n\n"
        "Click the button below when you want to return.",
        reply_markup=cancel_kb
    )

# --- Main Menu 'Chat to Admin' Button Handler ---
@dp.callback_query_handler(lambda c: c.data == 'chat_admin')
async def start_support(cq: types.CallbackQuery, state: FSMContext):
    await cq.answer()
    await OrderStates.in_support.set()
    
    cancel_kb = InlineKeyboardMarkup(row_width=1)
    cancel_kb.add(InlineKeyboardButton("❌ Close Support", callback_data="cancel_support"))
    
    await bot.send_message(
        cq.from_user.id,
        "💬 **Chat to Admin Mode Activated**\n\n"
        "You can now send your message here, and it will be forwarded directly to the admin.\n\n"
        "Click the button below to exit.",
        reply_markup=cancel_kb
    )

@dp.callback_query_handler(lambda c: c.data == 'cancel_support', state=OrderStates.in_support)
async def cancel_support(cq: types.CallbackQuery, state: FSMContext):
    await cq.answer("Support closed.")
    await state.finish()
    await bot.send_message(cq.from_user.id, "You are back to the main menu. Choose a service:", reply_markup=menu_keyboard())

# --- Quantity Received -> Send QR Code (Scanner) with Live 5-Min Countdown ---
@dp.message_handler(state=OrderStates.wait_quantity)
async def handle_quantity(msg: types.Message, state: FSMContext):
    if msg.text:
        await state.update_data(quantity=msg.text)
        await OrderStates.wait_payment_and_url.set()
        
        initial_caption = (
            f"📦 **Quantity:** {msg.text}\n\n"
            f"📲 Please scan the QR code above for payment.\n"
            f"After payment, send your **Instagram URL** and the **Payment Screenshot** here.\n\n"
            "⏳ Time Remaining: 05:00"
        )
        try:
            qr_msg = await bot.send_photo(msg.chat.id, QR_URL, caption=initial_caption)
        except:
            qr_msg = await msg.answer(initial_caption)

        async def live_countdown_timer(chat_id, message_id):
            for remaining in range(299, -1, -1):
                await asyncio.sleep(1)
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
                        f"After payment, send your **Instagram URL** and the **Payment Screenshot** here.\n\n"
                        f"⏳ Time Remaining: {time_str}"
                    )
                    try:
                        await bot.edit_message_caption(chat_id=chat_id, message_id=message_id, caption=updated_caption)
                    except:
                        pass
            
            current_state = await dp.current_state(user=chat_id).get_state()
            if current_state == 'OrderStates:wait_payment_and_url':
                await dp.current_state(user=chat_id).finish()
                try:
                    await bot.delete_message(chat_id=chat_id, message_id=message_id)
                except:
                    pass
                await bot.send_message(
                    chat_id,
                    "⚠️ **Time expired!** The QR scanner has been automatically deleted. Please start again from the menu.",
                    reply_markup=menu_keyboard()
                )

        asyncio.create_task(live_countdown_timer(msg.chat.id, qr_msg.message_id))
    else:
        await msg.answer("⚠️ Please enter a valid quantity number:")

# --- Handle Payment Details (Instagram URL + Screenshot) ---
@dp.message_handler(state=OrderStates.wait_payment_and_url, content_types=['photo', 'text'])
async def handle_payment_and_url(msg: types.Message, state: FSMContext):
    data = await state.get_data()
    uid = msg.from_user.id
    s_type = data.get('service', 'bot')
    qty = data.get('quantity', 'N/A')
    username = msg.from_user.username or "No Username"
    first_name = msg.from_user.first_name or "User"
    
    if msg.text and "instagram.com" in msg.text:
        await state.update_data(url=msg.text)
        await msg.answer("✅ **Instagram URL received!** Now please send the **payment screenshot**.")
        return
    elif msg.photo:
        url_data = data.get('url', 'Not Provided')
        
        admin_box = (
            "━━━━━━━━━━━━━━━━━━\n"
            "📥 **NEW ORDER RECEIVED**\n"
            "━━━━━━━━━━━━━━━━━━\n"
            f"👤 **Name:** {first_name}\n"
            f"🏷 **Username:** @{username}\n"
            f"🆔 **User ID:** `{uid}`\n"
            f"🛒 **Service:** {SERVICES[s_type]['name']}\n"
            f"📊 **Quantity:** {qty}\n"
            f"🔗 **URL:** {url_data}\n"
            "━━━━━━━━━━━━━━━━━━"
        )
        sent_box = await bot.send_message(ADMIN_ID, admin_box)
        await msg.forward(ADMIN_ID)
        
        ap_markup = InlineKeyboardMarkup(row_width=1)
        ap_markup.add(
            InlineKeyboardButton("✅ Approve", callback_data=f"ap_{uid}_{sent_box.message_id}"),
            InlineKeyboardButton("❌ Reject", callback_data=f"rj_{uid}_{sent_box.message_id}")
        )
        await bot.send_message(ADMIN_ID, "👇 To approve, click 'Approve' and reply with your custom delivery time:", reply_markup=ap_markup)
        
        await msg.answer("✅ **Screenshot received!** Admin will verify and process your order shortly.")
        await state.finish()
    else:
        await msg.answer("⚠️ Please send a valid Instagram URL or the payment screenshot image.")

# --- Admin Action: Approve / Reject ---
@dp.callback_query_handler(lambda c: c.data.startswith('ap_') or c.data.startswith('rj_'))
async def admin_actions(cq: types.CallbackQuery, state: FSMContext):
    if cq.from_user.id != ADMIN_ID: return
    parts = cq.data.split('_')
    action = parts[0]
    u_id = int(parts[1])
    box_msg_id = int(parts[2])
    
    if action == 'rj':
        await bot.send_message(u_id, "❌ Your payment was rejected or invalid. Please contact support.")
        await cq.answer("Order Rejected")
        try:
            await bot.edit_message_text("❌ Order Rejected.", ADMIN_ID, cq.message.message_id)
        except:
            pass
        return
        
    await cq.answer()
    await bot.send_message(ADMIN_ID, f"✍️ Reply to this message with the custom delivery time for User ID `{u_id}` (Example: `10 Hours`, `2 Days`):")
    
    admin_state = dp.current_state(user=ADMIN_ID)
    await admin_state.set_state(OrderStates.wait_admin_time)
    await admin_state.update_data(target_uid=u_id, orig_msg_id=cq.message.message_id, box_msg_id=box_msg_id)

@dp.message_handler(state=OrderStates.wait_admin_time)
async def get_admin_time(msg: types.Message, state: FSMContext):
    if msg.from_user.id != ADMIN_ID: return
    data = await state.get_data()
    u_id = data.get('target_uid')
    orig_msg_id = data.get('orig_msg_id')
    box_msg_id = data.get('box_msg_id')
    custom_time = msg.text
    
    await state.finish()
    
    start_time = datetime.now().strftime("%Y-%m-%d %H:%M")
    
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
    rec_msg = await bot.send_message(u_id, receipt)
    await msg.reply(f"✅ Successfully set delivery time as: **{custom_time}**")
    
    try:
        await bot.edit_message_text(f"✅ **Order Approved** | Delivery Time: {custom_time}", ADMIN_ID, orig_msg_id)
    except:
        pass
        
    async def finish_and_delete():
        await asyncio.sleep(25)
        
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
        
        admin_completion_notice = (
            "━━━━━━━━━━━━━━━━━━\n"
            "✅ **ORDER COMPLETED NOTIFICATION**\n"
            "━━━━━━━━━━━━━━━━━━\n"
            f"🆔 **User ID:** `{u_id}`\n"
            f"⏱ **Completed At:** {datetime.now().strftime('%Y-%m-%d %H:%M')}\n"
            "📌 **Status:** Successfully Finished & Delivered!\n"
            "━━━━━━━━━━━━━━━━━━"
        )
        
        try:
            sent_final = await bot.send_message(u_id, comp_text, reply_markup=menu_keyboard())
            await bot.send_message(ADMIN_ID, admin_completion_notice)
            
            await asyncio.sleep(10)
            await sent_final.delete()
            await rec_msg.delete()
            await bot.delete_message(ADMIN_ID, box_msg_id)
        except Exception as e:
            print(f"Error in finish task: {e}")

    asyncio.create_task(finish_and_delete())

# --- Chat to Admin / Support Message Handler ---
@dp.message_handler(state=OrderStates.in_support, content_types=['text', 'photo', 'video', 'document'])
async def customer_support_message(msg: types.Message):
    user_id = msg.from_user.id
    username = msg.from_user.username or "No Username"
    first_name = msg.from_user.first_name or "User"
    
    header = (
        "━━━━━━━━━━━━━━━━━━\n"
        "💬 **SUPPORT MESSAGE**\n"
        "━━━━━━━━━━━━━━━━━━\n"
        f"👤 **Name:** {first_name}\n"
        f"🏷 **Username:** @{username}\n"
        f"🆔 **User ID:** `{user_id}`\n"
        "━━━━━━━━━━━━━━━━━━"
    )
    await bot.send_message(ADMIN_ID, header)
    await msg.forward(ADMIN_ID)
    await msg.reply("✅ **Your message has been sent to the admin.**")

@dp.message_handler(content_types=['text', 'photo', 'video', 'document'])
async def global_message_handler(msg: types.Message):
    if msg.from_user.id == ADMIN_ID and msg.reply_to_message:
        try:
            txt = msg.reply_to_message.text or msg.reply_to_message.caption
            uid = int([x for x in txt.split('\n') if "🆔" in x and "ID:" in x][0].replace("🆔", "").replace("User ID:", "").replace("ID:", "").strip().replace("`", ""))
            
            sent_msg = await bot.send_message(uid, f"👨‍💻 **Admin Reply:**\n\n{msg.text}")
            await msg.reply("✅ Reply sent successfully!")
            
            async def del_support():
                await asyncio.sleep(15)
                try: await sent_msg.delete()
                except: pass
            asyncio.create_task(del_support())
        except Exception as e:
            await msg.reply(f"❌ Error sending reply: {e}")
        return

# --- Crash-Proof & Auto Recovery Loop ---
if __name__ == '__main__':
    keep_alive()
    while True:
        try:
            print("Bot is running securely...")
            executor.start_polling(dp, skip_updates=True)
        except Exception as e:
            print(f"Error occurred: {e}. Restarting in 5 seconds...")
            asyncio.sleep(5)


