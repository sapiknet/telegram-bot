import os
import telebot
import requests
import sqlite3
from flask import Flask, request
from telebot import types

TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_USERNAME = "@swkccl"  # Канал для обязательной подписки
bot = telebot.TeleBot(TOKEN)

app = Flask(__name__)

# -------------------- БАЗА ДАННЫХ --------------------

DB_FILE = "users.db"

# Создаем таблицу пользователей, если её нет
conn = sqlite3.connect(DB_FILE, check_same_thread=False)
cursor = conn.cursor()
cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY
)
""")
conn.commit()

def save_user(user_id):
    cursor.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (user_id,))
    conn.commit()

def get_user_count():
    cursor.execute("SELECT COUNT(*) FROM users")
    return cursor.fetchone()[0]

# -------------------- ПРОВЕРКА ПОДПИСКИ --------------------

def is_subscribed(user_id):
    try:
        member = bot.get_chat_member(CHANNEL_USERNAME, user_id)
        status = member.status
        return status in ["member", "administrator", "creator"]
    except Exception:
        return False

# -------------------- FLASK --------------------

@app.route('/')
def home():
    return "I'm alive!", 200

@app.route(f'/{TOKEN}', methods=['POST'])
def webhook():
    json_str = request.get_data().decode('UTF-8')
    update = telebot.types.Update.de_json(json_str)
    bot.process_new_updates([update])
    return '', 200

# -------------------- ОБРАБОТКА КОМАНД --------------------

@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.chat.id

    if not is_subscribed(user_id):
        keyboard = types.InlineKeyboardMarkup()
        keyboard.add(
            types.InlineKeyboardButton("🔗 Подписаться на канал", url=f"https://t.me/{CHANNEL_USERNAME[1:]}"),
            types.InlineKeyboardButton("✅ Проверить подписку", callback_data="check_subscribe")
        )
        bot.send_message(
            user_id,
            f"👋 Привет! Чтобы пользоваться ботом, подпишись на наш канал {CHANNEL_USERNAME}.\n"
            "После подписки нажми «✅ Проверить подписку».",
            reply_markup=keyboard
        )
        return

    # Если подписан
    save_user(user_id)

    bot.send_message(
        user_id,
        '''🎉 Добро пожаловать в TikTok Saver!

✨ Отправь мне ссылку на TikTok — я скачаю видео или фото без водяного знака.
''',
        reply_markup=keyboard
    )

# Проверка подписки
@bot.callback_query_handler(func=lambda call: call.data == "check_subscribe")
def check_subscribe(call):
    user_id = call.message.chat.id
    if is_subscribed(user_id):
        save_user(user_id)
        bot.send_message(
            user_id,
            "✅ Отлично! Подписка подтверждена.\nМожешь отправлять ссылки на TikTok.",
            reply_markup=keyboard
        )
    else:
        bot.answer_callback_query(call.id, "❌ Вы ещё не подписаны!")

# Кнопка "Статистика"
@bot.message_handler(func=lambda m: m.text == "📊 Статистика")
def stats(message):
    bot.send_message(message.chat.id, f"👥 Всего пользователей бота: {get_user_count()}")

# -------------------- ОБРАБОТКА ССЫЛОК --------------------

@bot.message_handler(func=lambda m: True)
def download_tiktok(message):
    user_id = message.chat.id

    # Проверяем подписку
    if not is_subscribed(user_id):
        bot.send_message(user_id, "❌ Сначала подпишись на канал, чтобы пользоваться ботом.")
        return

    save_user(user_id)
    url = message.text.strip()

    if "tiktok.com" not in url:
        bot.send_message(
            user_id,
            '''⚠ Некорректная ссылка TikTok

Пришли ссылку в формате:
🔗 https://vm.tiktok.com/XXXXXXX/
'''
        )
        return

    try:
        api_url = f"https://www.tikwm.com/api/?url={url}"
        response = requests.get(api_url, timeout=10).json()
        data = response.get("data", {})

        # 1️⃣ Видео
        if data.get("play"):
            bot.send_video(
                user_id,
                data["play"],
                caption="⚡️ Скачано через:\n@downloader52bot"
            )

        # 2️⃣ Фото-пост
        elif data.get("images"):
            media_group = [
                telebot.types.InputMediaPhoto(img)
                for img in data["images"]
            ]
            bot.send_media_group(user_id, media_group)

        else:
            bot.send_message(user_id, "⚠️ Не удалось получить медиа.")

    except Exception as e:
        bot.send_message(user_id, f"⚠️ Ошибка: {e}")

# -------------------- ЗАПУСК --------------------

if __name__ == "__main__":
    WEBHOOK_URL = f"https://{os.getenv('RENDER_EXTERNAL_HOSTNAME')}/{TOKEN}"
    bot.remove_webhook()
    bot.set_webhook(url=WEBHOOK_URL)

    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
