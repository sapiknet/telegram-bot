import os
import telebot
import requests
from flask import Flask, request
from telebot import types

TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_USERNAME = "@swkccl"  # Канал для обязательной подписки
bot = telebot.TeleBot(TOKEN)

app = Flask(__name__)

USERS_FILE = "users.txt"

# Загружаем пользователей при запуске
if os.path.exists(USERS_FILE):
    with open(USERS_FILE, "r") as f:
        users = set(f.read().splitlines())
else:
    users = set()

def save_user(user_id):
    if str(user_id) not in users:
        users.add(str(user_id))
        with open(USERS_FILE, "a") as f:
            f.write(f"{user_id}\n")

def is_subscribed(user_id):
    try:
        member = bot.get_chat_member(CHANNEL_USERNAME, user_id)
        status = member.status
        print(f"[DEBUG] Пользователь {user_id} статус в канале: {status}")
        return status in ["member", "administrator", "creator"]
    except Exception as e:
        print(f"[DEBUG] Ошибка проверки подписки: {e}")
        return False

@app.route('/')
def home():
    return "I'm alive!", 200

@app.route(f'/{TOKEN}', methods=['POST'])
def webhook():
    json_str = request.get_data().decode('UTF-8')
    update = telebot.types.Update.de_json(json_str)
    bot.process_new_updates([update])
    return '', 200

# Команда /start
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
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add(types.KeyboardButton("📊 Статистика"))

    bot.send_message(
        user_id,
        '''🎉 Добро пожаловать в TikTok Saver!

✨ Отправь мне ссылку ТикТок, а я тебе этот видос! 
''',
        reply_markup=keyboard
    )

# Проверка подписки после нажатия кнопки
@bot.callback_query_handler(func=lambda call: call.data == "check_subscribe")
def check_subscribe(call):
    user_id = call.message.chat.id
    if is_subscribed(user_id):
        save_user(user_id)
        keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
        keyboard.add(types.KeyboardButton("📊 Статистика"))
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
    bot.send_message(message.chat.id, f"👥 Всего пользователей бота: {len(users)}")

# Обработка ссылок TikTok
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

Чтобы я отправил тебе это, пришли ссылку в формате:
🔗 https://vm.tiktok.com/XXXXXXX/

💡 Совет: скопируй ссылку через кнопку «Поделиться» → «Копировать ссылку» в приложении TikTok.'''
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
            return

        # 2️⃣ Фото-пост (Photo Mode)
        if data.get("images"):
            media_group = []
            for idx, img in enumerate(data["images"]):
                media_group.append(
                    telebot.types.InputMediaPhoto(media=img, caption="📸 Фото с TikTok" if idx == 0 else "")
                )
            bot.send_media_group(user_id, media_group)
            return

        # 3️⃣ Только звук (например, удалённое видео)
        if data.get("music"):
            bot.send_audio(
                user_id,
                data["music"],
                caption="🎵 Только звук, видео недоступно"
            )
            return

        bot.send_message(user_id, "⚠️ Не удалось получить медиа. Попробуй другую ссылку.")

    except Exception as e:
        bot.send_message(user_id, f"⚠️ Ошибка: {e}")

if __name__ == "__main__":
    WEBHOOK_URL = f"https://{os.getenv('RENDER_EXTERNAL_HOSTNAME')}/{TOKEN}"
    bot.remove_webhook()
    bot.set_webhook(url=WEBHOOK_URL)

port = int(os.environ.get("PORT", 5000))
app.run(host="0.0.0.0", port=port)
