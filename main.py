import io
import os
import asyncio
import logging
from datetime import datetime
from threading import Thread
import qrcode
from flask import Flask

from aiogram import Bot, Dispatcher, executor, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from pymongo import MongoClient
from pymongo.errors import PyMongoError

# ==============================================================================
# LOGGING SETUP
# ==============================================================================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(name)s - %(message)s"
)

# ==============================================================================
# CONFIGURATION & MONGO DB SETUP
# ==============================================================================
BOT_TOKEN = os.environ.get("BOT_TOKEN", "").strip()
SUPPORT_USERNAME = "@Athulsudin"
ADMIN_ID = int(os.environ.get("ADMIN_ID", 123456789))

# UPI Payment Configuration
UPI_ID = "yourupiid@upi"  # Enter your UPI ID
PAYEE_NAME = "Free Fire Store"

# External Links
PAYMENT_PROOF_URL = "https://t.me/your_payment_proof_channel"
TUTORIAL_VIDEO_URL = "https://t.me/chatelitehackers"

# 🍃 MONGO DB CONNECTION WITH RECOVERY SETTINGS 🍃
MONGO_URI = os.environ.get(
    "MONGO_URI",
    "mongodb+srv://athulathulsudin6_db_user:nUNelkx7LST2IwG3@cluster0.bpgqz5v.mongodb.net/?appName=Cluster0"
)

try:
    mongo_client = MongoClient(
        MONGO_URI,
        serverSelectionTimeoutMS=5000,
        connectTimeoutMS=10000,
        socketTimeoutMS=10000,
        retryWrites=True
    )
    db = mongo_client["EliteHackersBotDB"]
    users_col = db["users"]
    orders_col = db["orders"]
    utrs_col = db["utrs"]
    settings_col = db["settings"]
    logging.info("Successfully connected to MongoDB Atlas!")
except Exception as e:
    logging.error(f"Failed to connect to MongoDB: {e}")

bot = Bot(token=BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)

# ==============================================================================
# FLASK KEEP-ALIVE SERVER (FOR 24/7 HOSTING)
# ==============================================================================
app = Flask('')

@app.route('/')
def home():
    return "Bot is alive and running 24/7 with MongoDB Database!"

def run_flask():
    port = int(os.environ.get('PORT', 8080))
    try:
        app.run(host='0.0.0.0', port=port)
    except Exception as e:
        logging.error(f"Flask server error: {e}")

def keep_alive():
    t = Thread(target=run_flask)
    t.daemon = True
    t.start()

# ==============================================================================
# FSM STATES
# ==============================================================================
class OrderStates(StatesGroup):
    waiting_for_utr_btn = State()    
    waiting_for_utr_input = State()  
    waiting_for_uid_input = State()  

class AdminStates(StatesGroup):
    waiting_for_key = State()        

class InstagramStates(StatesGroup):
    waiting_for_payment = State()
    waiting_for_link = State()
    waiting_for_custom = State()

# ==============================================================================
# DICTIONARIES & DEFAULT DATA
# ==============================================================================
PANEL_UPDATE_LINKS = {
    "prime_hook": "https://t.me/+NDj15jI_twE5NTdl",
    "hg_cheat": "https://t.me/+kfutvLSk8g8wMzZl",
    "drip_client_proxy": "https://t.me/+BUcKeIdDjP80ZWU1",
    "drip_client": "https://t.me/+h7Liqy0GIRYzOTY1",
    "silent_cheat": "https://t.me/+onh-I6YtcwsxMzE1",
    "bala_mod": "https://t.me/+fL_1HR-k6A84MTI1",
    "tm_panel": "https://t.me/+EsQhz5KJC6MwODI1",
    "br_mod_root": "https://t.me/+Rt56iLN5LpZjNzE1",
    "rapid_core": "https://t.me/+5_3PLx9dRTM5ODk1",
    "angry_mod": "https://t.me/+YTjLan1CWcE1ZDE1",
    "xyz": "https://t.me/+VsHY3UJhUHYyZTNl",
    "neo_strike": "https://t.me/+ucqEeTiTXl80Mjhl",
    "haxx_cker_pro": "https://t.me/+Q_x-yCA0p_UzMjY1",
    "xyt": "https://t.me/+ZJbIQbAgKzUwYWI1",
    "flourite": "https://t.me/+KrWqWydehUk5MDRl",
    "migul": "https://t.me/+QYmMKu_gegQyNDY1",
    "br_mod_pc": "https://t.me/+5v1tYHhAARMzNDZl",
    "internal_panel": "https://t.me/+5l4FgM2JTMo4ODE1",
}

PANEL_NAMES = {
    "prime_hook": "PRIME HOOK",
    "hg_cheat": "HG CHEAT",
    "drip_client_proxy": "DRIP CLIENT PROXY",
    "drip_client": "DRIP CLIENT",
    "silent_cheat": "SILENT CHEAT",
    "bala_mod": "BALA MOD",
    "tm_panel": "TM PANEL",
    "br_mod_root": "BR MOD ROOT",
    "rapid_core": "RAPID CORE",
    "angry_mod": "ANGRY MOD",
    "xyz": "XYZ PANEL",
    "neo_strike": "NEO STRIKE",
    "haxx_cker_pro": "HAXX-CKER PRO",
    "xyt": "XYT PANEL",
    "flourite": "FLOURITE",
    "migul": "MIGUL",
    "br_mod_pc": "BR MOD PC",
    "internal_panel": "INTERNAL PANEL",
}

DEFAULT_PRICES = {
    "3days": 140,
    "7days": 300,
    "30days": 900
}

INSTA_SERVICES = {
    "f1k": ("1,000 Instagram Followers", "120"),
    "f2k": ("2,000 Instagram Followers", "220"),
    "f5k": ("5,000 Instagram Followers", "500"),
    "f10k": ("10,000 Instagram Followers", "950"),
    "l1k": ("1,000 Instagram Likes", "40"),
    "l2k": ("2,000 Instagram Likes", "70"),
    "l5k": ("5,000 Instagram Likes", "150"),
}

# ==============================================================================
# GLOBAL ERROR CATCHER (PREVENTS CRASHES)
# ==============================================================================
@dp.errors_handler()
async def global_error_handler(update, exception):
    logging.error(f"Global Exception Safe Guarded: {exception}")
    return True

# ==============================================================================
# DATABASE HELPER FUNCTIONS
# ==============================================================================
def get_or_create_user(user_id: int):
    try:
        user = users_col.find_one({"user_id": user_id})
        if not user:
            user_data = {
                "user_id": user_id,
                "joined_date": datetime.now().strftime("%d %b %Y"),
                "total_orders": 0
            }
            users_col.insert_one(user_data)
            return user_data
        return user
    except PyMongoError as e:
        logging.error(f"DB Error in get_or_create_user: {e}")
        return {"user_id": user_id, "joined_date": "N/A", "total_orders": 0}

def add_user_order(user_id: int, item_name: str, duration: str, amount: str, status: str = "Pending", key: str = None):
    try:
        get_or_create_user(user_id)
        order_doc = {
            "user_id": user_id,
            "item": item_name,
            "duration": duration,
            "amount": amount,
            "status": status,
            "key": key,
            "timestamp": datetime.now()
        }
        orders_col.insert_one(order_doc)
    except PyMongoError as e:
        logging.error(f"DB Error in add_user_order: {e}")

def increment_user_orders(user_id: int):
    try:
        get_or_create_user(user_id)
        users_col.update_one({"user_id": user_id}, {"$inc": {"total_orders": 1}})
    except PyMongoError as e:
        logging.error(f"DB Error in increment_user_orders: {e}")

def is_utr_used(utr: str) -> bool:
    try:
        return utrs_col.find_one({"utr": utr}) is not None
    except PyMongoError as e:
        logging.error(f"DB Error in is_utr_used: {e}")
        return False

def save_utr(utr: str, user_id: int):
    try:
        utrs_col.insert_one({"utr": utr, "user_id": user_id, "timestamp": datetime.now()})
    except PyMongoError as e:
        logging.error(f"DB Error in save_utr: {e}")

def get_panel_setting(panel_key: str):
    try:
        doc = settings_col.find_one({"panel_key": panel_key})
        if not doc:
            doc = {
                "panel_key": panel_key,
                "maintenance": False,
                "stock": {"3days": True, "7days": True, "30days": True},
                "prices": DEFAULT_PRICES.copy()
            }
            settings_col.insert_one(doc)
        return doc
    except PyMongoError as e:
        logging.error(f"DB Error in get_panel_setting: {e}")
        return {
            "panel_key": panel_key,
            "maintenance": False,
            "stock": {"3days": True, "7days": True, "30days": True},
            "prices": DEFAULT_PRICES.copy()
        }

def set_panel_maintenance(panel_key: str, status: bool):
    try:
        get_panel_setting(panel_key)
        settings_col.update_one({"panel_key": panel_key}, {"$set": {"maintenance": status}})
    except PyMongoError as e:
        logging.error(f"DB Error in set_panel_maintenance: {e}")

def set_plan_stock(panel_key: str, plan_key: str, status: bool):
    try:
        get_panel_setting(panel_key)
        settings_col.update_one({"panel_key": panel_key}, {"$set": {f"stock.{plan_key}": status}})
    except PyMongoError as e:
        logging.error(f"DB Error in set_plan_stock: {e}")

def set_plan_price(panel_key: str, plan_key: str, new_price: int):
    try:
        get_panel_setting(panel_key)
        settings_col.update_one({"panel_key": panel_key}, {"$set": {f"prices.{plan_key}": new_price}})
    except PyMongoError as e:
        logging.error(f"DB Error in set_plan_price: {e}")

# ==============================================================================
# 1. COMMAND /START & MAIN MENU
# ==============================================================================
def get_welcome_text() -> str:
    return (
        "════════════════════════════\n"
        "🚀 **WELCOME TO ELITE HACKERS** 🌟\n"
        "════════════════════════════\n\n"
        "👋 Welcome to our official store bot.\n\n"
        "👇 Select an option from below:"
    )

def get_main_menu_keyboard():
    main_menu_kb = InlineKeyboardMarkup(row_width=2)
    main_menu_kb.row(
        InlineKeyboardButton("🛒 Shop Now", callback_data="show_shop_menu")
    )
    main_menu_kb.row(
        InlineKeyboardButton("🔑 My Orders", callback_data="show_my_orders"),
        InlineKeyboardButton("👤 Your Profile", callback_data="show_user_profile")
    )
    main_menu_kb.row(
        InlineKeyboardButton("📢 Pay Proof", url=PAYMENT_PROOF_URL),
        InlineKeyboardButton("💬 Support", url=f"https://t.me/{SUPPORT_USERNAME.replace('@', '')}")
    )
    main_menu_kb.row(
        InlineKeyboardButton("🎬 How to Use Bot", callback_data="show_how_to_use")
    )
    return main_menu_kb

@dp.message_handler(commands=['start'], state='*')
async def cmd_start(msg: types.Message, state: FSMContext):
    try:
        await state.finish()
        get_or_create_user(msg.from_user.id)
        await msg.answer(get_welcome_text(), reply_markup=get_main_menu_keyboard(), parse_mode="Markdown")
    except Exception as e:
        logging.error(f"Error in cmd_start: {e}")

@dp.callback_query_handler(lambda c: c.data == 'main_menu', state='*')
async def back_to_main_menu_handler(cq: types.CallbackQuery, state: FSMContext):
    try:
        await state.finish()
        try:
            await cq.answer()
        except Exception:
            pass
        
        get_or_create_user(cq.from_user.id)
        welcome_text = get_welcome_text()
        
        try:
            await cq.message.edit_text(welcome_text, reply_markup=get_main_menu_keyboard(), parse_mode="Markdown")
        except Exception:
            try:
                await cq.message.delete()
            except Exception:
                pass
            await cq.message.answer(welcome_text, reply_markup=get_main_menu_keyboard(), parse_mode="Markdown")
    except Exception as e:
        logging.error(f"Error in back_to_main_menu_handler: {e}")

# ==============================================================================
# 2. FEATURE: SHOP NOW SUB-MENU
# ==============================================================================
@dp.callback_query_handler(lambda c: c.data == 'show_shop_menu', state='*')
async def show_shop_menu_handler(cq: types.CallbackQuery, state: FSMContext):
    try:
        await state.finish()
        try:
            await cq.answer()
        except Exception:
            pass
            
        shop_kb = InlineKeyboardMarkup(row_width=1)
        shop_kb.add(
            InlineKeyboardButton("🎮 Free Fire Panel Services", callback_data="show_products"),
            InlineKeyboardButton("👍 Free Fire Like Services", callback_data="show_like_services"),
            InlineKeyboardButton("📸 Instagram Services", callback_data="show_insta_services"),
            InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")
        )
        
        shop_text = (
            "════════════════════════\n"
            "🛒 **STORE MENU**\n"
            "════════════════════════\n\n"
            "Please select a service category below:"
        )
        
        try:
            await cq.message.edit_text(shop_text, reply_markup=shop_kb, parse_mode="Markdown")
        except Exception:
            try:
                await cq.message.delete()
            except Exception:
                pass
            await cq.message.answer(shop_text, reply_markup=shop_kb, parse_mode="Markdown")
    except Exception as e:
        logging.error(f"Error in show_shop_menu_handler: {e}")

# ==============================================================================
# 3. FEATURE: YOUR PROFILE
# ==============================================================================
@dp.callback_query_handler(lambda c: c.data == 'show_user_profile', state='*')
async def show_user_profile_handler(cq: types.CallbackQuery, state: FSMContext):
    try:
        await state.finish()
        try:
            await cq.answer()
        except Exception:
            pass

        user_id = cq.from_user.id
        user_db = get_or_create_user(user_id)
        
        name = cq.from_user.full_name if cq.from_user.full_name else "User"
        username = f"@{cq.from_user.username}" if cq.from_user.username else "No Username"
        joined_date = user_db.get("joined_date", "N/A")
        total_orders = user_db.get("total_orders", 0)
        
        profile_text = (
            "═════════════════════════════\n"
            "👤 **YOUR PROFILE**\n"
            "═════════════════════════════\n\n"
            f"👨‍💼 **Name:** {name}\n"
            f"🔗 **Username:** {username}\n"
            f"🆔 **User ID:** `{user_id}`\n"
            f"📅 **Member Since:** {joined_date}\n"
            f"🪪 **Account Type:** Regular\n"
            f"🛒 **Total Orders:** {total_orders}\n\n"
            "═════════════════════════════"
        )
        
        prof_kb = InlineKeyboardMarkup(row_width=2)
        prof_kb.row(
            InlineKeyboardButton("🛒 Shop Now", callback_data="show_shop_menu"),
            InlineKeyboardButton("🔑 My Orders", callback_data="show_my_orders")
        )
        prof_kb.row(
            InlineKeyboardButton("↩️ Back to Menu", callback_data="main_menu")
        )
        
        try:
            await cq.message.edit_text(profile_text, reply_markup=prof_kb, parse_mode="Markdown")
        except Exception:
            try:
                await cq.message.delete()
            except Exception:
                pass
            await cq.message.answer(profile_text, reply_markup=prof_kb, parse_mode="Markdown")
    except Exception as e:
        logging.error(f"Error in show_user_profile_handler: {e}")

# ==============================================================================
# 4. FEATURE: MY ORDERS
# ==============================================================================
@dp.callback_query_handler(lambda c: c.data == 'show_my_orders', state='*')
async def show_my_orders_handler(cq: types.CallbackQuery, state: FSMContext):
    try:
        await state.finish()
        try:
            await cq.answer()
        except Exception:
            pass

        user_id = cq.from_user.id
        get_or_create_user(user_id)
        
        user_orders = list(orders_col.find({"user_id": user_id}).sort("timestamp", -1).limit(10))
        
        orders_text = "═════════════════════════════\n"
        orders_text += "🔑 **MY ORDERS (last 10)**\n"
        orders_text += "═════════════════════════════\n\n"
        
        if not user_orders:
            orders_text += "❌ You haven't made any purchases yet."
        else:
            for index, item in enumerate(user_orders, 1):
                orders_text += f"{index}. 🎮 {item.get('item', 'Service')}\n"
                orders_text += f"   ⏱️ {item.get('duration', 'N/A')} • 💰 {item.get('amount', 'N/A')}\n"
                if item.get('key'):
                    orders_text += f"   🔑 Key: `{item['key']}`\n"
                orders_text += f"   📊 Status: {item.get('status', 'Pending')}\n\n"
                
        orders_text += "═════════════════════════════"
        
        orders_kb = InlineKeyboardMarkup(row_width=1)
        orders_kb.add(
            InlineKeyboardButton("🛒 Shop Again", callback_data="show_shop_menu"),
            InlineKeyboardButton("↩️ Back to Menu", callback_data="main_menu")
        )
        
        try:
            await cq.message.edit_text(orders_text, reply_markup=orders_kb, parse_mode="Markdown")
        except Exception:
            try:
                await cq.message.delete()
            except Exception:
                pass
            await cq.message.answer(orders_text, reply_markup=orders_kb, parse_mode="Markdown")
    except Exception as e:
        logging.error(f"Error in show_my_orders_handler: {e}")

# ==============================================================================
# 5. FEATURE: HOW TO USE BOT
# ==============================================================================
@dp.callback_query_handler(lambda c: c.data == 'show_how_to_use', state='*')
async def show_how_to_use_handler(cq: types.CallbackQuery, state: FSMContext):
    try:
        await state.finish()
        try:
            await cq.answer()
        except Exception:
            pass

        tutorial_text = (
            "📖 **How to Buy — ELITE HACKERS BOT**\n\n"
            "🎮 **How to Buy Free Fire Services:**\n"
            "1️⃣ Tap 🛒 **Shop Now**\n"
            "2️⃣ Select Free Fire Panel or Like Services\n"
            "3️⃣ Pick your product & validity plan\n"
            "4️⃣ Scan UPI QR Code & pay exact amount\n"
            "5️⃣ Enter your UTR Number or payment proof\n"
            "6️⃣ Get your License Key instantly! 🚀\n\n"
            "─────────────────────────────\n\n"
            "📸 **How to Buy Instagram Services:**\n"
            "1️⃣ Tap 🛒 **Shop Now**\n"
            "2️⃣ Select Instagram Services\n"
            "3️⃣ Choose Followers or Likes package\n"
            "4️⃣ Submit your Instagram Username / Link\n"
            "5️⃣ Complete UPI Payment & send proof screenshot\n"
            "6️⃣ Order completed within minutes! ⚡\n\n"
            "⚠️ **Note:** Always send clear payment proof to admin for instant approval."
        )
        
        tut_kb = InlineKeyboardMarkup(row_width=1)
        tut_kb.add(
            InlineKeyboardButton("🎥 Watch Tutorial Video ↗️", url=TUTORIAL_VIDEO_URL),
            InlineKeyboardButton("⬅️ Back to Menu", callback_data="main_menu")
        )
        
        try:
            await cq.message.edit_text(tutorial_text, reply_markup=tut_kb, parse_mode="Markdown")
        except Exception:
            try:
                await cq.message.delete()
            except Exception:
                pass
            await cq.message.answer(tutorial_text, reply_markup=tut_kb, parse_mode="Markdown")
    except Exception as e:
        logging.error(f"Error in show_how_to_use_handler: {e}")

# ==============================================================================
# 6. FREE FIRE LIKE SERVICES
# ==============================================================================
@dp.callback_query_handler(lambda c: c.data == 'show_like_services', state='*')
async def show_like_services(cq: types.CallbackQuery, state: FSMContext):
    try:
        await state.finish()
        try:
            await cq.answer()
        except Exception:
            pass
        
        like_kb = InlineKeyboardMarkup(row_width=1)
        like_kb.add(
            InlineKeyboardButton("🟢 7 DAYS - 220+ Likes/day - ₹90.00", callback_data="buylike_7days_220likes_90"),
            InlineKeyboardButton("🔵 15 DAYS - 220+ Likes/day - ₹160.00", callback_data="buylike_15days_220likes_160"),
            InlineKeyboardButton("🟣 30 DAYS - 220+ Likes/day - ₹275.00", callback_data="buylike_30days_220likes_275"),
            InlineKeyboardButton("🟠 60 DAYS - 220+ Likes/day - ₹500.00", callback_data="buylike_60days_220likes_500"),
            InlineKeyboardButton("🔴 90 DAYS - 220+ Likes/day - ₹730.00", callback_data="buylike_90days_220likes_730"),
            InlineKeyboardButton("🔙 Back to Shop", callback_data="show_shop_menu")
        )
        
        like_text = (
            "════════════════════════\n"
            "👍 **FREE FIRE LIKE SERVICE** 👍\n"
            "════════════════════════\n\n"
            "🔥 **AUTO LIKE EVERY DAY PLAN** 🔥\n"
            "⭐ *Get 220+ Auto Likes Everyday!*\n\n"
            "Please select your desired plan below:"
        )
        
        try:
            await cq.message.edit_text(like_text, reply_markup=like_kb, parse_mode="Markdown")
        except Exception:
            try:
                await cq.message.delete()
            except Exception:
                pass
            await cq.message.answer(like_text, reply_markup=like_kb, parse_mode="Markdown")
    except Exception as e:
        logging.error(f"Error in show_like_services: {e}")

# ==============================================================================
# 7. FREE FIRE PANEL SERVICES
# ==============================================================================
@dp.callback_query_handler(lambda c: c.data in ['show_products', 'back_to_category'], state='*')
async def show_categories(cq: types.CallbackQuery, state: FSMContext):
    try:
        await state.finish()
        try:
            await cq.answer()
        except Exception:
            pass
            
        cat_kb = InlineKeyboardMarkup(row_width=1)
        cat_kb.add(
            InlineKeyboardButton("📱 Non-Root Panels", callback_data="cat_non_root"),
            InlineKeyboardButton("🔓 Root Panels", callback_data="cat_root"),
            InlineKeyboardButton("💻 PC Panels", callback_data="cat_pc"),
            InlineKeyboardButton("🔙 Back to Shop", callback_data="show_shop_menu")
        )
        try:
            await cq.message.edit_text("🔰 **SELECT CATEGORY**\n\nChoose a category from below:", reply_markup=cat_kb, parse_mode="Markdown")
        except Exception:
            try:
                await cq.message.delete()
            except Exception:
                pass
            await cq.message.answer("🔰 **SELECT CATEGORY**\n\nChoose a category from below:", reply_markup=cat_kb, parse_mode="Markdown")
    except Exception as e:
        logging.error(f"Error in show_categories: {e}")

@dp.callback_query_handler(lambda c: c.data and c.data.startswith('cat_'), state='*')
async def show_panels_by_category(cq: types.CallbackQuery, state: FSMContext):
    try:
        await state.finish()
        try:
            await cq.answer()
        except Exception:
            pass
            
        category = cq.data.replace("cat_", "")
        panels_kb = InlineKeyboardMarkup(row_width=1)
        
        if category == "non_root":
            non_root_keys = ["prime_hook", "hg_cheat", "drip_client_proxy", "drip_client", "silent_cheat", "bala_mod", "tm_panel", "rapid_core", "angry_mod", "xyz", "neo_strike", "haxx_cker_pro", "xyt", "flourite", "migul", "internal_panel"]
            for key in non_root_keys:
                panels_kb.add(InlineKeyboardButton(f"🔥 {PANEL_NAMES[key]}", callback_data=f"panel_{key}"))
        elif category == "root":
            panels_kb.add(InlineKeyboardButton(f"🔥 {PANEL_NAMES['br_mod_root']}", callback_data="panel_br_mod_root"))
        elif category == "pc":
            panels_kb.add(InlineKeyboardButton(f"🔥 {PANEL_NAMES['br_mod_pc']}", callback_data="panel_br_mod_pc"))
            
        panels_kb.add(InlineKeyboardButton("🔙 Back", callback_data="back_to_category"))
        await cq.message.edit_text("📱 **SELECT PANEL**\n\nChoose your desired panel from the list:", reply_markup=panels_kb, parse_mode="Markdown")
    except Exception as e:
        logging.error(f"Error in show_panels_by_category: {e}")

@dp.callback_query_handler(lambda c: c.data and c.data.startswith('panel_'), state='*')
async def show_panel_details(cq: types.CallbackQuery, state: FSMContext):
    try:
        await state.finish()
        try:
            await cq.answer()
        except Exception:
            pass
        
        panel_key = cq.data.replace("panel_", "") 
        panel_name = PANEL_NAMES.get(panel_key, panel_key.upper().replace("_", " "))
        update_file_url = PANEL_UPDATE_LINKS.get(panel_key, f"https://t.me/{SUPPORT_USERNAME.replace('@', '')}")
        
        setting = get_panel_setting(panel_key)
        
        if setting.get("maintenance", False):
            maint_kb = InlineKeyboardMarkup(row_width=1)
            maint_kb.add(
                InlineKeyboardButton("📢 🔄 Check Update", url=update_file_url),
                InlineKeyboardButton("🔙 Back", callback_data="back_to_category")
            )
            
            maint_text = (
                f"🛠️ **{panel_name}**\n\n"
                "**This product is currently under maintenance. Please check back later — sorry for the inconvenience!**"
            )
            
            try:
                await cq.message.edit_text(maint_text, reply_markup=maint_kb, parse_mode="Markdown")
            except Exception:
                try:
                    await cq.message.delete()
                except Exception:
                    pass
                await cq.message.answer(maint_text, reply_markup=maint_kb, parse_mode="Markdown")
            return

        prices = setting.get("prices", DEFAULT_PRICES)
        stock = setting.get("stock", {"3days": True, "7days": True, "30days": True})
        
        plan_kb = InlineKeyboardMarkup(row_width=1)
        
        if stock.get("3days", True):
            plan_kb.add(InlineKeyboardButton(f"🟢 3 Days - ₹{prices['3days']}.00", callback_data=f"buy_{panel_key}_3days_{prices['3days']}"))
        else:
            plan_kb.add(InlineKeyboardButton("3 Days — Sold Out", callback_data="sold_out_plan"))
            
        if stock.get("7days", True):
            plan_kb.add(InlineKeyboardButton(f"🔵 7 Days - ₹{prices['7days']}.00", callback_data=f"buy_{panel_key}_7days_{prices['7days']}"))
        else:
            plan_kb.add(InlineKeyboardButton("7 Days — Sold Out", callback_data="sold_out_plan"))
            
        if stock.get("30days", True):
            plan_kb.add(InlineKeyboardButton(f"🟣 30 Days - ₹{prices['30days']}.00", callback_data=f"buy_{panel_key}_30days_{prices['30days']}"))
        else:
            plan_kb.add(InlineKeyboardButton("30 Days — Sold Out", callback_data="sold_out_plan"))

        plan_kb.row(
            InlineKeyboardButton("📁 Update File", url=update_file_url),
            InlineKeyboardButton("🔙 Back", callback_data="back_to_category")
        )
        plan_kb.add(InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu"))
        
        panel_text = (
            "════════════════════════\n"
            "🔥 **FREE FIRE PANEL SERVICE** 🔥\n"
            "════════════════════════\n\n"
            f"👾 **Selected Panel:** {panel_name}\n"
            "👇 **Select your plan:**\n"
        )
        
        try:
            await cq.message.edit_text(panel_text, reply_markup=plan_kb, parse_mode="Markdown")
        except Exception:
            try:
                await cq.message.delete()
            except Exception:
                pass
            await cq.message.answer(panel_text, reply_markup=plan_kb, parse_mode="Markdown")
    except Exception as e:
        logging.error(f"Error in show_panel_details: {e}")

@dp.callback_query_handler(lambda c: c.data == 'sold_out_plan', state='*')
async def sold_out_alert(cq: types.CallbackQuery):
    try:
        await cq.answer("❌ Sorry, this plan is currently OUT OF STOCK!", show_alert=True)
    except Exception as e:
        logging.error(f"Error in sold_out_alert: {e}")

# ==============================================================================
# 8. ADMIN COMMANDS
# ==============================================================================
@dp.message_handler(commands=['maint_on'], state='*')
async def admin_maint_on(msg: types.Message):
    if msg.from_user.id != ADMIN_ID:
        return
    args = msg.get_args().strip().lower()
    if not args or args not in PANEL_NAMES:
        await msg.reply("⚠️ **Usage:** `/maint_on <panel_key>`\n\nExample: `/maint_on prime_hook`", parse_mode="Markdown")
        return
    set_panel_maintenance(args, True)
    await msg.reply(f"🛠️ **{PANEL_NAMES[args]}** is now set to **MAINTENANCE MODE**!", parse_mode="Markdown")

@dp.message_handler(commands=['maint_off'], state='*')
async def admin_maint_off(msg: types.Message):
    if msg.from_user.id != ADMIN_ID:
        return
    args = msg.get_args().strip().lower()
    if not args or args not in PANEL_NAMES:
        await msg.reply("⚠️ **Usage:** `/maint_off <panel_key>`\n\nExample: `/maint_off prime_hook`", parse_mode="Markdown")
        return
    set_panel_maintenance(args, False)
    await msg.reply(f"✅ **{PANEL_NAMES[args]}** is now **ONLINE & AVAILABLE**!", parse_mode="Markdown")

@dp.message_handler(commands=['stock_off'], state='*')
async def admin_stock_off(msg: types.Message):
    if msg.from_user.id != ADMIN_ID:
        return
    try:
        panel_key, plan_key = msg.get_args().strip().lower().split()
        if panel_key in PANEL_NAMES and plan_key in ["3days", "7days", "30days"]:
            set_plan_stock(panel_key, plan_key, False)
            await msg.reply(f"❌ **{PANEL_NAMES[panel_key]} ({plan_key})** is now marked as **SOLD OUT**!", parse_mode="Markdown")
            return
    except Exception:
        pass
    await msg.reply("⚠️ **Usage:** `/stock_off <panel_key> <plan_key>`\n\nExample: `/stock_off prime_hook 3days`", parse_mode="Markdown")

@dp.message_handler(commands=['stock_on'], state='*')
async def admin_stock_on(msg: types.Message):
    if msg.from_user.id != ADMIN_ID:
        return
    try:
        panel_key, plan_key = msg.get_args().strip().lower().split()
        if panel_key in PANEL_NAMES and plan_key in ["3days", "7days", "30days"]:
            set_plan_stock(panel_key, plan_key, True)
            await msg.reply(f"✅ **{PANEL_NAMES[panel_key]} ({plan_key})** is back **IN STOCK**!", parse_mode="Markdown")
            return
    except Exception:
        pass
    await msg.reply("⚠️ **Usage:** `/stock_on <panel_key> <plan_key>`\n\nExample: `/stock_on prime_hook 3days`", parse_mode="Markdown")

@dp.message_handler(commands=['setprice'], state='*')
async def admin_set_price(msg: types.Message):
    if msg.from_user.id != ADMIN_ID:
        return
    try:
        panel_key, plan_key, price_str = msg.get_args().strip().lower().split()
        price = int(price_str)
        if panel_key in PANEL_NAMES and plan_key in ["3days", "7days", "30days"]:
            set_plan_price(panel_key, plan_key, price)
            await msg.reply(f"💵 **Price Updated!**\n\nPanel: **{PANEL_NAMES[panel_key]}**\nPlan: **{plan_key}**\nNew Price: **₹{price}.00**", parse_mode="Markdown")
            return
    except Exception:
        pass
    await msg.reply("⚠️ **Usage:** `/setprice <panel_key> <plan_key> <price>`\n\nExample: `/setprice prime_hook 3days 150`", parse_mode="Markdown")

@dp.message_handler(commands=['maintenance'], state='*')
async def admin_list_status(msg: types.Message):
    if msg.from_user.id != ADMIN_ID:
        return
    status_text = "📋 **ADMIN PANEL KEYS & STATUS**\n\n"
    for key, name in PANEL_NAMES.items():
        st = get_panel_setting(key)
        m_str = "🛠️ MAINT" if st.get("maintenance") else "✅ ONLINE"
        status_text += f"• `{key}` : {name} ({m_str})\n"
    status_text += "\n💡 **Plans Keys:** `3days`, `7days`, `30days`"
    await msg.reply(status_text, parse_mode="Markdown")

# ==============================================================================
# 9. PAYMENT & UTR VERIFICATION FLOW
# ==============================================================================
@dp.callback_query_handler(lambda c: c.data and (c.data.startswith('buy_') or c.data.startswith('buylike_')), state='*')
async def process_payment_qr(cq: types.CallbackQuery, state: FSMContext):
    try:
        try:
            await cq.answer()
        except Exception:
            pass
        
        if cq.data.startswith('buylike_'):
            _, duration, desc, price = cq.data.split('_')
            product_name = f"AUTO LIKE SERVICE ({desc})"
            service_type = "like_service"
            duration_str = duration.upper()
            amount = f"₹{price}.00"
        else:
            _, panel_key, duration, price = cq.data.split('_')
            product_name = PANEL_NAMES.get(panel_key, panel_key.upper())
            service_type = "panel_service"
            duration_str = duration
            amount = f"₹{price}.00"
        
        await state.update_data(product_name=product_name, duration=duration_str, amount=amount, service_type=service_type)
        await OrderStates.waiting_for_utr_btn.set()
        
        upi_url = f"upi://pay?pa={UPI_ID}&pn={PAYEE_NAME}&am={price}&cu=INR"
        qr = qrcode.QRCode(version=1, box_size=10, border=4)
        qr.add_data(upi_url)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        
        img_byte_arr = io.BytesIO()
        img.save(img_byte_arr, format='PNG')
        img_byte_arr.seek(0)
        
        pay_kb = InlineKeyboardMarkup(row_width=1)
        pay_kb.add(
            InlineKeyboardButton("📥 Enter UTR Number", callback_data="click_enter_utr"),
            InlineKeyboardButton("❌ Cancel Order", callback_data="cancel_to_product_panel"),
            InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")
        )
        
        pay_text = (
            "════════════════════════\n"
            "💳 **PAYMENT DETAILS**\n"
            "════════════════════════\n\n"
            f"🛍️ **Product:** {product_name}\n"
            f"⏱️ **Duration:** {duration_str}\n"
            f"💰 **Amount:** {amount}\n\n"
            f"📍 **UPI ID:** `{UPI_ID}`\n\n"
            "👉 **Scan the QR Code above to complete payment.**\n"
            "👉 After payment, click the **📥 Enter UTR Number** button below."
        )
        
        try:
            await cq.message.delete()
        except Exception:
            pass
            
        msg = await bot.send_photo(
            chat_id=cq.message.chat.id,
            photo=img_byte_arr,
            caption=pay_text,
            reply_markup=pay_kb,
            parse_mode="Markdown"
        )
        
        await state.update_data(qr_message_id=msg.message_id)
        asyncio.create_task(start_qr_expiration_timer(cq.message.chat.id, msg.message_id, state, product_name, duration_str, amount))
    except Exception as e:
        logging.error(f"Error in process_payment_qr: {e}")

async def start_qr_expiration_timer(chat_id: int, message_id: int, state: FSMContext, item: str, dur: str, amt: str):
    try:
        await asyncio.sleep(600)  # 10 Minutes timeout
        
        current_state = await state.get_state()
        if current_state in [OrderStates.waiting_for_utr_btn.state, OrderStates.waiting_for_utr_input.state]:
            add_user_order(chat_id, item, dur, amt, status="Expired (Time Ended)")
            
            expired_kb = InlineKeyboardMarkup(row_width=1)
            expired_kb.add(
                InlineKeyboardButton("🔄 Try Again", callback_data="show_shop_menu"),
                InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")
            )

            expired_text = (
                "════════════════════════\n"
                "⚠️ **ORDER EXPIRED**\n"
                "════════════════════════\n\n"
                "Your order has expired due to no UTR submission within 10 minutes.\n\n"
                f"Contact Support:\n👉 **{SUPPORT_USERNAME}**"
            )

            try:
                await bot.edit_message_caption(
                    chat_id=chat_id, 
                    message_id=message_id,
                    caption=expired_text, 
                    reply_markup=expired_kb, 
                    parse_mode="Markdown"
                )
            except Exception:
                pass
    except Exception as e:
        logging.error(f"Error in start_qr_expiration_timer: {e}")

@dp.callback_query_handler(lambda c: c.data == 'click_enter_utr', state=OrderStates.waiting_for_utr_btn)
async def ask_for_utr_input(cq: types.CallbackQuery, state: FSMContext):
    try:
        try:
            await cq.answer()
        except Exception:
            pass
        await OrderStates.waiting_for_utr_input.set()
        
        cancel_kb = InlineKeyboardMarkup(row_width=1)
        cancel_kb.add(InlineKeyboardButton("❌ Cancel Order", callback_data="cancel_to_product_panel"))
        
        ask_text = (
            "✍️ **ENTER UTR NUMBER**\n\n"
            "Please enter the **12-digit UTR / Ref Number** from your UPI app statement below:"
        )
        await cq.message.reply(ask_text, reply_markup=cancel_kb, parse_mode="Markdown")
    except Exception as e:
        logging.error(f"Error in ask_for_utr_input: {e}")

@dp.message_handler(state=OrderStates.waiting_for_utr_input, content_types=types.ContentTypes.TEXT)
async def process_utr_submission(msg: types.Message, state: FSMContext):
    try:
        utr_code = msg.text.strip()
        
        if len(utr_code) == 12 and utr_code.isdigit():
            if is_utr_used(utr_code):
                invalid_msg = (
                    "⚠️ **DUPLICATE UTR!**\n\n"
                    "❌ This UTR number has already been used. Please submit a valid new UTR number."
                )
                await msg.answer(invalid_msg, parse_mode="Markdown")
                return

            save_utr(utr_code, msg.from_user.id)
            
            data = await state.get_data()
            product_name = data.get('product_name', 'FREE FIRE SERVICE')
            product_duration = data.get('duration', 'N/A')
            product_amount = data.get('amount', 'N/A')
            
            await state.update_data(submitted_utr=utr_code)
            
            user_wait_msg = (
                "════════════════════════\n"
                "🔄 **VERIFYING PAYMENT**\n"
                "════════════════════════\n\n"
                f"📌 **Submitted UTR:** `{utr_code}`\n"
                "⏳ **Status:** Pending Admin Verification\n\n"
                "Your payment is being verified by admin. Please wait a moment..."
            )
            await msg.answer(user_wait_msg, parse_mode="Markdown")
            
            user_mention = f"[{msg.from_user.first_name}](tg://user?id={msg.from_user.id})"
            username_str = f"@{msg.from_user.username}" if msg.from_user.username else "No Username"
            
            admin_markup = InlineKeyboardMarkup(row_width=2)
            admin_markup.add(
                InlineKeyboardButton("✅ Approve UTR", callback_data=f"approve_utr_{msg.from_user.id}"),
                InlineKeyboardButton("❌ Reject UTR", callback_data=f"reject_utr_{msg.from_user.id}")
            )
            
            admin_notify = (
                "━━━━━━━━━━━━━━━━━━\n"
                "🔔 **NEW PAYMENT UTR SUBMITTED**\n"
                "━━━━━━━━━━━━━━━━━━\n\n"
                f"👤 **User:** {user_mention}\n"
                f"🆔 **Username:** `{username_str}`\n"
                f"🛍️ **Product:** {product_name}\n"
                f"⏱️ **Duration:** {product_duration}\n"
                f"💰 **Amount:** {product_amount}\n"
                f"💳 **Submitted UTR:** `{utr_code}`\n\n"
                "━━━━━━━━━━━━━━━━━━"
            )
            
            try:
                await bot.send_message(ADMIN_ID, admin_notify, reply_markup=admin_markup, parse_mode="Markdown")
            except Exception as e:
                logging.error(f"Failed to notify admin: {e}")
            
        else:
            await msg.answer("❌ **INVALID UTR!** Please send a valid 12-digit UTR/Ref number.", parse_mode="Markdown")
    except Exception as e:
        logging.error(f"Error in process_utr_submission: {e}")

@dp.callback_query_handler(lambda c: c.data and c.data.startswith(('approve_utr_', 'reject_utr_')), state='*')
async def handle_admin_action(cq: types.CallbackQuery, state: FSMContext):
    try:
        if cq.from_user.id != ADMIN_ID:
            return
            
        try:
            await cq.answer()
        except Exception:
            pass
            
        action, _, user_id_str = cq.data.split('_')
        target_user_id = int(user_id_str)
        
        user_state = dp.current_state(chat=target_user_id, user=target_user_id)
        user_data = await user_state.get_data()
        service_type = user_data.get('service_type', 'panel_service')
        product_name = user_data.get('product_name', 'Service')
        duration = user_data.get('duration', 'N/A')
        amount = user_data.get('amount', 'N/A')
        
        if action == 'approve':
            increment_user_orders(target_user_id)
            
            if service_type == 'like_service':
                await user_state.set_state(OrderStates.waiting_for_uid_input)
                
                uid_request_msg = (
                    "════════════════════════\n"
                    "✅ **PAYMENT APPROVED!**\n"
                    "════════════════════════\n\n"
                    "🎯 **SEND YOUR FF GAME UID**\n\n"
                    "Please type and send your **Free Fire Game UID** below to start your Like Service:"
                )
                try:
                    await bot.send_message(target_user_id, uid_request_msg, parse_mode="Markdown")
                except Exception:
                    pass
                await cq.message.edit_text(f"✅ Approved UTR for User ID: `{target_user_id}`. Waiting for customer UID...", parse_mode="Markdown")

            else:
                await AdminStates.waiting_for_key.set()
                await state.update_data(target_user_id=target_user_id)
                await cq.message.reply(f"⌨️ **Enter Product Key for User ID `{target_user_id}`:**", parse_mode="Markdown")

        elif action == 'reject':
            add_user_order(target_user_id, product_name, duration, amount, status="Cancelled")
            
            reject_kb = InlineKeyboardMarkup(row_width=1)
            reject_kb.add(InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu"))
            
            reject_msg = (
                "❌ **PAYMENT REJECTED!**\n\n"
                "Your payment was rejected due to an invalid UTR number. Please try again with a valid UTR."
            )
            try:
                await bot.send_message(target_user_id, reject_msg, reply_markup=reject_kb, parse_mode="Markdown")
            except Exception:
                pass
            await cq.message.edit_text(f"❌ Rejected payment for User ID: `{target_user_id}`", parse_mode="Markdown")
    except Exception as e:
        logging.error(f"Error in handle_admin_action: {e}")

@dp.message_handler(state=OrderStates.waiting_for_uid_input, content_types=types.ContentTypes.TEXT)
async def process_game_uid_submission(msg: types.Message, state: FSMContext):
    try:
        game_uid = msg.text.strip()
        
        data = await state.get_data()
        product_name = data.get('product_name', 'AUTO LIKE SERVICE')
        duration = data.get('duration', 'N/A')
        amount = data.get('amount', 'N/A')
        utr_code = data.get('submitted_utr', 'N/A')
        
        await state.update_data(customer_game_uid=game_uid)
        
        ack_text = (
            "════════════════════════\n"
            "📥 **GAME UID RECEIVED!**\n"
            "════════════════════════\n\n"
            f"🎯 **Your UID:** `{game_uid}`\n"
            f"🛍️ **Service:** {product_name}\n"
            f"⏱️ **Duration:** {duration}\n\n"
            "⏳ **Status:** Processing your likes request...\n"
            "You will receive a notification as soon as likes are activated!"
        )
        await msg.answer(ack_text, parse_mode="Markdown")
        
        user_mention = f"[{msg.from_user.first_name}](tg://user?id={msg.from_user.id})"
        username_str = f"@{msg.from_user.username}" if msg.from_user.username else "No Username"
        
        admin_like_kb = InlineKeyboardMarkup(row_width=1)
        admin_like_kb.add(
            InlineKeyboardButton("✅ Confirm & Send Like Added", callback_data=f"confirm_likes_{msg.from_user.id}")
        )
        
        admin_alert_text = (
            "━━━━━━━━━━━━━━━━━━\n"
            "🟢 **VERIFIED PAID CUSTOMER - GAME UID**\n"
            "━━━━━━━━━━━━━━━━━━\n\n"
            f"👤 **Customer:** {user_mention}\n"
            f"🆔 **Username:** `{username_str}`\n"
            f"🎮 **Game UID:** `{game_uid}`\n"
            f"🛍️ **Plan:** {product_name}\n"
            f"⏱️ **Duration:** {duration}\n"
            f"💰 **Amount Paid:** {amount}\n"
            f"💳 **Verified UTR:** `{utr_code}`\n\n"
            "👇 Click the button below after adding likes:"
        )
        
        try:
            await bot.send_message(ADMIN_ID, admin_alert_text, reply_markup=admin_like_kb, parse_mode="Markdown")
        except Exception as e:
            logging.error(f"Failed to notify admin: {e}")
    except Exception as e:
        logging.error(f"Error in process_game_uid_submission: {e}")

@dp.callback_query_handler(lambda c: c.data and c.data.startswith('confirm_likes_'), state='*')
async def handle_likes_added_confirmation(cq: types.CallbackQuery, state: FSMContext):
    try:
        if cq.from_user.id != ADMIN_ID:
            return
            
        try:
            await cq.answer()
        except Exception:
            pass
            
        target_user_id = int(cq.data.replace("confirm_likes_", ""))
        
        user_state = dp.current_state(chat=target_user_id, user=target_user_id)
        user_data = await user_state.get_data()
        
        product_name = user_data.get('product_name', 'AUTO LIKE SERVICE')
        duration = user_data.get('duration', 'N/A')
        amount = user_data.get('amount', 'N/A')
        game_uid = user_data.get('customer_game_uid', 'N/A')
        
        add_user_order(target_user_id, product_name, duration, amount, status="✅ Active / Approved")

        customer_notify_msg = (
            "════════════════════════\n"
            "🎉 **LIKES ADDED SUCCESSFULLY!**\n"
            "════════════════════════\n\n"
            f"🎯 **Game UID:** `{game_uid}`\n"
            f"🛍️ **Service:** {product_name}\n"
            f"⏱️ **Duration:** {duration}\n"
            f"💰 **Price:** {amount}\n\n"
            "✅ Your daily auto-likes service is now active!\n\n"
            "━━━━━━━━━━━━━━━━━━\n"
            f"Thank you for purchasing with us! Support: {SUPPORT_USERNAME}"
        )

        try:
            await bot.send_message(target_user_id, customer_notify_msg, parse_mode="Markdown")
            await user_state.finish()
            await cq.message.edit_text(f"✅ **Likes Confirmation Sent to User ID:** `{target_user_id}`", parse_mode="Markdown")
        except Exception as e:
            await cq.message.reply(f"❌ Failed to send confirmation to user! Error: {e}", parse_mode="Markdown")
    except Exception as e:
        logging.error(f"Error in handle_likes_added_confirmation: {e}")

@dp.message_handler(state=AdminStates.waiting_for_key, content_types=types.ContentTypes.TEXT)
async def process_and_send_key(msg: types.Message, state: FSMContext):
    try:
        if msg.from_user.id != ADMIN_ID:
            return

        admin_data = await state.get_data()
        target_user_id = admin_data.get('target_user_id')
        product_key = msg.text.strip()
        
        user_state = dp.current_state(chat=target_user_id, user=target_user_id)
        user_data = await user_state.get_data()
        
        product_name = user_data.get('product_name', 'FREE FIRE PANEL')
        duration = user_data.get('duration', '3 Days')
        amount = user_data.get('amount', '₹140.00')
        qr_msg_id = user_data.get('qr_message_id')
        
        if qr_msg_id:
            try:
                await bot.delete_message(chat_id=target_user_id, message_id=qr_msg_id)
            except Exception:
                pass

        add_user_order(target_user_id, product_name, duration, amount, status="✅ Active / Approved", key=product_key)

        customer_key_msg = (
            "════════════════════════\n"
            "🎉 **YOUR ORDER IS COMPLETE!**\n"
            "════════════════════════\n\n"
            f"🛍️ **Item:** {product_name}\n"
            f"⏱️ **Duration:** {duration}\n\n"
            "🔑 **Your Product Key:**\n"
            f"`{product_key}`\n\n"
            "*(Tap the code above to copy!)*\n\n"
            "━━━━━━━━━━━━━━━━━━\n"
            f"Thank you for purchasing with us! Support: {SUPPORT_USERNAME}"
        )

        try:
            await bot.send_message(target_user_id, customer_key_msg, parse_mode="Markdown")
            await user_state.finish()
            await state.finish()

            admin_confirm_text = (
                "✅ **Product Key Delivered Successfully!**\n\n"
                f"👤 **User ID:** `{target_user_id}`\n"
                f"🔑 **Sent Key:** `{product_key}`"
            )
            await msg.reply(admin_confirm_text, parse_mode="Markdown")

        except Exception as e:
            await msg.reply(f"❌ **Failed to deliver key!** Error: {e}", parse_mode="Markdown")
    except Exception as e:
        logging.error(f"Error in process_and_send_key: {e}")

# ==============================================================================
# 10. INSTAGRAM SERVICES
# ==============================================================================
@dp.callback_query_handler(lambda c: c.data == 'show_insta_services', state='*')
async def show_insta_services(cq: types.CallbackQuery, state: FSMContext):
    try:
        await state.finish()
        try:
            await cq.answer()
        except Exception:
            pass
        
        kb = InlineKeyboardMarkup(row_width=1)
        kb.add(
            InlineKeyboardButton("👥 1,000 Followers - ₹120", callback_data="insta_f1k"),
            InlineKeyboardButton("👥 2,000 Followers - ₹220", callback_data="insta_f2k"),
            InlineKeyboardButton("👥 5,000 Followers - ₹500", callback_data="insta_f5k"),
            InlineKeyboardButton("👥 10,000 Followers - ₹950", callback_data="insta_f10k"),
            InlineKeyboardButton("❤️ 1,000 Likes - ₹40", callback_data="insta_l1k"),
            InlineKeyboardButton("❤️ 2,000 Likes - ₹70", callback_data="insta_l2k"),
            InlineKeyboardButton("❤️ 5,000 Likes - ₹150", callback_data="insta_l5k"),
            InlineKeyboardButton("⚙️ Custom Quantity / Bulk Order", callback_data="insta_custom"),
            InlineKeyboardButton("🔙 Back to Shop", callback_data="show_shop_menu")
        )
        
        insta_text = (
            "════════════════════════\n"
            "📸 **INSTAGRAM SERVICES** 📸\n"
            "════════════════════════\n\n"
            "⚡ Instant Delivery & Non-Drop Guaranteed!\n"
            "Please select a service from below:"
        )
        try:
            await cq.message.edit_text(insta_text, reply_markup=kb, parse_mode="Markdown")
        except Exception:
            try:
                await cq.message.delete()
            except Exception:
                pass
            await cq.message.answer(insta_text, reply_markup=kb, parse_mode="Markdown")
    except Exception as e:
        logging.error(f"Error in show_insta_services: {e}")

@dp.callback_query_handler(lambda c: c.data and c.data.startswith('insta_'), state='*')
async def handle_insta_selection(cq: types.CallbackQuery, state: FSMContext):
    try:
        try:
            await cq.answer()
        except Exception:
            pass
        service_key = cq.data.replace("insta_", "")
        
        if service_key == "custom":
            await InstagramStates.waiting_for_custom.set()
            await cq.message.edit_text(
                "✍️ **CUSTOM / BULK ORDER**\n\n"
                "Please type the quantity or details you need (e.g., '15k Followers' or '50k Likes'):",
                parse_mode="Markdown"
            )
            return

        item_name, price = INSTA_SERVICES[service_key]
        await state.update_data(insta_item=item_name, insta_price=f"₹{price}.00")
        await InstagramStates.waiting_for_payment.set()

        kb = InlineKeyboardMarkup(row_width=1)
        kb.add(InlineKeyboardButton("❌ Cancel", callback_data="main_menu"))

        pay_text = (
            "════════════════════════\n"
            "💳 **INSTAGRAM PAYMENT**\n"
            "════════════════════════\n\n"
            f"🛍️ **Service:** {item_name}\n"
            f"💰 **Amount:** ₹{price}.00\n\n"
            f"📍 **UPI ID:** `{UPI_ID}`\n\n"
            "👉 Complete payment using the UPI ID above.\n"
            "👉 **Send the Payment Screenshot here** to proceed."
        )
        await cq.message.edit_text(pay_text, reply_markup=kb, parse_mode="Markdown")
    except Exception as e:
        logging.error(f"Error in handle_insta_selection: {e}")

@dp.message_handler(state=InstagramStates.waiting_for_custom, content_types=types.ContentTypes.TEXT)
async def process_insta_custom_input(msg: types.Message, state: FSMContext):
    try:
        custom_details = msg.text.strip()
        await state.update_data(insta_item=f"Custom Request: {custom_details}", insta_price="Custom Pricing")
        await InstagramStates.waiting_for_payment.set()
        
        kb = InlineKeyboardMarkup(row_width=1)
        kb.add(InlineKeyboardButton("❌ Cancel", callback_data="main_menu"))

        pay_text = (
            "════════════════════════\n"
            "💳 **CUSTOM PAYMENT**\n"
            "════════════════════════\n\n"
            f"🛍️ **Request:** {custom_details}\n\n"
            f"📍 **UPI ID:** `{UPI_ID}`\n\n"
            "👉 Pay the agreed amount to the UPI ID above.\n"
            "👉 **Send the Payment Screenshot here** to proceed."
        )
        await msg.answer(pay_text, reply_markup=kb, parse_mode="Markdown")
    except Exception as e:
        logging.error(f"Error in process_insta_custom_input: {e}")

@dp.message_handler(state=InstagramStates.waiting_for_payment, content_types=types.ContentTypes.PHOTO)
async def process_insta_payment_photo(msg: types.Message, state: FSMContext):
    try:
        photo_id = msg.photo[-1].file_id
        await state.update_data(payment_photo=photo_id)
        await InstagramStates.waiting_for_link.set()

        await msg.answer(
            "✅ **Screenshot Received!**\n\n"
            "🔗 Now, please send your **Instagram Profile or Post Link** below:",
            parse_mode="Markdown"
        )
    except Exception as e:
        logging.error(f"Error in process_insta_payment_photo: {e}")

@dp.message_handler(state=InstagramStates.waiting_for_payment, content_types=types.ContentTypes.ANY)
async def invalid_insta_payment_input(msg: types.Message):
    try:
        await msg.answer("⚠️ Please upload a **photo / screenshot** of your payment receipt.")
    except Exception as e:
        logging.error(f"Error in invalid_insta_payment_input: {e}")

@dp.message_handler(state=InstagramStates.waiting_for_link, content_types=types.ContentTypes.TEXT)
async def process_insta_link_submission(msg: types.Message, state: FSMContext):
    try:
        link = msg.text.strip()
        data = await state.get_data()
        
        item_name = data.get('insta_item', 'Instagram Service')
        price = data.get('insta_price', 'N/A')
        photo_id = data.get('payment_photo')

        user_mention = f"[{msg.from_user.first_name}](tg://user?id={msg.from_user.id})"
        username_str = f"@{msg.from_user.username}" if msg.from_user.username else "No Username"

        admin_kb = InlineKeyboardMarkup(row_width=2)
        admin_kb.add(
            InlineKeyboardButton("✅ Approve & Complete", callback_data=f"instappr_{msg.from_user.id}"),
            InlineKeyboardButton("❌ Reject Order", callback_data=f"instarej_{msg.from_user.id}")
        )

        admin_text = (
            "━━━━━━━━━━━━━━━━━━\n"
            "📸 **NEW INSTAGRAM ORDER**\n"
            "━━━━━━━━━━━━━━━━━━\n\n"
            f"👤 **Customer:** {user_mention}\n"
            f"🆔 **Username:** `{username_str}`\n"
            f"🛍️ **Service:** {item_name}\n"
            f"💰 **Amount:** {price}\n"
            f"🔗 **Target Link:** `{link}`\n\n"
            "━━━━━━━━━━━━━━━━━━"
        )

        try:
            await bot.send_photo(ADMIN_ID, photo_id, caption=admin_text, reply_markup=admin_kb, parse_mode="Markdown")
        except Exception as e:
            logging.error(f"Failed to send photo to admin: {e}")

        await msg.answer(
            "════════════════════════\n"
            "🎉 **ORDER SUBMITTED!**\n"
            "════════════════════════\n\n"
            f"🛍️ **Service:** {item_name}\n"
            f"🔗 **Target Link:** `{link}`\n\n"
            "⏳ **Status:** Processing by Admin. You will get a notification soon!",
            parse_mode="Markdown"
        )
    except Exception as e:
        logging.error(f"Error in process_insta_link_submission: {e}")

@dp.callback_query_handler(lambda c: c.data and c.data.startswith(('instappr_', 'instarej_')), state='*')
async def handle_insta_admin_approval(cq: types.CallbackQuery, state: FSMContext):
    try:
        if cq.from_user.id != ADMIN_ID:
            return

        try:
            await cq.answer()
        except Exception:
            pass
        action, user_id_str = cq.data.split('_')
        target_user_id = int(user_id_str)

        user_state = dp.current_state(chat=target_user_id, user=target_user_id)
        user_data = await user_state.get_data()
        
        item_name = user_data.get('insta_item', 'Instagram Service')
        price = user_data.get('insta_price', 'N/A')

        if action == "instappr":
            increment_user_orders(target_user_id)
            add_user_order(target_user_id, item_name, "Instant", price, status="✅ Completed")
            
            notify_text = (
                "════════════════════════\n"
                "✅ **INSTAGRAM SERVICE COMPLETED!**\n"
                "════════════════════════\n\n"
                "Your Instagram order has been processed and successfully delivered!\n\n"
                f"Thank you for choosing us! Support: {SUPPORT_USERNAME}"
            )
            try:
                await bot.send_message(target_user_id, notify_text, parse_mode="Markdown")
                await cq.message.edit_caption(caption=cq.message.caption + "\n\n✅ **Approved & Delivered!**")
            except Exception as e:
                await cq.message.reply(f"❌ Error sending confirmation to user: {e}")

        elif action == "instarej":
            add_user_order(target_user_id, item_name, "Instant", price, status="Cancelled")
            
            notify_text = (
                "❌ **INSTAGRAM ORDER REJECTED!**\n\n"
                "Your order was rejected by Admin. Please contact Support for assistance."
            )
            try:
                await bot.send_message(target_user_id, notify_text, parse_mode="Markdown")
                await cq.message.edit_caption(caption=cq.message.caption + "\n\n❌ **Rejected!**")
            except Exception as e:
                await cq.message.reply(f"❌ Error sending rejection to user: {e}")

        await user_state.finish()
    except Exception as e:
        logging.error(f"Error in handle_insta_admin_approval: {e}")

# ==============================================================================
# 11. CANCEL HANDLER
# ==============================================================================
@dp.callback_query_handler(lambda c: c.data == 'cancel_to_product_panel', state='*')
async def cancel_to_panel_handler(cq: types.CallbackQuery, state: FSMContext):
    try:
        await state.finish()
        try:
            await cq.answer("Order Cancelled")
        except Exception:
            pass
        await back_to_main_menu_handler(cq, state)
    except Exception as e:
        logging.error(f"Error in cancel_to_panel_handler: {e}")

# ==============================================================================
# MAIN EXECUTION WITH AUTO-RESTART LOOP
# ==============================================================================
if __name__ == '__main__':
    keep_alive()  # Starts background Flask server for Render/Koyeb hosting
    
    while True:
        try:
            logging.info("Starting Telegram Bot Polling with Dynamic MongoDB Settings...")
            executor.start_polling(dp, skip_updates=True)
        except Exception as e:
            logging.error(f"Bot crashed with error: {e}. Auto-restarting in 2 seconds...")
            asyncio.run(asyncio.sleep(2))
