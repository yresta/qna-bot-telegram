import os
import re
import asyncio
import logging
import threading
import requests

from fastapi import FastAPI, Request
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters
from apscheduler.schedulers.background import BackgroundScheduler
from dotenv import load_dotenv

import db
from faq import get_auto_answer

logging.getLogger("telegram.ext").setLevel(logging.DEBUG)

load_dotenv()
TOKEN = os.getenv("TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")  # url publik dari Render / domainmu
WEBHOOK_PATH = f"/webhook/{TOKEN}"

# ===== Init DB =====
db.init_db()

# ===== Event loop =====
loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)

# ===== Bot Application =====
app_bot = Application.builder().token(TOKEN).build()

# ===== Handlers =====
async def start(update, context):
    await update.message.reply_text("Halo! Bot QnA siap digunakan.")

async def handle_question(update, context):
    question_text = update.message.text
    chat_id = update.message.chat.id
    message_id = update.message.message_id
    user = update.message.from_user
    full_name = f"{user.first_name or ''} {user.last_name or ''}".strip()

    # cek FAQ pakai model
    faq_answer, score = get_auto_answer(question_text)
    if faq_answer:
        await update.message.reply_text(faq_answer)
        return

    if re.search(r"\bPO\w{8,}\b", question_text, re.IGNORECASE):
        db.add_question(question_text, chat_id, message_id, sender_name=full_name)
        logging.info(f"Pertanyaan diteruskan ke CS: {question_text}")
    else:
        logging.info(f"Pertanyaan tidak diteruskan karena bukan PO: {question_text}")

app_bot.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_question))
app_bot.add_handler(CommandHandler("start", start))

# ===== Scheduler =====
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

# ===== FastAPI server =====
fastapi_app = FastAPI()

@fastapi_app.get("/")
async def index():
    return {"status": "Bot is running ✅"}

@fastapi_app.post(WEBHOOK_PATH)
async def webhook(req: Request):
    data = await req.json()
    update = Update.de_json(data, app_bot.bot)
    await app_bot.update_queue.put(update)
    return {"ok": True}

# ===== Jalankan bot =====
def run_bot():
    loop.run_until_complete(app_bot.initialize())
    loop.run_until_complete(app_bot.start())
    loop.run_forever()

if __name__ == "__main__":
    # start bot di thread terpisah
    threading.Thread(target=run_bot, daemon=True).start()

    # set webhook sekali jalan
    requests.get(f"https://api.telegram.org/bot{TOKEN}/setWebhook?url={WEBHOOK_URL}{WEBHOOK_PATH}")

    # jalankan FastAPI (Render butuh port binding)
    import uvicorn
    port = int(os.getenv("PORT", 10000))
    uvicorn.run(fastapi_app, host="0.0.0.0", port=port)
