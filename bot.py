from flask import Flask, request
import asyncio
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters
import logging
import db
import os
from dotenv import load_dotenv
import re
from apscheduler.schedulers.background import BackgroundScheduler
import threading

logging.getLogger("telegram.ext").setLevel(logging.DEBUG)

load_dotenv()
TOKEN = os.getenv("TOKEN")
WEBHOOK_PATH = f"/webhook/{TOKEN}"
WEBHOOK_URL = os.getenv("WEBHOOK_URL")  # url publik dari Render / domainmu
FAQ_API_URL = os.getenv("FAQ_API_URL")

db.init_db()

# ===== Buat loop baru biar stabil =====
loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)

# ===== Bot Application =====
app_bot = Application.builder().token(TOKEN).build()

# ----- Handlers -----
async def start(update, context):
    await update.message.reply_text("Halo! Bot QnA siap digunakan.")

async def handle_question(update, context):
    question_text = update.message.text
    chat_id = update.message.chat.id
    message_id = update.message.message_id
    user = update.message.from_user
    full_name = f"{user.first_name or ''} {user.last_name or ''}".strip()

    # ==== panggil Hugging Face API ====
    try:
        resp = requests.post(
            f"{FAQ_API_URL}/faq",
            json={"text": question_text},
            timeout=10
        )
        if resp.status_code == 200:
            data = resp.json()
            if data.get("score", 0) > 0.75:  # threshold
                await update.message.reply_text(data["faq_answer"])
                return
    except Exception as e:
        print("FAQ API error:", e)
        
    if re.search(r"\bPO\w{8,}\b", question_text, re.IGNORECASE):
        db.add_question(question_text, chat_id, message_id, sender_name=full_name)
        logging.info(f"Pertanyaan diteruskan ke CS: {question_text}")
    else:
        logging.info(f"Pertanyaan tidak diteruskan karena bukan PO: {question_text}")

app_bot.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_question))
app_bot.add_handler(CommandHandler("start", start))

# ===== Scheduler untuk auto-reply =====
def auto_reply_job():
    answered = db.get_questions(status="answered")
    for q in answered:
        try:
            asyncio.run_coroutine_threadsafe(
                app_bot.bot.send_message(
                    chat_id=q[2],
                    text=f"{q[5]}\n- {q[7]}",
                    reply_to_message_id=q[8]
                ),
                loop
            )
            db.mark_replied(q[0])
        except Exception as e:
            logging.error(f"Error sending reply for ID {q[0]}: {e}")

scheduler = BackgroundScheduler()
scheduler.add_job(auto_reply_job, "interval", seconds=10)
scheduler.start()

# ===== Flask server =====
flask_app = Flask(_name_)

@flask_app.route("/")
def index():
    return "Bot is running ✅"

@flask_app.route(WEBHOOK_PATH, methods=["POST"])
def webhook():
    update = Update.de_json(request.get_json(force=True), app_bot.bot)
    asyncio.run_coroutine_threadsafe(app_bot.update_queue.put(update), loop)
    return {"ok": True}

# ===== Jalankan bot & Flask bareng =====
def run_loop():
    loop.run_until_complete(app_bot.initialize())
    loop.run_until_complete(app_bot.start())
    loop.run_forever()

if __name__ == "__main__":
    # Start event loop di thread terpisah
    threading.Thread(target=run_loop, daemon=True).start()

    # Set webhook (sekali jalan)
    import requests
    requests.get(f"https://api.telegram.org/bot{TOKEN}/setWebhook?url={WEBHOOK_URL}{WEBHOOK_PATH}")

    # Jalankan Flask (Render akan pakai ini)
    flask_app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)))
