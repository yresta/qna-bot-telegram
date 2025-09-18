from sentence_transformers import SentenceTransformer, util
import db

# ==== Init model & embeddings global ====
model = SentenceTransformer("paraphrase-MiniLM-L3-v2")  # lebih ringan dari L6
faq_embeddings = None
faqs = None

def init_embeddings():
    """Load FAQ dari DB dan encode sekali saat startup."""
    global faqs, faq_embeddings
    faqs = db.get_faq()
    if not faqs:
        faq_embeddings = None
        return

    questions = [row[1] for row in faqs]
    # encode batch kecil untuk hemat RAM
    faq_embeddings = model.encode(questions, convert_to_tensor=True, batch_size=16)

def get_auto_answer(question_text: str, threshold: float = 0.75):
    """Cari jawaban paling relevan dari FAQ."""
    if not faqs or faq_embeddings is None:
        return None, 0.0

    # Encode pertanyaan user saja
    q_embedding = model.encode(question_text, convert_to_tensor=True)
    cosine_scores = util.cos_sim(q_embedding, faq_embeddings)[0]

    best_idx = int(cosine_scores.argmax())
    best_score = float(cosine_scores[best_idx])

    if best_score >= threshold:
        return faqs[best_idx][2], best_score  # return jawaban
    return None, best_score

# ==== Panggil ini sekali di startup bot ====
init_embeddings()
