import asyncio
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from apscheduler.schedulers.background import BackgroundScheduler
import db
from dotenv import load_dotenv
import os
import logging
import re 

logging.getLogger("telegram.ext").setLevel(logging.DEBUG)

load_dotenv()
TOKEN = os.getenv("TOKEN")

db.init_db()

# ===== Bot Handlers =====
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Halo! Bot QnA siap digunakan.")

async def handle_question(update: Update, context: ContextTypes.DEFAULT_TYPE):
    question_text = update.message.text
    chat_id = update.message.chat.id
    message_id = update.message.message_id
    user = update.message.from_user
    first_name = user.first_name or ""
    last_name = user.last_name or ""
    full_name = f"{first_name} {last_name}".strip()

    # cek FAQ
    faq_answer = db.search_faq(question_text)
    if faq_answer:
        await update.message.reply_text(faq_answer)
        return  # sangat penting: hentikan eksekusi di sini

    # hanya teruskan jika ada kode PO
    if re.search(r"\bPO\w{8,}\b", question_text, re.IGNORECASE):
        db.add_question(question_text, chat_id, message_id, sender_name=full_name)
        logging.info(f"Pertanyaan diteruskan ke CS: {question_text}")
    else:
        logging.info(f"Pertanyaan tidak diteruskan karena bukan PO: {question_text}")

# ===== Scheduler Job =====
def auto_reply_job(app, loop):
    try:
        answered = db.get_questions(status="answered")
        for q in answered:
            try:
                asyncio.run_coroutine_threadsafe(
                    app.bot.send_message(
                        chat_id=q[2],            
                        text=f"{q[5]}\n- {q[7]}",
                        reply_to_message_id=q[8] 
                    ),
                    loop
                )
                db.mark_replied(q[0])  # ubah status jadi replied
                logging.info(f"Jawaban dikirim untuk ID {q[0]} ke chat {q[2]}")
            except Exception as e:
                logging.error(f"Error sending reply for ID {q[0]}: {e}")
    except Exception as e:
        logging.error(f"Error in auto_reply_job: {e}")

# ===== Main =====
def main():
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_question))

    loop = asyncio.get_event_loop()

    scheduler = BackgroundScheduler()
    scheduler.add_job(lambda: auto_reply_job(app, loop), 'interval', seconds=10)
    scheduler.start()
    logging.info("Scheduler started.")

    logging.info("Bot polling started.")
    app.run_polling()

if __name__ == "__main__":
    main()
