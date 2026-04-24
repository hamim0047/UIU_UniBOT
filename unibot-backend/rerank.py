from sentence_transformers import CrossEncoder
from functools import lru_cache

@lru_cache(maxsize=1)
def get_cross_encoder():
    return CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")

def rerank_pairs(query: str, docs):
    pairs = [(query, d["text"]) for d in docs]
    model = get_cross_encoder()
    scores = model.predict(pairs)
    ranked = [{**d, "rerank_score": float(s)} for d, s in zip(docs, scores)]
    ranked.sort(key=lambda x: x["rerank_score"], reverse=True)
    return ranked

