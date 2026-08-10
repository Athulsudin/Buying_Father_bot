import asyncio
from datetime import datetime, timedelta, timezone
import email
from email.header import decode_header
import imaplib
import io
import json
import logging
import os
import re
import threading
from aiogram import Bot, Dispatcher, executor, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from flask import Flask

# QR Code-ൽ Green Tick ചേർക്കാൻ PIL (Pillow) ഉപയോഗിക്കുന്നു
from PIL import Image, ImageDraw
import requests

logging.basicConfig(level=logging.ERROR)

# --- Gmail Auto Verification Configuration ---
GMAIL_USER = "athulsudin37@gmail.com"  # നിങ്ങളുടെ ഫാംപേ ലഭിക്കുന്ന Gmail ID
GMAIL_APP_PASS = "vgsa letp vopb tofs"  # App Password

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
        "title": (
            "🔹 [ 🤖 Bot Followers ]\n*(Low Speed ⏰ | No refill 🚫 | Delivery"
            " Time: {time})*"
        ),
        "delivery_time": "2 Hours and 45 Minutes",
        "plans": [
            {"qty": "1000", "price": 30, "text": "🤖 1k Bot — ₹{price}"},
            {"qty": "2000", "price": 60, "text": "🤖 2k Bot — ₹{price}"},
            {"qty": "3000", "price": 90, "text": "🤖 3k Bot — ₹{price}"},
            {"qty": "4000", "price": 120, "text": "🤖 4k Bot — ₹{price}"},
            {"qty": "5000", "price": 150, "text": "🤖 5k Bot — ₹{price}"},
        ],
    },
    "real": {
        "title": (
            "🔹 [ 🔥 Real Followers ]\n*(Fast Delivery ⏰ | Refill 💵 | Delivery"
            " Time: {time})*"
        ),
        "delivery_time": "7 Hours and 8 Minutes",
        "plans": [
            {"qty": "1000", "price": 55, "text": "🔥 1k Real — ₹{price}"},
            {"qty": "2000", "price": 110, "text": "🔥 2k Real — ₹{price}"},
            {"qty": "3000", "price": 165, "text": "🔥 3k Real — ₹{price}"},
            {"qty": "4000", "price": 220, "text": "🔥 4k Real — ₹{price}"},
            {"qty": "5000", "price": 275, "text": "🔥 5k Real — ₹{price}"},
        ],
    },
    "likes": {
        "title": (
            "🔹 [ ❤️ Likes ]\n*(Lifetime 💯 | Fast delivery 📮 | Delivery"
            " Time: {time})*"
        ),
        "delivery_time": "3 Hours and 18 Minutes",
        "plans": [
            {"qty": "1000", "price": 8, "text": "❤️ 1000 Likes — ₹{price}"},
            {"qty": "2000", "price": 16, "text": "❤️ 2000 Likes — ₹{price}"},
            {"qty": "3000", "price": 24, "text": "❤️ 3000 Likes — ₹{price}"},
            {"qty": "4000", "price": 32, "text": "❤️ 4000 Likes — ₹{price}"},
            {"qty": "5000", "price": 40, "text": "❤️ 5000 Likes — ₹{price}"},
        ],
    },
}

# Dynamic Custom Limits & Names
CUSTOM_LIMITS = {
    "bot": {"min": 500, "max": 100000, "name": "🤖 Bot Followers"},
    "real": {"min": 500, "max": 100000, "name": "🔥 Real Followers"},
    "likes": {"min": 1000, "max": 100000, "name": "❤️ Likes"},
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


def get_1k_rate(s_type):
  try:
    return SERVICES_DATA[s_type]["plans"][0]["price"]
  except Exception:
    fallback = {"bot": 30, "real": 55, "likes": 8}
    return fallback.get(s_type, 30)


# --- Gmail IMAP Auto Verification Engine ---
def verify_utr_from_gmail(user_utr):
  try:
    mail = imaplib.IMAP4_SSL("imap.gmail.com")
    mail.login(GMAIL_USER, GMAIL_APP_PASS)
    mail.select("inbox")

    status, messages = mail.search(None, 'FROM "noreply@fampay.in"')
    if status != "OK" or not messages[0]:
      status, messages = mail.search(None, "ALL")

    email_ids = messages[0].split()

    for e_id in reversed(email_ids[-10:]):  # പരിശോധിക്കുന്നു
      res, msg_data = mail.fetch(e_id, "(RFC822)")
      for response_part in msg_data:
        if isinstance(response_part, tuple):
          msg = email.message_from_bytes(response_part[1])
          body = ""
          if msg.is_multipart():
            for part in msg.walk():
              if part.get_content_type() == "text/plain":
                body = part.get_payload(decode=True).decode(errors="ignore")
          else:
            body = msg.get_payload(decode=True).decode(errors="ignore")

          if str(user_utr) in body:
            mail.logout()
            return True

    mail.logout()
    return False
  except Exception as e:
    print(f"Gmail IMAP Error: {e}")
    return False


# --- Function to Draw Green Tick Mark Overlay on QR Image ---
def generate_green_tick_qr(qr_url):
  try:
    response = requests.get(qr_url, timeout=10)
    base_img = Image.open(io.BytesIO(response.content)).convert("RGBA")

    width, height = base_img.size
    overlay = Image.new("RGBA", base_img.size, (255, 255, 255, 0))
    draw = ImageDraw.Draw(overlay)

    center_x, center_y = width // 2, height // 2
    radius = min(width, height) // 5

    # Green Circle
    draw.ellipse(
        [
            (center_x - radius, center_y - radius),
            (center_x + radius, center_y + radius),
        ],
        fill=(34, 197, 94, 230),
        outline=(255, 255, 255, 255),
        width=6,
    )

    # White Checkmark inside
    p1 = (center_x - int(radius * 0.4), center_y)
    p2 = (center_x - int(radius * 0.1), center_y + int(radius * 0.35))
    p3 = (center_x + int(radius * 0.4), center_y - int(radius * 0.35))

    draw.line([p1, p2, p3], fill=(255, 255, 255, 255), width=int(radius * 0.18))

    combined = Image.alpha_composite(base_img, overlay).convert("RGB")
    bio = io.BytesIO()
    bio.name = "success_qr.jpg"
    combined.save(bio, "JPEG")
    bio.seek(0)
    return bio
  except Exception as e:
    print(f"Error generating green tick image: {e}")
    return None


# --- Flask Server ---
app = Flask("")


@app.route("/")
def home():
  return "Bot is Alive!"


def keep_alive():
  def run_flask():
    try:
      port = int(os.environ.get("PORT", 10000))
      app.run(
          host="0.0.0.0",
          port=port,
          use_reloader=False,
          debug=False,
          threaded=True,
      )
    except Exception as e:
      print(f"Flask internal error: {e}")

  t = threading.Thread(target=run_flask, daemon=True)
  t.start()


# --- Configurations ---
bot = Bot(token="8642149587:AAGCDZqRoYxFAGGMKjLAAQZQG0S_BGdfQGw")
ADMIN_ID = 7616127905
QR_URL = "https://i.ibb.co/jdffT3p/qr.jpg"  # Direct Image URL
PAYMENT_PROOF_CHANNEL = "https://t.me/+hLxD0623ZEs1M2I1"

IST = timezone(timedelta(hours=5, minutes=30))

storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)


# --- States ---
class OrderStates(StatesGroup):
  wait_custom_qty = State()
  wait_utr = State()
  wait_ig_link = State()  # Instagram Link വാങ്ങാൻ പുതിയ സ്റ്റേറ്റ്
  in_support = State()


# --- Keyboards ---
def get_main_menu():
  kb = InlineKeyboardMarkup(row_width=2)
  kb.add(InlineKeyboardButton("🛒 Shop Now", callback_data="buy_now"))
  kb.add(
      InlineKeyboardButton("🔑 My Orders", callback_data="my_orders"),
      InlineKeyboardButton("👤 Your Profile", callback_data="your_profile"),
  )
  kb.add(
      InlineKeyboardButton("📢 Pay Proof ↗️", url=PAYMENT_PROOF_CHANNEL),
      InlineKeyboardButton("💬 Support", callback_data="chat_admin"),
  )
  kb.add(InlineKeyboardButton("🎬 How to Use Bot", callback_data="how_to_use"))
  return kb


def get_services_menu():
  kb = InlineKeyboardMarkup(row_width=1)
  kb.add(
      InlineKeyboardButton("🤖 Bot Followers", callback_data="svc_bot"),
      InlineKeyboardButton("🔥 Real Followers", callback_data="svc_real"),
      InlineKeyboardButton("❤️ Likes", callback_data="svc_likes"),
      InlineKeyboardButton(
          "🔙 Back to Main Menu", callback_data="back_to_main"
      ),
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


def get_custom_keypad():
  kb = InlineKeyboardMarkup(row_width=3)
  kb.add(
      InlineKeyboardButton("1", callback_data="kpad_1"),
      InlineKeyboardButton("2", callback_data="kpad_2"),
      InlineKeyboardButton("3", callback_data="kpad_3"),
      InlineKeyboardButton("4", callback_data="kpad_4"),
      InlineKeyboardButton("5", callback_data="kpad_5"),
      InlineKeyboardButton("6", callback_data="kpad_6"),
      InlineKeyboardButton("7", callback_data="kpad_7"),
      InlineKeyboardButton("8", callback_data="kpad_8"),
      InlineKeyboardButton("9", callback_data="kpad_9"),
      InlineKeyboardButton("❌ CLEAR", callback_data="kpad_clear"),
      InlineKeyboardButton("0", callback_data="kpad_0"),
      InlineKeyboardButton("🔙 BACK", callback_data="back_to_shop"),
  )
  kb.add(InlineKeyboardButton("✅ CONFIRM ORDER", callback_data="kpad_confirm"))
  return kb


def get_custom_calc_text(s_type, qty):
  cfg = CUSTOM_LIMITS[s_type]
  rate_1k = get_1k_rate(s_type)
  unit_price = rate_1k / 1000.0
  total_price = round(qty * unit_price, 2)

  formatted_qty = f"{qty:,}"
  return (
      "✦━━━━━━━━━━━━━━━━━━✦\n"
      "   💎 **QUANTITY CALCULATOR** 💎\n"
      "✦━━━━━━━━━━━━━━━━━━✦\n\n"
      f"• **Service**  : {cfg['name']}\n"
      f"• **Rate**     : ₹{rate_1k} per 1,000\n\n"
      "───────────────\n"
      f"📊 **Entered Qty** : {formatted_qty}\n"
      f"💵 **Total Price** : ₹{total_price:.2f}\n"
      "───────────────\n\n"
      f"⚠️ **Limits**: {cfg['min']:,} to {cfg['max']:,}\n\n"
      "👇 *Enter quantity using keypad:*"
  )


# --- Start Command ---
@dp.message_handler(commands=["start"], state="*")
async def start(msg: types.Message, state: FSMContext):
  try:
    user_id = msg.from_user.id
    save_user(user_id)

    if user_id == ADMIN_ID:
      await msg.answer(
          "👨‍💻 **Admin Commands:**\n\n"
          "• `/broadcast <message>` - Send updates to all users\n"
          "• `/setprice <category> <index> <new_price>` - Change price\n"
          "• `/settime <category> <new_time>` - Change delivery time",
          parse_mode="Markdown",
      )
      return

    await state.finish()
    first_name = msg.from_user.first_name or "User"
    username = (
        f"@{msg.from_user.username}"
        if msg.from_user.username
        else "No Username"
    )
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
      await bot.send_message(
          ADMIN_ID,
          admin_notify,
          parse_mode="Markdown",
          disable_web_page_preview=True,
      )
    except Exception:
      pass

    await msg.answer(
        get_welcome_text(first_name),
        reply_markup=get_main_menu(),
        parse_mode="Markdown",
    )
  except Exception as e:
    print(f"Error in start command: {e}")


# --- Navigation Handlers ---
@dp.callback_query_handler(lambda c: c.data == "back_to_main", state="*")
async def back_to_main_handler(cq: types.CallbackQuery, state: FSMContext):
  try:
    await state.finish()
    await cq.answer()
    first_name = cq.from_user.first_name or "User"
    try:
      await cq.message.edit_text(
          get_welcome_text(first_name),
          reply_markup=get_main_menu(),
          parse_mode="Markdown",
      )
    except Exception:
      await cq.message.delete()
      await bot.send_message(
          cq.from_user.id,
          get_welcome_text(first_name),
          reply_markup=get_main_menu(),
          parse_mode="Markdown",
      )
  except Exception as e:
    print(f"Error in back_to_main: {e}")


@dp.callback_query_handler(lambda c: c.data == "my_orders", state="*")
async def my_orders_handler(cq: types.CallbackQuery):
  await cq.answer()
  kb = InlineKeyboardMarkup().add(
      InlineKeyboardButton("🔙 Back to Main Menu", callback_data="back_to_main")
  )
  text = (
      "🔑 **My Orders**\n\n📌 You currently have no active or previous orders."
  )
  await cq.message.edit_text(text, reply_markup=kb, parse_mode="Markdown")


@dp.callback_query_handler(lambda c: c.data == "your_profile", state="*")
async def your_profile_handler(cq: types.CallbackQuery):
  await cq.answer()
  u = cq.from_user
  kb = InlineKeyboardMarkup().add(
      InlineKeyboardButton("🔙 Back to Main Menu", callback_data="back_to_main")
  )
  text = (
      "👤 **YOUR PROFILE**\n\n"
      f"📛 **Name:** {u.first_name}\n"
      f"🏷 **Username:** @{u.username if u.username else 'N/A'}\n"
      f"🆔 **User ID:** `{u.id}`"
  )
  await cq.message.edit_text(text, reply_markup=kb, parse_mode="Markdown")


@dp.callback_query_handler(lambda c: c.data == "how_to_use", state="*")
async def how_to_use_handler(cq: types.CallbackQuery):
  await cq.answer()
  kb = InlineKeyboardMarkup().add(
      InlineKeyboardButton("🔙 Back to Main Menu", callback_data="back_to_main")
  )
  text = (
      "🎬 **HOW TO USE THE BOT**\n\n"
      "1️⃣ Tap on **🛒 Shop Now**.\n"
      "2️⃣ Select your desired service (Followers / Likes).\n"
      "3️⃣ Select a plan or use **✏️ Custom Quantity**.\n"
      "4️⃣ Scan QR code & pay via FamPay/UPI.\n"
      "5️⃣ Send the **12-digit UTR Number** to verify.\n"
      "6️⃣ Send your **Instagram Link** to activate the order!\n\n"
      "⚡ System will automatically process your order!"
  )
  await cq.message.edit_text(text, reply_markup=kb, parse_mode="Markdown")


@dp.callback_query_handler(lambda c: c.data == "back_to_shop", state="*")
async def back_to_shop_handler(cq: types.CallbackQuery, state: FSMContext):
  try:
    await state.finish()
    await cq.answer()
    try:
      await cq.message.edit_text(
          "🛍 **Select Your Instagram Service**\n\n*Choose an option below:*",
          reply_markup=get_services_menu(),
          parse_mode="Markdown",
      )
    except Exception:
      await cq.message.delete()
      await bot.send_message(
          cq.from_user.id,
          "🛍 **Select Your Instagram Service**\n\n*Choose an option below:*",
          reply_markup=get_services_menu(),
          parse_mode="Markdown",
      )
  except Exception as e:
    print(f"Error in back_to_shop: {e}")


@dp.callback_query_handler(lambda c: c.data == "buy_now", state="*")
async def buy_now_handler(cq: types.CallbackQuery):
  try:
    await cq.answer()
    try:
      await cq.message.edit_text(
          "🛍 **Select Your Instagram Service**\n\n*Choose an option below:*",
          reply_markup=get_services_menu(),
          parse_mode="Markdown",
      )
    except Exception:
      await bot.send_message(
          cq.from_user.id,
          "🛍 **Select Your Instagram Service**\n\n*Choose an option below:*",
          reply_markup=get_services_menu(),
          parse_mode="Markdown",
      )
  except Exception as e:
    print(f"Error in buy_now: {e}")


@dp.callback_query_handler(
    lambda c: c.data and c.data.startswith("svc_"), state="*"
)
async def show_service_plans(cq: types.CallbackQuery):
  try:
    await cq.answer()
    s_type = cq.data.split("_")[1]
    if s_type not in SERVICES_DATA:
      return

    s_info = SERVICES_DATA[s_type]
    kb = InlineKeyboardMarkup(row_width=1)

    for idx, plan in enumerate(s_info["plans"]):
      btn_text = plan["text"].format(price=plan["price"])
      kb.add(
          InlineKeyboardButton(btn_text, callback_data=f"plan_{s_type}_{idx}")
      )

    kb.add(
        InlineKeyboardButton(
            "✏️ Custom Quantity", callback_data=f"custom_{s_type}"
        )
    )
    kb.add(InlineKeyboardButton("🔙 Back to Shop", callback_data="back_to_shop"))

    title_text = s_info["title"].format(
        time=s_info.get("delivery_time", "Standard")
    )
    caption_text = (
        f"{title_text}\n\n**Choose a plan or enter Custom Quantity 📥**"
    )

    try:
      await cq.message.edit_text(
          caption_text, reply_markup=kb, parse_mode="Markdown"
      )
    except Exception:
      await bot.send_message(
          cq.from_user.id, caption_text, reply_markup=kb, parse_mode="Markdown"
      )
  except Exception as e:
    print(f"Error in show_service_plans: {e}")


# --- Custom Quantity Mode ---
@dp.callback_query_handler(
    lambda c: c.data and c.data.startswith("custom_"), state="*"
)
async def start_custom_quantity(cq: types.CallbackQuery, state: FSMContext):
  try:
    await cq.answer()
    s_type = cq.data.split("_")[1]

    await OrderStates.wait_custom_qty.set()
    await state.update_data(service=s_type, custom_qty=0)

    calc_text = get_custom_calc_text(s_type, 0)
    await cq.message.edit_text(
        calc_text, reply_markup=get_custom_keypad(), parse_mode="Markdown"
    )
  except Exception as e:
    print(f"Error in start_custom_quantity: {e}")


@dp.callback_query_handler(
    lambda c: c.data and c.data.startswith("kpad_"),
    state=OrderStates.wait_custom_qty,
)
async def process_keypad_input(cq: types.CallbackQuery, state: FSMContext):
  try:
    action = cq.data.split("_")[1]
    data = await state.get_data()
    s_type = data.get("service", "bot")
    current_qty = data.get("custom_qty", 0)
    cfg = CUSTOM_LIMITS[s_type]

    if action.isdigit():
      digit = int(action)
      new_qty = (current_qty * 10) + digit
      if new_qty > cfg["max"]:
        await cq.answer(f"⚠️ Maximum limit is {cfg['max']:,}!", show_alert=True)
        return
      await state.update_data(custom_qty=new_qty)
      await cq.answer()
      await cq.message.edit_text(
          get_custom_calc_text(s_type, new_qty),
          reply_markup=get_custom_keypad(),
          parse_mode="Markdown",
      )

    elif action == "clear":
      await state.update_data(custom_qty=0)
      await cq.answer("Cleared!")
      await cq.message.edit_text(
          get_custom_calc_text(s_type, 0),
          reply_markup=get_custom_keypad(),
          parse_mode="Markdown",
      )

    elif action == "confirm":
      if current_qty < cfg["min"]:
        await cq.answer(
            f"⚠️ Minimum quantity allowed is {cfg['min']:,}!", show_alert=True
        )
        return

      rate_1k = get_1k_rate(s_type)
      unit_price = rate_1k / 1000.0
      price = round(current_qty * unit_price, 2)

      await OrderStates.wait_utr.set()
      await state.update_data(
          service=s_type, quantity=str(current_qty), price=price
      )
      await cq.answer()
      await start_payment_session(
          cq.from_user.id, s_type, str(current_qty), price, state
      )

  except Exception as e:
    print(f"Error in process_keypad_input: {e}")


async def start_payment_session(chat_id, s_type, qty, price, state: FSMContext):
  qr_kb = InlineKeyboardMarkup(row_width=1)
  qr_kb.add(InlineKeyboardButton("🔙 Back to Shop", callback_data="back_to_shop"))

  initial_caption = (
      f"📦 **Quantity:** {qty}\n"
      f"💰 **Amount to Pay:** ₹{price}\n\n"
      "📲 Scan QR code above and complete your payment.\n\n"
      "👇 **After payment, send your 12-digit UTR / Reference Number below:**\n\n"
      "⏳ Time Remaining: 05:00"
  )

  try:
    qr_msg = await bot.send_photo(
        chat_id,
        QR_URL,
        caption=initial_caption,
        reply_markup=qr_kb,
        parse_mode="Markdown",
    )
  except Exception:
    qr_msg = await bot.send_message(
        chat_id, initial_caption, reply_markup=qr_kb, parse_mode="Markdown"
    )

  await state.update_data(qr_msg_id=qr_msg.message_id)

  async def live_countdown_timer(c_id, message_id):
    for remaining in range(299, -1, -1):
      await asyncio.sleep(1)
      try:
        current_state = await dp.current_state(user=c_id).get_state()
        if current_state != "OrderStates:wait_utr":
          return

        if remaining % 5 == 0 or remaining < 10:
          mins, secs = divmod(remaining, 60)
          time_str = f"{mins:02d}:{secs:02d}"
          data_dict = await dp.current_state(user=c_id).get_data()
          q_val = data_dict.get("quantity", qty)
          p_val = data_dict.get("price", price)
          updated_caption = (
              f"📦 **Quantity:** {q_val}\n"
              f"💰 **Amount to Pay:** ₹{p_val}\n\n"
              "📲 Scan QR code above and complete your payment.\n\n"
              "👇 **After payment, send your 12-digit UTR / Reference Number"
              " below:**\n\n"
              f"⏳ Time Remaining: {time_str}"
          )
          try:
            await bot.edit_message_caption(
                chat_id=c_id,
                message_id=message_id,
                caption=updated_caption,
                reply_markup=qr_kb,
                parse_mode="Markdown",
            )
          except Exception:
            pass
      except Exception:
        pass

    try:
      current_state = await dp.storage.get_state(chat=c_id, user=c_id)
      if current_state == "OrderStates:wait_utr":
        await dp.storage.finish(chat=c_id, user=c_id)
        try:
          await bot.delete_message(chat_id=c_id, message_id=message_id)
        except Exception:
          pass
        await bot.send_message(
            c_id,
            "⚠️ **Time expired!** Session ended. Please start again from the"
            " menu.",
            reply_markup=get_main_menu(),
            parse_mode="Markdown",
        )
    except Exception:
      pass

  asyncio.create_task(live_countdown_timer(chat_id, qr_msg.message_id))


# --- Plan Selection ---
@dp.callback_query_handler(
    lambda c: c.data and c.data.startswith("plan_"), state="*"
)
async def select_plan_handler(cq: types.CallbackQuery, state: FSMContext):
  try:
    await cq.answer()
    parts = cq.data.split("_")
    s_type = parts[1]
    idx = int(parts[2])

    plan_info = SERVICES_DATA[s_type]["plans"][idx]
    qty = plan_info["qty"]
    price = plan_info["price"]

    await OrderStates.wait_utr.set()
    await state.update_data(service=s_type, quantity=qty, price=price)
    await start_payment_session(cq.from_user.id, s_type, qty, price, state)

  except Exception as e:
    print(f"Error in select_plan_handler: {e}")


# --- STEP 1: Gmail Auto UTR Verification & Green Tick ---
@dp.message_handler(
    state=OrderStates.wait_utr, content_types=types.ContentTypes.TEXT
)
async def process_utr_verification(msg: types.Message, state: FSMContext):
  try:
    utr_input = msg.text.strip()

    if not (utr_input.isdigit() and len(utr_input) == 12):
      await msg.answer(
          "❌ **Invalid UTR Number!**\n\n⚠️ Please send a valid **12-digit UTR"
          " / Reference Number**.",
          parse_mode="Markdown",
      )
      return

    verifying_msg = await msg.answer(
        "🔍 **Checking Gmail for payment verification...**\n⏳ *Please wait"
        " 2 seconds...*",
        parse_mode="Markdown",
    )

    is_valid = await asyncio.to_thread(verify_utr_from_gmail, utr_input)

    if is_valid:
      data = await state.get_data()
      qr_msg_id = data.get("qr_msg_id")
      s_type = data.get("service", "bot")
      qty = data.get("quantity", "N/A")
      price = data.get("price", "N/A")
      uid = msg.from_user.id

      # Green Tick ഇമേജ് സൃഷ്‌ടിക്കുന്നു
      green_tick_file = await asyncio.to_thread(generate_green_tick_qr, QR_URL)

      if qr_msg_id and green_tick_file:
        try:
          # QR ഇമേജ് അപ്‌ഡേറ്റ് ചെയ്ത് Green Tick കാണിക്കുന്നു
          await bot.edit_message_media(
              chat_id=uid,
              message_id=qr_msg_id,
              media=types.InputMediaPhoto(
                  media=green_tick_file,
                  caption=(
                      "✅ **PAYMENT VERIFIED SUCCESSFULLY!**\n\n"
                      f"📦 Quantity: {qty}\n"
                      f"💰 Amount: ₹{price}\n"
                      f"🔢 UTR: `{utr_input}`"
                  ),
                  parse_mode="Markdown",
              ),
          )
        except Exception as e:
          print(f"Error updating QR image: {e}")

      try:
        await verifying_msg.delete()
      except Exception:
        pass

      # 3 സെക്കൻഡിനു ശേഷം QR കോഡ് മായ്ച്ചു കളയുന്നു
      await asyncio.sleep(3)
      if qr_msg_id:
        try:
          await bot.delete_message(chat_id=uid, message_id=qr_msg_id)
        except Exception:
          pass

      # അടുത്ത ഘട്ടത്തിലേക്ക് പോകുന്നു (Instagram Link വാങ്ങുന്നു)
      await OrderStates.wait_ig_link.set()
      await state.update_data(utr=utr_input)

      req_link_text = (
          "✅ **Payment Received & Verified!**\n\n"
          "🔗 **NOW, PLEASE SEND YOUR INSTAGRAM LINK:**\n"
          "───────────────\n"
          "• *Followers ആവശ്യമാണെങ്കിൽ*: Send Profile Link\n"
          "• *Likes ആവശ്യമാണെങ്കിൽ*: Send Post/Reel Link\n\n"
          "👇 *Paste your Instagram URL below:*"
      )
      await msg.answer(req_link_text, parse_mode="Markdown")

    else:
      try:
        await verifying_msg.delete()
      except Exception:
        pass

      await msg.answer(
          "❌ **Payment Verification Failed!**\n\n"
          "⚠️ Payment with this UTR was not found in our Gmail records.\n"
          "Please check the UTR number and try again.",
          parse_mode="Markdown",
      )

  except Exception as e:
    print(f"Error in process_utr_verification: {e}")


# --- STEP 2: Instagram Link Verification & Order Activation ---
@dp.message_handler(
    state=OrderStates.wait_ig_link, content_types=types.ContentTypes.TEXT
)
async def process_instagram_link(msg: types.Message, state: FSMContext):
  try:
    user_text = msg.text.strip()

    # Instagram Link ആണോ എന്ന് വാലിഡേറ്റ് ചെയ്യുന്നു
    ig_pattern = r"(https?://(?:www\.)?instagram\.com/[a-zA-Z0-9_\-\./\?=#]+|https?://instagr\.am/[a-zA-Z0-9_\-\./\?=#]+)"
    match = re.search(ig_pattern, user_text)

    if not match:
      await msg.answer(
          "❌ **Invalid Instagram Link!**\n\n"
          "⚠️ ദയവായി ശരിയായ ഒരു **Instagram Link** അയക്കുക.\n"
          "Example:\n`https://www.instagram.com/your_username`\n"
          "അല്ലെങ്കിൽ\n`https://www.instagram.com/p/Cxyz123/`",
          parse_mode="Markdown",
      )
      return

    verified_ig_url = match.group(0)

    # State Data ലഭിക്കുന്നു
    data = await state.get_data()
    s_type = data.get("service", "bot")
    qty = data.get("quantity", "N/A")
    price = data.get("price", "N/A")
    utr_num = data.get("utr", "N/A")

    uid = msg.from_user.id
    first_name = msg.from_user.first_name or "User"
    service_title = CUSTOM_LIMITS.get(s_type, {}).get(
        "name", s_type.capitalize()
    )

    # 1. കസ്റ്റമർക്ക് അയക്കുന്ന ORder Activated മെസ്സേജ്
    customer_order_msg = (
        "━━━━━━━━━━━━━━━━━━━━━━━\n"
        "🎉 **ORDER ACTIVATED SUCCESSFULLY!** 🎉\n"
        "━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"👤 **Customer:** {first_name}\n"
        f"🛍 **Service:** {service_title}\n"
        f"📦 **Quantity:** {qty}\n"
        f"💰 **Amount Paid:** ₹{price}\n"
        f"🔢 **Verified UTR:** `{utr_num}`\n"
        f"🔗 **Target Link:** [Click Here]({verified_ig_url})\n\n"
        "⚡ **Status:** Processing Fast! Your order will be completed"
        " shortly.\n"
        "━━━━━━━━━━━━━━━━━━━━━━━"
    )

    await msg.answer(
        customer_order_msg,
        reply_markup=get_main_menu(),
        parse_mode="Markdown",
        disable_web_page_preview=True,
    )

    # 2. അഡ്മിന് ലഭിക്കുന്ന Order Details മെസ്സേജ്
    admin_order_msg = (
        "━━━━━━━━━━━━━━━━━━━━━━━\n"
        "🚀 **NEW ORDER ACTIVATED**\n"
        "━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"👤 **Name:** {first_name}\n"
        f"🆔 **User ID:** `{uid}`\n"
        f"🛍 **Service:** {service_title}\n"
        f"📦 **Quantity:** {qty}\n"
        f"💰 **Paid:** ₹{price}\n"
        f"🔢 **UTR:** `{utr_num}`\n"
        f"🔗 **Link:** {verified_ig_url}\n"
        "━━━━━━━━━━━━━━━━━━━━━━━"
    )

    try:
      await bot.send_message(
          ADMIN_ID,
          admin_order_msg,
          parse_mode="Markdown",
          disable_web_page_preview=True,
      )
    except Exception:
      pass

    await state.finish()

  except Exception as e:
    print(f"Error in process_instagram_link: {e}")


# --- Support Mode Handlers ---
@dp.callback_query_handler(lambda c: c.data == "chat_admin", state="*")
async def start_support(cq: types.CallbackQuery, state: FSMContext):
  try:
    await cq.answer()
    await OrderStates.in_support.set()
    cancel_kb = InlineKeyboardMarkup(row_width=1).add(
        InlineKeyboardButton(
            "❌ Cancel Support", callback_data="cancel_support"
        )
    )
    await bot.send_message(
        cq.from_user.id,
        "💬 **Support Mode Activated**\n\n"
        "Send your message here. It will be forwarded to the admin.\n\n"
        "Click below to exit support mode.",
        reply_markup=cancel_kb,
        parse_mode="Markdown",
    )
  except Exception as e:
    print(f"Error in start_support: {e}")


@dp.callback_query_handler(
    lambda c: c.data == "cancel_support", state=OrderStates.in_support
)
async def cancel_support(cq: types.CallbackQuery, state: FSMContext):
  try:
    await cq.answer("Support closed.")
    await state.finish()
    await bot.send_message(
        cq.from_user.id,
        "You are back to the main menu:",
        reply_markup=get_main_menu(),
    )
  except Exception as e:
    print(f"Error in cancel_support: {e}")


# --- ADMIN COMMANDS ---
@dp.message_handler(commands=["broadcast"], state="*")
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
      await msg.reply(
          "⚠️ **Usage:**\n"
          "Reply to a message/photo with `/broadcast`\n"
          "OR type `/broadcast Your Message Here`",
          parse_mode="Markdown",
      )
      return

    for u_id in users:
      try:
        await bot.send_message(u_id, text, parse_mode="Markdown")
        count += 1
        await asyncio.sleep(0.05)
      except Exception:
        pass

  await msg.reply(
      f"📢 **Broadcast completed successfully!**\nSent to {count} user(s).",
      parse_mode="Markdown",
  )


@dp.message_handler(commands=["setprice"], state="*")
async def set_price_cmd(msg: types.Message):
  if msg.from_user.id != ADMIN_ID:
    return

  args = msg.get_args().split()
  if len(args) < 3:
    await msg.reply(
        "⚠️ **Usage:** `/setprice <category> <index> <new_price>`\n"
        "Example: `/setprice bot 0 40`",
        parse_mode="Markdown",
    )
    return

  cat, idx, new_price = args[0].lower(), int(args[1]), int(args[2])

  if cat in SERVICES_DATA and idx < len(SERVICES_DATA[cat]["plans"]):
    SERVICES_DATA[cat]["plans"][idx]["price"] = new_price
    save_services(SERVICES_DATA)
    await msg.reply(
        f"✅ **Price updated successfully!**\n"
        f"{cat.capitalize()} plan #{idx} price changed to ₹{new_price}.",
        parse_mode="Markdown",
    )
  else:
    await msg.reply(
        "❌ Invalid category or plan index.", parse_mode="Markdown"
    )


@dp.message_handler(commands=["settime"], state="*")
async def set_time_cmd(msg: types.Message):
  if msg.from_user.id != ADMIN_ID:
    return

  args = msg.get_args().split(maxsplit=1)
  if len(args) < 2:
    await msg.reply(
        "⚠️ **Usage:** `/settime <category> <new_time>`\n"
        "Example: `/settime bot 1 Hour and 30 Minutes`",
        parse_mode="Markdown",
    )
    return

  cat, new_time = args[0].lower(), args[1]

  if cat in SERVICES_DATA:
    SERVICES_DATA[cat]["delivery_time"] = new_time
    save_services(SERVICES_DATA)
    await msg.reply(
        f"✅ **Delivery time updated!**\n"
        f"{cat.capitalize()} delivery time set to: {new_time}",
        parse_mode="Markdown",
    )
  else:
    await msg.reply(
        "❌ Invalid category. Choose from: bot, real, likes",
        parse_mode="Markdown",
    )


# --- Global Message Handler ---
@dp.message_handler(content_types=types.ContentTypes.ANY)
async def global_message_handler(msg: types.Message):
  try:
    if msg.from_user.id == ADMIN_ID and msg.reply_to_message:
      try:
        replied_msg = msg.reply_to_message
        txt = replied_msg.text or replied_msg.caption or ""

        uid = None
        for line in txt.split("\n"):
          if "🆔" in line and "ID:" in line:
            clean_line = (
                line.replace("🆔", "")
                .replace("User ID:", "")
                .replace("ID:", "")
                .strip()
                .replace("`", "")
            )
            uid = int(clean_line)
            break

        if uid:
          if msg.text:
            await bot.send_message(uid, f"👨‍💻 **Admin Reply:**\n\n{msg.text}")
          elif msg.photo:
            await bot.send_photo(
                uid,
                msg.photo[-1].file_id,
                caption=f"👨‍💻 **Admin Reply:**\n\n{msg.caption or ''}",
            )

          await msg.reply("✅ Reply sent successfully!")
        else:
          await msg.reply(
              "❌ Could not find User ID from this message. Please reply to a"
              " valid notification box."
          )
      except Exception as e:
        await msg.reply(f"❌ Error sending reply: {e}")
      return
  except Exception as e:
    print(f"Global message handler error: {e}")


# --- Execution Loop ---
if __name__ == "__main__":
  keep_alive()
  while True:
    try:
      print("Bot is running smoothly...")
      executor.start_polling(
          dp,
          skip_updates=True,
          relax=0.01,
          timeout=20,
          allowed_updates=types.AllowedUpdates.all(),
      )
    except Exception as e:
      print(f"Crash prevented: {e}. Auto-restarting in 1 second...")
      import time

      time.sleep(1)

