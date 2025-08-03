import os
import telebot
import requests
from flask import Flask
import threading

# Берём токен из переменной окружения BOT_TOKEN
TOKEN = os.getenv("BOT_TOKEN")
bot = telebot.TeleBot(TOKEN)

app = Flask(__name__)

# Эндпоинт для Uptimer.dev
@app.route('/')
def home():
    return "I'm alive!", 200

# Команда /start
@bot.message_handler(commands=['start'])
def start(message):
    bot.send_message(
        message.chat.id,
        '''🎉 Добро пожаловать в TikTok Saver!

✨ С помощью этого бота вы можете скачивать TikTok‑видео без водяного знака прямо сюда в чат.

📥 Как пользоваться:
1️⃣ Скопируйте ссылку на любое TikTok‑видео
2️⃣ Отправьте её в этот чат
3️⃣ Получите своё видео в чистом виде'''
    )

# Обработка всех сообщений (TikTok-ссылки)
@bot.message_handler(func=lambda m: True)
def download_tiktok(message):
    url = message.text.strip()

    if "tiktok.com" not in url:
        bot.send_message(message.chat.id, '''⚠ Некорректная ссылка TikTok

Чтобы скачать видео, пришлите ссылку в формате:
🔗 https://vm.tiktok.com/XXXXXXX/

💡 Совет: скопируйте ссылку через кнопку «Поделиться» → «Копировать ссылку» в приложении TikTok.''')
        return

    try:
        api_url = f"https://www.tikwm.com/api/?url={url}"
        response = requests.get(api_url).json()

        if response.get("data") and response["data"].get("play"):
            video_url = response["data"]["play"]
            bot.send_video(message.chat.id, video_url, caption="⚡️ Скачано через:\n@downloader52bot")
        else:
            bot.send_message(message.chat.id, "⚠️ Не удалось получить видео. Попробуй другую ссылку.")
    except Exception as e:
        bot.send_message(message.chat.id, f"⚠️ Ошибка: {e}")

# Функция для запуска бота
def start_bot():
    bot.polling(none_stop=True)

if __name__ == "__main__":
    threading.Thread(target=start_bot).start()
    app.run(host="0.0.0.0", port=10000)
