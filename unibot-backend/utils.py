import re
import unicodedata

def normalize_ws(text: str) -> str:
    text = text.replace("\r", "\n")
    text = re.sub(r"\u00a0", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text

def chunk_text(text: str, target_tokens: int = 800, overlap_tokens: int = 120):
    words = text.split()
    n = len(words)
    step = max(1, target_tokens - overlap_tokens)
    for start in range(0, n, step):
        end = min(n, start + target_tokens)
        yield " ".join(words[start:end])

def safe_filename(name: str) -> str:
    name = unicodedata.normalize("NFKD", name)
    name = re.sub(r"[^a-zA-Z0-9-_\\.]+", "_", name)
    return name[:120]
