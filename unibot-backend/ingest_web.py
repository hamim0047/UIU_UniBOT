# FILE: ingest_web.py
# Use after running crawl_uiu.py (needs data/raw/web/manifest.csv)

import os
from pathlib import Path
import pandas as pd
from bs4 import BeautifulSoup
from markdownify import markdownify as md
from sentence_transformers import SentenceTransformer
from pypdf import PdfReader
import chromadb

from utils import normalize_ws, chunk_text, safe_filename

# ------------- Config -------------
MANIFEST = Path("data/raw/web/manifest.csv")
OUT_DB = os.getenv("CHROMA_PATH", "./chroma_db")
COLLECTION = os.getenv("CHROMA_COLLECTION", "uni_rag")
EMBED_MODEL = os.getenv("EMBED_MODEL", "sentence-transformers/all-MiniLM-L6-v2")

# chunking: your utils.chunk_text is word-based (named target_tokens)
CHUNK_TOKENS = int(os.getenv("CHUNK_TOKENS", "800"))
OVERLAP_TOKENS = int(os.getenv("OVERLAP_TOKENS", "120"))
EMBED_BATCH = int(os.getenv("EMBED_BATCH", "128"))

# Cap sequence length for the embedder tokenizer (defensive)
EMBED_MAX_SEQ_LENGTH = int(os.getenv("EMBED_MAX_SEQ_LENGTH", "256"))

# ------------- Init -------------
# Avoid HF parallelism warning / forking issues on macOS
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")

encoder = SentenceTransformer(EMBED_MODEL)
# Truncate long inputs safely at the tokenizer level
try:
    encoder.max_seq_length = EMBED_MAX_SEQ_LENGTH
except Exception:
    pass

client = chromadb.PersistentClient(path=OUT_DB)
collection = client.get_or_create_collection(name=COLLECTION, metadata={"hnsw:space": "cosine"})

# ------------- Parsers -------------
def parse_html_text(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()
    for tag in soup.find_all(["nav", "footer"]):
        tag.decompose()
    return normalize_ws(md(str(soup)))

def parse_file(path: Path, ctype: str) -> str:
    ext = path.suffix.lower()
    if "pdf" in (ctype or "") or ext == ".pdf":
        pages = []
        reader = PdfReader(str(path))
        for p in reader.pages:
            pages.append(p.extract_text() or "")
        return normalize_ws("\n\n".join(pages))
    if "html" in (ctype or "") or ext in (".html", ".htm"):
        html = path.read_text(encoding="utf-8", errors="ignore")
        return parse_html_text(html)
    try:
        return normalize_ws(path.read_text(encoding="utf-8", errors="ignore"))
    except Exception:
        return ""

# ------------- Sanitizers -------------
def _is_nan_like(x) -> bool:
    """True for None, NaN, pandas.NA, NaT, etc."""
    try:
        return pd.isna(x)
    except Exception:
        return False

def _to_clean_str(x):
    """Coerce to a clean Python str; return None if impossible/empty."""
    if x is None or _is_nan_like(x):
        return None
    if isinstance(x, bytes):
        try:
            x = x.decode("utf-8", errors="ignore")
        except Exception:
            return None
    elif not isinstance(x, str):
        try:
            x = str(x)
        except Exception:
            return None
    x = x.strip()
    if not x:
        return None
    return x[:8000]  # defensive cap

def sanitize_triplet(ids, docs, metas):
    """Sanitize docs and keep ids/metas aligned."""
    out_ids, out_docs, out_metas = [], [], []
    for i, d, m in zip(ids, docs, metas):
        cd = _to_clean_str(d)
        if cd is None:
            continue
        out_ids.append(i)
        out_docs.append(cd)
        out_metas.append(m)
    return out_ids, out_docs, out_metas

# ------------- Embedding with alignment -------------
def _find_bad_indices(texts):
    """Return indices that fail individual encode attempts."""
    bad = []
    for i, t in enumerate(texts):
        try:
            encoder.encode([t], normalize_embeddings=True, convert_to_numpy=True, show_progress_bar=False)
        except Exception:
            bad.append(i)
    return bad

def embed_aligned(ids, docs, metas):
    """
    Returns aligned (ids_out, docs_out, metas_out, embs_out).
    Drops any samples that fail tokenization from ALL three lists before embedding.
    """
    # Sanitize first
    ids, docs, metas = sanitize_triplet(ids, docs, metas)
    if not docs:
        return [], [], [], []

    texts = docs[:]  # copy
    # Try full-batch encode; on error, locate and drop bad items across all three lists
    while True:
        try:
            embs = encoder.encode(
                texts,
                normalize_embeddings=True,
                convert_to_numpy=True,
                batch_size=max(8, min(EMBED_BATCH, 256)),
                show_progress_bar=False,
            ).tolist()
            # success: lengths must match
            if len(embs) != len(texts):
                # Extremely rare; align by trimming to min length
                k = min(len(embs), len(texts), len(ids), len(metas))
                return ids[:k], docs[:k], metas[:k], embs[:k]
            # Ensure ids/docs/metas match texts after any drops (handled below)
            return ids, docs, metas, embs
        except TypeError:
            bad_idx = set(_find_bad_indices(texts))
            if not bad_idx:
                # Could not isolate; re-raise
                raise
            # Log a compact preview
            previews = []
            for i in sorted(bad_idx)[:3]:
                try:
                    previews.append(repr(texts[i][:120]).replace("\n", " "))
                except Exception:
                    previews.append("<unprintable>")
            print(f"[embed] Dropped {len(bad_idx)} bad sample(s):", "; ".join(previews))

            # Apply drops to ids/docs/metas AND texts in lockstep (same relative positions)
            ids = [v for j, v in enumerate(ids) if j not in bad_idx]
            docs = [v for j, v in enumerate(docs) if j not in bad_idx]
            metas = [v for j, v in enumerate(metas) if j not in bad_idx]
            texts = [v for j, v in enumerate(texts) if j not in bad_idx]

            if not texts:
                return [], [], [], []

# ------------- Ingest -------------
def main():
    if not MANIFEST.exists():
        raise SystemExit("Run crawl_uiu.py first (missing data/raw/web/manifest.csv)")

    df = pd.read_csv(MANIFEST)
    if df.empty:
        print("Manifest has no rows.")
        return

    print(f"Ingesting {len(df)} items into Chroma collection '{COLLECTION}' ...")

    ids_buf, docs_buf, metas_buf = [], [], []

    def flush():
        nonlocal ids_buf, docs_buf, metas_buf
        if not docs_buf:
            return

        s_ids, s_docs, s_metas, embs = embed_aligned(ids_buf, docs_buf, metas_buf)

        # Clear buffers regardless
        ids_buf, docs_buf, metas_buf = [], [], []

        if not s_docs:
            return

        # Final safety: enforce equal lengths
        k = min(len(s_ids), len(s_docs), len(s_metas), len(embs))
        s_ids, s_docs, s_metas, embs = s_ids[:k], s_docs[:k], s_metas[:k], embs[:k]

        try:
            collection.upsert(ids=s_ids, documents=s_docs, metadatas=s_metas, embeddings=embs)
        except Exception:
            collection.add(ids=s_ids, documents=s_docs, metadatas=s_metas, embeddings=embs)

    for _, row in df.iterrows():
        local_path = Path(str(row["local_path"]))
        source_url = str(row.get("source_url", "") or "")
        ctype = str(row.get("content_type", "") or "")
        title = str(row.get("title", "") or "").strip()

        # structured + freshness fields (from crawler)
        address = str(row.get("address", "") or "").strip()
        hotline = str(row.get("hotline", "") or "").strip()
        emails = str(row.get("emails", "") or "").strip()
        published_at = str(row.get("published_at", "") or "").strip()
        updated_at = str(row.get("updated_at", "") or "").strip()
        fetched_at = str(row.get("fetched_at", "") or "").strip()

        if not local_path.exists():
            continue

        try:
            text = parse_file(local_path, ctype)
        except Exception as e:
            print("Skip (parse err):", source_url, "->", e)
            continue

        if not text.strip():
            continue

        # chunk (word-based in your utils)
        chunks = list(chunk_text(text, target_tokens=CHUNK_TOKENS, overlap_tokens=OVERLAP_TOKENS))
        if not chunks:
            continue

        base_id = safe_filename(local_path.stem)  # deterministic per file

        for i, ch in enumerate(chunks):
            clean = _to_clean_str(ch)
            if clean is None:
                continue

            doc_id = f"{base_id}::{i}"
            meta = {
                "doc_id": base_id,
                "source_url": source_url,
                "title": title,
                "content_type": ctype,
                "chunk_index": i,
                # structured facts
                "address": address,
                "hotline": hotline,
                "emails": emails,
                # freshness fields
                "published_at": published_at,
                "updated_at": updated_at,
                "fetched_at": fetched_at,
            }

            ids_buf.append(doc_id)
            docs_buf.append(clean)
            metas_buf.append(meta)

            if len(docs_buf) >= EMBED_BATCH:
                flush()

        print("Indexed:", source_url)

    # last flush
    flush()
    print("Done. Indexed into Chroma at", OUT_DB)

if __name__ == "__main__":
    main()
