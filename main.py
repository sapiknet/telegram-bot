import os
import telebot
import requests
from flask import Flask, request
from telebot import types

TOKEN = os.getenv("BOT_TOKEN")
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
    """Добавляем пользователя и сохраняем в файл"""
    if str(user_id) not in users:
        users.add(str(user_id))
        with open(USERS_FILE, "a") as f:
            f.write(f"{user_id}\n")

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
    save_user(message.chat.id)

    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add(types.KeyboardButton("📊 Статистика"))

    bot.send_message(
        message.chat.id,
        '''🎉 Добро пожаловать в TikTok Saver!

✨ Отправь мне ссылку ТикТок, а я тебе этот видос! 
''',
        reply_markup=keyboard
    )

# Обработка кнопки "Статистика"
@bot.message_handler(func=lambda m: m.text == "📊 Статистика")
def stats(message):
    bot.send_message(message.chat.id, f"👥 Всего пользователей бота: {len(users)}")

# Обработка ссылок TikTok
@bot.message_handler(func=lambda m: True)
def download_tiktok(message):
    save_user(message.chat.id)
    url = message.text.strip()

    if "tiktok.com" not in url:
        bot.send_message(
            message.chat.id,
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
                message.chat.id,
                data["play"],
                caption="⚡️ Скачано через:\n@downloader52bot"
            )

        # 2️⃣ Фото-пост (Photo Mode)
        elif data.get("images"):
            media_group = [
                telebot.types.InputMediaPhoto(img)
                for img in data["images"]
            ]
            bot.send_media_group(message.chat.id, media_group)

        # 3️⃣ Только звук (например, удалённое видео)
        elif data.get("music"):
            bot.send_audio(
                message.chat.id,
                data["music"],
                caption="🎵 Только звук, видео недоступно"
            )

        else:
            bot.send_message(message.chat.id, "⚠️ Не удалось получить медиа.")

    except Exception as e:
        bot.send_message(message.chat.id, f"⚠️ Ошибка: {e}")

if __name__ == "__main__":
    # Устанавливаем Webhook для Render
    WEBHOOK_URL = f"https://{os.getenv('RENDER_EXTERNAL_HOSTNAME')}/{TOKEN}"
    bot.remove_webhook()
    bot.set_webhook(url=WEBHOOK_URL)
    app.run(host="0.0.0.0", port=10000)
