import psycopg2
from datetime import datetime
import pytz
from rapidfuzz import fuzz
import os

# ================= PostgreSQL Config =================
DATABASE_URL = os.getenv("DATABASE_URL")

def get_conn():
    return psycopg2.connect(DATABASE_URL, sslmode="require")
    
# ================= Init DB =================
def init_db():
    with get_conn() as conn:
        with conn.cursor() as c:
            # table questions
            c.execute('''
            CREATE TABLE IF NOT EXISTS questions (
                id SERIAL PRIMARY KEY,
                question TEXT NOT NULL,
                chat_id BIGINT,
                sender_name TEXT,
                status TEXT DEFAULT 'pending',
                answer TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                cs_id TEXT,
                message_id BIGINT,
                closed_reason TEXT
            )
            ''')

            # table FAQ
            c.execute('''
            CREATE TABLE IF NOT EXISTS faq (
                id SERIAL PRIMARY KEY,
                question TEXT,
                answer TEXT
            )
            ''')

            # table CS list
            c.execute('''
            CREATE TABLE IF NOT EXISTS cs_list (
                id SERIAL PRIMARY KEY,
                name TEXT UNIQUE NOT NULL
            )
            ''')

            # Seed CS list
            c.execute("SELECT COUNT(*) FROM cs_list")
            if c.fetchone()[0] == 0:
                for cs in ["CS1", "CS2", "CS3"]:
                    c.execute("INSERT INTO cs_list (name) VALUES (%s) ON CONFLICT DO NOTHING", (cs,))

# ================= Question Functions =================
def add_question(question, chat_id, message_id, sender_name=None, status="pending"):
    jakarta = pytz.timezone("Asia/Jakarta")
    now = datetime.now(jakarta).strftime("%Y-%m-%d %H:%M:%S")
    with get_conn() as conn:
        with conn.cursor() as c:
            c.execute("""
                INSERT INTO questions 
                (question, chat_id, message_id, sender_name, status, timestamp)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (question, chat_id, message_id, sender_name, status, now))

def get_questions(status=None):
    with get_conn() as conn:
        with conn.cursor() as c:
            if status:
                c.execute("""
                    SELECT id, question, chat_id, sender_name, status, answer, timestamp, cs_id, message_id, closed_reason
                    FROM questions WHERE status=%s
                """, (status,))
            else:
                c.execute("""
                    SELECT id, question, chat_id, sender_name, status, answer, timestamp, cs_id, message_id, closed_reason
                    FROM questions
                """)
            return c.fetchall()

def update_answer(q_id, answer, cs_id, status="replied"):
    jakarta = pytz.timezone("Asia/Jakarta")
    now = datetime.now(jakarta).strftime("%Y-%m-%d %H:%M:%S")
    with get_conn() as conn:
        with conn.cursor() as c:
            c.execute("""
                UPDATE questions
                SET answer=%s, cs_id=%s, status=%s, timestamp=%s
                WHERE id=%s
            """, (answer, cs_id, status, now, q_id))

def close_question(q_id, reason=None):
    with get_conn() as conn:
        with conn.cursor() as c:
            c.execute("UPDATE questions SET status='closed', closed_reason=%s WHERE id=%s", (reason, q_id))

def mark_replied(q_id):
    with get_conn() as conn:
        with conn.cursor() as c:
            c.execute("UPDATE questions SET status='replied' WHERE id=%s", (q_id,))

# ================= FAQ Functions =================
def get_faq():
    with get_conn() as conn:
        with conn.cursor() as c:
            c.execute("SELECT id, question, answer FROM faq")
            return c.fetchall()

def add_faq(question, answer):
    with get_conn() as conn:
        with conn.cursor() as c:
            c.execute("INSERT INTO faq (question, answer) VALUES (%s, %s)", (question, answer))

def update_faq(faq_id, question, answer):
    with get_conn() as conn:
        with conn.cursor() as c:
            c.execute("UPDATE faq SET question=%s, answer=%s WHERE id=%s", (question, answer, faq_id))

def delete_faq(faq_id):
    with get_conn() as conn:
        with conn.cursor() as c:
            c.execute("DELETE FROM faq WHERE id=%s", (faq_id,))

def search_faq(user_text, threshold=80):
    faqs = get_faq()
    user_text_lower = user_text.lower()
    for q, a in [(f[1], f[2]) for f in faqs]:
        score = fuzz.partial_ratio(q.lower(), user_text_lower)
        if score >= threshold:
            return a
    return None

# ================= CS Functions =================
def get_cs_list():
    with get_conn() as conn:
        with conn.cursor() as c:
            c.execute("SELECT name FROM cs_list ORDER BY id")
            return [r[0] for r in c.fetchall()]

def add_cs(name):
    with get_conn() as conn:
        with conn.cursor() as c:
            c.execute("INSERT INTO cs_list (name) VALUES (%s) ON CONFLICT DO NOTHING", (name,))

def remove_cs(name):
    with get_conn() as conn:
        with conn.cursor() as c:
            c.execute("DELETE FROM cs_list WHERE name=%s", (name,))
