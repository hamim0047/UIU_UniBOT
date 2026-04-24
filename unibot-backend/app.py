# app.py — RAG with token-capped context + freshness-aware retrieval + Qwen(ChatML) support

import os, re, datetime
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Optional
import chromadb
from sentence_transformers import SentenceTransformer
from rank_bm25 import BM25Okapi
from rerank import rerank_pairs
from llama_cpp import Llama

load_dotenv()

# Optional: avoid tokenizers' fork warning noise on macOS
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")

# ---------------- Embeddings ----------------
EMBED_MODEL = os.getenv("EMBED_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
encoder = SentenceTransformer(EMBED_MODEL)

# ---------------- Llama (one init) ----------------
LLAMA_CTX = int(os.getenv("LLAMA_CTX", 4096))        # good for 3B models
GEN_TOKENS = int(os.getenv("GEN_TOKENS", 384))       # how many tokens to generate
SAFETY_MARGIN = int(os.getenv("SAFETY_MARGIN", 64))  # safety cushion

model_path = os.getenv("LLAMA_MODEL_PATH", "").strip()
if not model_path or not os.path.exists(model_path):
    raise RuntimeError(
        f"LLAMA_MODEL_PATH is missing or file not found:\n{model_path}\n\n"
        "Set it to your GGUF, e.g.:\n"
        "export LLAMA_MODEL_PATH=$PWD/models/qwen2.5-3b-instruct-q4_k_m.gguf"
    )

# --- Chat template handling (Qwen needs ChatML) ---
CHAT_FORMAT = os.getenv("CHAT_FORMAT", "").strip().lower()
fname = os.path.basename(model_path).lower()
if not CHAT_FORMAT:
    if "qwen" in fname or "chatml" in fname:
        CHAT_FORMAT = "chatml"
    elif "llama-3" in fname or "llama3" in fname:
        CHAT_FORMAT = "llama-3"
    else:
        CHAT_FORMAT = "llama-2"  # safe default for many llama-style instruct models

llm = Llama(
    model_path=model_path,
    n_ctx=LLAMA_CTX,
    n_threads=os.cpu_count() or 4,
    n_gpu_layers=int(os.getenv("N_GPU_LAYERS", 0)),
    logits_all=False,
    chat_format=CHAT_FORMAT,
)

# ---------------- Vector store ----------------
client = chromadb.PersistentClient(path="./chroma_db")
col = client.get_or_create_collection(name="uni_rag")

results = col.get(include=["documents", "metadatas"])
DOCS = results.get("documents", []) or []
METAS = results.get("metadatas", []) or []
IDS = results.get("ids", []) or []
BM25 = BM25Okapi([d.split() for d in DOCS]) if DOCS else None

# ---------------- FastAPI ----------------
app = FastAPI(title="University RAG (Llama local)")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:5173", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class Ask(BaseModel):
    query: str
    k: int = 20
    top_n: int = 6

def embed(texts: List[str]):
    return encoder.encode(texts, normalize_embeddings=True)

def dense_search(query: str, k: int):
    qv = embed([query])[0]
    res = col.query(
        query_embeddings=[qv.tolist()],
        n_results=k,
        include=["documents", "metadatas"],
    )
    ids = (res.get("ids") or [[]])[0]
    docs = (res.get("documents") or [[]])[0]
    metas = (res.get("metadatas") or [[]])[0] if res.get("metadatas") else []
    hits = []
    for i in range(len(ids)):
        meta = metas[i] if metas and i < len(metas) else {}
        text = docs[i] if i < len(docs) else ""
        hits.append({"id": ids[i], "text": text, "meta": meta, "score": 0.0})
    return hits

def bm25_search(query: str, k: int):
    if not BM25:
        return []
    scores = BM25.get_scores(query.split())
    ranked = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:k]
    return [
        {"id": IDS[i], "text": DOCS[i], "meta": METAS[i] if i < len(METAS) else {}, "bm25": float(scores[i])}
        for i in ranked
    ]

def hybrid_search(query: str, k: int = 20):
    dense = dense_search(query, k)
    sparse = bm25_search(query, k)
    merged = {d["id"]: d for d in dense}
    for s in sparse:
        if s["id"] in merged:
            merged[s["id"]]["bm25"] = s.get("bm25", 0.0)
        else:
            merged[s["id"]] = s
    return list(merged.values())

# ---------------- Freshness helpers ----------------
# Tweak freshness behavior via env without code edits
ALPHA = float(os.getenv("FRESH_ALPHA", "0.7"))               # semantic weight
BETA = float(os.getenv("FRESH_BETA", "0.3"))                 # recency weight
HALF_LIFE_DAYS = int(os.getenv("FRESH_HALF_LIFE_DAYS", "270"))

DATE_PATTERNS = [
    re.compile(r"/(20\d{2})(?:[/-](\d{1,2}))?(?:[/-](\d{1,2}))?"),     # /2025/10/15 or /2025/10 or /2025
    re.compile(r"(20\d{2})[._-](\d{1,2})[._-](\d{1,2})"),              # 2025-10-15 or 2025_10_15
    re.compile(r"(\d{1,2})[._/-](\d{1,2})[._/-](20\d{2})"),            # 15-10-2025
]

def _safe_int(x: Optional[str]) -> Optional[int]:
    try:
        return int(x) if x is not None else None
    except Exception:
        return None

def parse_date_from_url(url: str) -> Optional[datetime.date]:
    u = url or ""
    for pat in DATE_PATTERNS:
        m = pat.search(u)
        if not m:
            continue
        g = m.groups()
        if len(g) == 3:
            if len(g[0]) == 4:
                y, mth, d = _safe_int(g[0]), _safe_int(g[1]), _safe_int(g[2])
            else:
                d, mth, y = _safe_int(g[0]), _safe_int(g[1]), _safe_int(g[2])
            try:
                if y and mth and d:
                    return datetime.date(y, mth, d)
                if y and mth:
                    return datetime.date(y, mth, 1)
                if y:
                    return datetime.date(y, 1, 1)
            except Exception:
                continue
        elif len(g) == 1 and len(g[0]) == 4:
            y = _safe_int(g[0])
            if y:
                return datetime.date(y, 1, 1)
    return None

def parse_date_from_meta(meta: Dict) -> Optional[datetime.date]:
    for key in ("published_at", "lastmod", "date", "updated_at"):
        val = meta.get(key)
        if not val:
            continue
        try:
            dt = datetime.datetime.fromisoformat(str(val).replace("Z", "+00:00"))
            return dt.date()
        except Exception:
            pass
        m = re.search(r"(20\d{2})-(\d{1,2})-(\d{1,2})", str(val))
        if m:
            y, mth, d = map(int, m.groups())
            try:
                return datetime.date(y, mth, d)
            except Exception:
                continue
    return None

TODAY = datetime.date.today()

def freshness_score(meta: Dict) -> float:
    url = meta.get("source_url") or ""
    d = parse_date_from_meta(meta) or parse_date_from_url(url)
    if not d:
        return 0.5  # unknown age: neutral baseline
    age_days = max(0, (TODAY - d).days)
    # Smooth decay; newer docs closer to 1.0
    return 0.5 + 0.5 * (2 ** (-age_days / HALF_LIFE_DAYS))

def combine_scores(items: List[Dict], alpha: float = ALPHA, beta: float = BETA) -> List[Dict]:
    # collect semantic scores
    sems = []
    for it in items:
        s = it.get("rerank_score")
        if s is None:
            s = it.get("bm25", 0.0)
        sems.append(float(s))

    # normalize semantic to 0..1
    if sems:
        lo, hi = min(sems), max(sems)
        span = hi - lo if hi > lo else 1.0
    else:
        lo, span = 0.0, 1.0

    combined = []
    for it, s in zip(items, sems):
        sem_norm = (s - lo) / span
        fresh = freshness_score(it.get("meta", {}))
        it["freshness"] = fresh
        it["sem_norm"] = sem_norm
        it["final_score"] = alpha * sem_norm + beta * fresh
        combined.append(it)

    combined.sort(key=lambda x: x.get("final_score", 0.0), reverse=True)
    return combined

SYSTEM_PROMPT = (
    "You are a university assistant. Use ONLY the provided context. "
    "Prefer the most recent information when there are conflicts. "
    "Explicitly include dates (semester/year/effective date) and fees when available. "
    "If the answer is missing, say you don’t know and suggest the relevant office. "
    "Cite sources."
)

# ---------- helper: token budgeting ----------
def count_tokens(text: str) -> int:
    return len(llm.tokenize(text.encode("utf-8"), add_bos=False))

def trim_to_tokens(text: str, max_tokens: int) -> str:
    if max_tokens <= 0 or not text:
        return ""
    toks = llm.tokenize(text.encode("utf-8"), add_bos=False)
    if len(toks) <= max_tokens:
        return text
    toks = toks[:max_tokens]
    return llm.detokenize(toks).decode("utf-8", errors="ignore")

def build_context(query: str, ctx_blocks: List[Dict]) -> str:
    # Reserve room for system+user wrappers and the model's generation
    budget = max(256, LLAMA_CTX - GEN_TOKENS - SAFETY_MARGIN)
    wrapper_overhead = count_tokens(SYSTEM_PROMPT) + count_tokens("Question: " + query) + 32
    remain = max(128, budget - wrapper_overhead)

    per_chunk_cap = 512  # avoid one giant doc blowing the budget
    assembled = []
    used = 0

    for i, c in enumerate(ctx_blocks, 1):
        raw = c.get("text", "") or ""
        src = c.get("meta", {}).get("source_url", "") or ""
        if not raw:
            continue

        # Surface date in the block header if we have one
        d = parse_date_from_meta(c.get("meta", {})) or parse_date_from_url(src)
        date_tag = f" (date: {d.isoformat()})" if d else ""

        cap = min(per_chunk_cap, max(0, remain - used))
        if cap <= 0:
            break

        chunk_text = trim_to_tokens(raw, cap)
        if not chunk_text:
            continue

        block = f"[{i}]{date_tag} {chunk_text}\nsource: {src}".strip()
        t = count_tokens(block)
        if used + t > remain:
            break
        assembled.append(block)
        used += t + 4  # small separator cost

    return "\n\n".join(assembled)

def generate_answer(query: str, ctx_blocks: List[Dict]):
    context_str = build_context(query, ctx_blocks)
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": (
            f"Question: {query}\n\nContext:\n{context_str}\n\n"
            "Instructions: Prefer the newest information if numbers conflict. "
            "Quote dates (semester/year/effective date) and cite sources."
        )},
    ]
    out = llm.create_chat_completion(
        messages=messages,
        temperature=0.2,
        top_p=0.9,
        max_tokens=GEN_TOKENS,
        repeat_penalty=1.1,
    )
    return out["choices"][0]["message"]["content"].strip()

@app.get("/health")
def health():
    return {
        "ok": True,
        "model": os.path.basename(model_path),
        "ctx": LLAMA_CTX,
        "chat_format": CHAT_FORMAT,
    }

@app.post("/ask")
def ask(body: Ask):
    # keep pools modest to avoid huge context
    k = max(4, min(body.k, 12))
    top_n = max(2, min(body.top_n, 5))

    pool = hybrid_search(body.query, k)
    if not pool:
        return {"answer": "I don’t have indexed content yet. Please ingest documents first.", "citations": []}

    # semantic re-rank
    reranked = rerank_pairs(body.query, pool)

    # fuse semantic + freshness
    reranked = combine_scores(reranked)

    # pick top_n
    chosen = reranked[:top_n]

    answer = generate_answer(body.query, chosen)
    cits = [
        {
            "id": r["id"],
            "url": r.get("meta", {}).get("source_url", ""),
            "score": r.get("final_score", 0.0),
            "freshness": r.get("freshness", 0.0)
        }
        for r in chosen
    ]
    return {"answer": answer, "citations": cits}
