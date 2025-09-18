from sentence_transformers import SentenceTransformer, util
import db

model = SentenceTransformer("all-MiniLM-L6-v2")

def build_embeddings():
    faqs = db.get_faq()
    if not faqs:
        return [], None, None

    questions = [row[1] for row in faqs]
    embeddings = model.encode(questions, convert_to_tensor=True)
    return faqs, questions, embeddings

def get_auto_answer(question_text: str, threshold: float = 0.75):
    faqs, _, faq_embeddings = build_embeddings()
    if not faqs:
        return None, 0.0

    q_embedding = model.encode(question_text, convert_to_tensor=True)
    cosine_scores = util.cos_sim(q_embedding, faq_embeddings)[0]

    best_idx = int(cosine_scores.argmax())
    best_score = float(cosine_scores[best_idx])

    if best_score >= threshold:
        return faqs[best_idx][2], best_score  # return jawaban
    return None, best_score

