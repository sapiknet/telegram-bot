import os
import telebot
import requests
from flask import Flask, request

TOKEN = os.getenv("BOT_TOKEN")
bot = telebot.TeleBot(TOKEN)

app = Flask(__name__)

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
@bot.message_handler(func=lambda m: True)
def download_tiktok(message):
    url = message.text.strip()

    if "tiktok.com" not in url:
        bot.send_message(message.chat.id, '''⚠ ННекорректная ссылка TikTok

Чтобы скачать видео, пришлите ссылку в формате:
🔗 https://vm.tiktok.com/XXXXXXX/

💡 Совет: скопируйте ссылку через кнопку «Поделиться» → «Копировать ссылку» в приложении TikTok.''')
        return

    try:
        api_url = f"https://www.tikwm.com/api/?url={url}"
        response = requests.get(api_url).json()

        data = response.get("data", {})

        # 1️⃣ Видео
        if data.get("play"):
            bot.send_video(message.chat.id, data["play"], caption="⚡️ Скачано через:\n@downloader52bot")

        # 2️⃣ Фото-пост (Photo Mode)
        elif data.get("images"):
            media = [telebot.types.InputMediaPhoto(img) for img in data["images"]]
            bot.send_media_group(message.chat.id, media)

        else:
            bot.send_message(message.chat.id, "⚠️ Не удалось получить видео или фото. Попробуй другую ссылку.")

    except Exception as e:
        bot.send_message(message.chat.id, f"⚠️ Ошибка: {e}")

if __name__ == "__main__":
    # Устанавливаем Webhook
    WEBHOOK_URL = f"https://{os.getenv('RENDER_EXTERNAL_HOSTNAME')}/{TOKEN}"
    bot.remove_webhook()
    bot.set_webhook(url=WEBHOOK_URL)
    app.run(host="0.0.0.0", port=10000)
