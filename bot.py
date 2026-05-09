import telebot
import random
import string
import time
import hashlib
import hmac
import base64
import struct
from telebot import types
from datetime import datetime
from flask import Flask
from threading import Thread

# ================= CONFIGURATION =================
TOKEN = "8783194900:AAH__MsqIgqwKn_-Pzg2NdxQsIJ1OjvAVY8"
ADMIN_ID = 8783194900 # আপনার আইডি
bot = telebot.TeleBot(TOKEN, parse_mode="HTML")
app = Flask('')

# গ্লোবাল সেটিংস ও ডাটাবেজ (সিমুলেটেড)
config = {
    "rates": {"FB": 0.030, "IG 2FA": 0.025, "IG Cookies": 0.034, "IG Old": 0.034},
    "status": {"FB": True, "IG 2FA": True, "IG Cookies": True, "IG Old": True},
    "ref_bonus": 0.0200,
    "sheets": {"source": "Not Set", "save": "Not Set"}
}

user_data = {} # ইউজার ব্যালেন্স ও রেফার ট্র্যাকিং
cooldowns = {} # ৩ মিনিটের সিকিউরিটি ব্লক

# ================= HELPERS =================

def generate_smart_pass():
    names = ["Tanjimz", "Saidurz", "Rifatxx", "Siyamzz"]
    selected_name = random.choice(names)
    day = datetime.now().strftime("%d")
    return f"{selected_name}{day}"

def get_totp_code(secret):
    try:
        clean_sec = ''.join(c for c in secret if c.isalnum()).upper()
        key = base64.b32decode(clean_sec + '=' * ((8 - len(clean_sec) % 8) % 8))
        counter = struct.pack('>Q', int(time.time() // 30))
        hmac_hash = hmac.new(key, counter, hashlib.sha1).digest()
        offset = hmac_hash[-1] & 0x0F
        code = (struct.unpack('>I', hmac_hash[offset:offset+4])[0] & 0x7FFFFFFF) % 1000000
        return f"{code:06d}"
    except: return "Invalid"

# ================= KEYBOARDS (Reply ✅) =================

def main_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add("📋 Tasks", "💰 Balance")
    markup.add("🏦 Withdraw", "🏆 Leaderboard")
    markup.add("👥 Refer", "📞 Support")
    return markup

def task_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    if config["status"]["FB"]: markup.add("📘 Facebook")
    if config["status"]["IG 2FA"]: markup.add("📸 IG 2FA")
    if config["status"]["IG Cookies"]: markup.add("🍪 IG Cookies")
    if config["status"]["IG Old"]: markup.add("📜 IG Old Cookies")
    markup.add("🔙 Back to Menu")
    return markup

# ================= USER HANDLERS =================

@bot.message_handler(commands=['start'])
def start(message):
    bot.send_message(message.chat.id, f"Welcome, <b>{message.from_user.first_name}</b>!", reply_markup=main_menu())

@bot.message_handler(func=lambda m: m.text == "📋 Tasks")
def tasks(message):
    bot.send_message(message.chat.id, "Select a task to start (30 mins limit):", reply_markup=task_menu())

@bot.message_handler(func=lambda m: m.text == "📸 IG 2FA")
def ig_2fa_logic(message):
    uid = message.from_user.id
    # সিকিউরিটি ব্লক চেক (৩ মিনিট)
    if uid in cooldowns and time.time() - cooldowns[uid] < 180:
        bot.send_message(message.chat.id, "⚠️ Security Block! Wait 3 minutes before next task.")
        return
    
    psw = generate_smart_pass()
    cooldowns[uid] = time.time() # ৩ মিনিটের টাইমার শুরু
    
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("🔐 Get 2FA OTP", callback_data="get_otp"))
    bot.send_message(message.chat.id, f"🔑 <b>Task Password:</b> <code>{psw}</code>\nSubmit your ID within 30 mins.", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "get_otp")
def otp_call(call):
    msg = bot.send_message(call.message.chat.id, "Send your <b>2FA Secret Key</b>:")
    bot.register_next_step_handler(msg, process_otp)

def process_otp(message):
    code = get_totp_code(message.text)
    bot.send_message(message.chat.id, f"✅ <b>OTP Code:</b> <code>{code}</code>\nNow submit your username.")

# ================= ADMIN PANEL (👑) =================

@bot.message_handler(commands=['admin'])
def admin_p(message):
    if message.from_user.id == ADMIN_ID:
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
        markup.add("🚫 Task Control", "✅ Approve Report")
        markup.add("❌ Reject Report", "⚙️ Settings")
        markup.add("📊 Daily Logs", "🔙 Back to Menu")
        bot.send_message(message.chat.id, "👑 <b>Admin Control Center</b>", reply_markup=markup)

@bot.message_handler(func=lambda m: m.text == "✅ Approve Report")
def approve_init(message):
    if message.from_user.id == ADMIN_ID:
        msg = bot.send_message(message.chat.id, "Paste successful Usernames (one per line):")
        bot.register_next_step_handler(msg, bulk_approve)

def bulk_approve(message):
    unames = message.text.split('\n')
    for u in unames:
        u = u.strip()
        if u:
            # ইউজারকে মেসেজ ও রেফার বোনাস লজিক
            bot.send_message(message.chat.id, f"✅ <b>Report approved, +$0.034</b>\n🆔 <b>Username:</b> <code>{u}</code>\n✉ <b>Ref Bonus:</b> ${config['ref_bonus']} sent to inviter.")
    bot.send_message(message.chat.id, "🏁 Approved All!")

@bot.message_handler(func=lambda m: m.text == "⚙️ Settings")
def settings_p(message):
    if message.from_user.id == ADMIN_ID:
        markup = types.InlineKeyboardMarkup(row_width=1)
        markup.add(
            types.InlineKeyboardButton("🔗 Edit Source Sheet", callback_data="set_source"),
            types.InlineKeyboardButton("📂 Edit Save Sheet", callback_data="set_save"),
            types.InlineKeyboardButton("💰 Edit Task Rates", callback_data="set_rates")
        )
        bot.send_message(message.chat.id, "⚙️ <b>Bot Configuration</b>", reply_markup=markup)

@bot.message_handler(func=lambda m: m.text == "🔙 Back to Menu")
def back(message):
    bot.send_message(message.chat.id, "Main Menu", reply_markup=main_menu())

# ================= WEB SERVER =================
@app.route('/')
def home(): return "Active"
def run(): app.run(host='0.0.0.0', port=8080)

if __name__ == "__main__":
    t = Thread(target=run)
    t.start()
    bot.infinity_polling()

