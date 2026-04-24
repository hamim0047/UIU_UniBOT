# FILE: crawl_uiu.py
# pip install requests beautifulsoup4 markdownify tldextract pandas pdfminer.six
import os, time, hashlib, mimetypes, re, math, random, json, datetime
from urllib.parse import urljoin, urlparse, urldefrag, parse_qsl, urlunparse
from urllib import robotparser
from collections import deque

import requests
from bs4 import BeautifulSoup
import pandas as pd

try:
    from pdfminer.high_level import extract_text as pdf_extract_text
except Exception:
    pdf_extract_text = None  # optional; if missing, we'll skip PDF text

# ==========================
# Config
# ==========================
SEEDS = [
    "https://www.uiu.ac.bd/",
    "https://www.uiu.ac.bd/contact-us/",
    "https://www.uiu.ac.bd/about-uiu/uiu-campus/",
    "https://www.uiu.ac.bd/admission/",
    "https://www.uiu.ac.bd/admission/tuition-fees-payment-policies/",
    "https://www.uiu.ac.bd/admission/tuition-fees-payment-policies/tuition-fees-waiver/",
    "https://www.uiu.ac.bd/academics/",
    "https://www.uiu.ac.bd/academics/calendar/",
    # high-signal areas for schedules & notices:
    "https://www.uiu.ac.bd/notices/",
    "https://www.uiu.ac.bd/category/notice/",
    "https://www.uiu.ac.bd/category/exam-schedule/",
    "https://www.uiu.ac.bd/academics/notice/",
    # sub-sites
    "https://admission.uiu.ac.bd/",
    "https://cse.uiu.ac.bd/ug-program/course-plan/",
]

# Allowlist base domains (add more dept subdomains as needed)
ALLOWED = {
    "uiu.ac.bd",
    "admission.uiu.ac.bd",
    "cse.uiu.ac.bd",
    "eee.uiu.ac.bd",
    "sobe.uiu.ac.bd",
    "cdip.uiu.ac.bd",
    "datascience.uiu.ac.bd",
    "pharmacy.uiu.ac.bd",
    "english.uiu.ac.bd",
    "msj.uiu.ac.bd",
    "eds.uiu.ac.bd",
    "bge.uiu.ac.bd",
}

OUT_DIR = "data/raw/web"
os.makedirs(OUT_DIR, exist_ok=True)

USER_AGENT = "UIU-RAG-Crawler/1.2 (+for research; contact: your_email@example.com)"
MAX_PAGES = 2000
MAX_DEPTH = 3
REQUEST_DELAY = 0.7  # base politeness (seconds) if robots has no crawl-delay
TIMEOUT = 25

session = requests.Session()
session.headers.update({"User-Agent": USER_AGENT, "Accept": "*/*"})

# File types we should skip as navigational targets
SKIP_EXTS = {
    ".jpg",".jpeg",".png",".gif",".webp",".svg",".ico",".mp4",".mp3",".zip",".rar",
    ".7z",".tar",".gz",".tgz",".bz2",".xz",".ics",".doc",".docx",".ppt",".pptx",
    ".xls",".xlsx",".apk",".exe",".dmg",".iso"
}

EMAIL_PAT = re.compile(r"[A-Za-z0-9._%+-]+@(?:[A-Za-z0-9-]+\.)+[A-Za-z]{2,}", re.I)
HOTLINE_PAT = re.compile(r"(09604[-\s]*848848)", re.I)
ADDRESS_PAT = re.compile(
    r"(United\s+City.*?(?:Satarkul,?\s*)?Madani\s+Avenue.*?Badda.*?Dhaka\s*[-]?\s*1212.*?(?:Bangladesh)?)",
    re.I | re.S
)

# Date patterns for URL hints
URL_DATE_PATS = [
    re.compile(r"/(20\d{2})/(0?\d{1}|1[0-2])/(0?\d{1}|[12]\d|3[01])/"),   # /yyyy/mm/dd/
    re.compile(r"(20\d{2})[-_/](0?\d{1}|1[0-2])[-_/](0?\d{1}|[12]\d|3[01])"),  # yyyy-mm-dd
    re.compile(r"/(20\d{2})/(0?\d{1}|1[0-2])/?"),                         # /yyyy/mm/
    re.compile(r"/(20\d{2})/"),                                           # /yyyy/
]

def parse_url_date(url: str):
    u = url or ""
    for pat in URL_DATE_PATS:
        m = pat.search(u)
        if not m:
            continue
        g = [int(x) for x in m.groups() if x]
        try:
            if len(g) == 3:
                y, mth, d = g
                return datetime.date(y, mth, d)
            if len(g) == 2:
                y, mth = g
                return datetime.date(y, mth, 1)
            if len(g) == 1:
                y = g[0]
                return datetime.date(y, 1, 1)
        except Exception:
            pass
    return None

# ==========================
# Helpers
# ==========================
def is_allowed(url: str) -> bool:
    host = urlparse(url).netloc.lower()
    host = host[4:] if host.startswith("www.") else host
    return any(host == a or host.endswith("." + a) for a in ALLOWED)

def strip_tracking_params(url: str) -> str:
    parsed = urlparse(url)
    q = [(k, v) for (k, v) in parse_qsl(parsed.query, keep_blank_values=True)
         if not k.lower().startswith(("utm_", "fbclid", "gclid", "mc_", "cmp", "ref"))]
    return urlunparse(parsed._replace(query="&".join(f"{k}={v}" for k, v in q)))

def canon(url: str) -> str:
    url, _frag = urldefrag(url)
    url = strip_tracking_params(url)
    p = urlparse(url)
    url = urlunparse((p.scheme.lower(), p.netloc.lower(), p.path, p.params, p.query, ""))
    return url

def get_title(html: str) -> str:
    try:
        soup = BeautifulSoup(html, "html.parser")
        title = soup.title.string.strip() if soup.title and soup.title.string else ""
        return re.sub(r"\s+", " ", title)[:300]
    except Exception:
        return ""

def html_to_text(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "noscript"]):
        tag.extract()
    for tag in soup.find_all(["nav", "footer"]):
        tag.decompose()
    text = " ".join(soup.stripped_strings)
    text = re.sub(r"\s+", " ", text)
    return text.strip()

def file_name(url: str, content_type: str) -> str:
    ext = mimetypes.guess_extension((content_type or "").split(";")[0]) or ""
    if "html" in (content_type or "") and ext not in (".html", ".htm"):
        ext = ".html"
    if "pdf" in (content_type or ""):
        ext = ".pdf"
    h = hashlib.sha1(url.encode("utf-8")).hexdigest()[:16]
    return f"{h}{ext}"

def should_skip_link(href: str) -> bool:
    if href.startswith(("mailto:", "tel:", "javascript:", "data:")):
        return True
    path = urlparse(href).path.lower()
    _, ext = os.path.splitext(path)
    return ext in SKIP_EXTS

def backoff_sleep(base: float, attempt: int):
    jitter = random.uniform(0, 0.3)
    time.sleep(base * (1.5 ** attempt) + jitter)

def get_crawl_delay(rp: robotparser.RobotFileParser, default_delay: float) -> float:
    try:
        delay = rp.crawl_delay(USER_AGENT)
        if delay is None:
            delay = rp.crawl_delay("*")
        if delay and delay > 0:
            return float(delay)
    except Exception:
        pass
    return default_delay

def extract_structured_fields(text_like: str):
    hotline = None
    m = HOTLINE_PAT.search(text_like)
    if m:
        hotline = m.group(1).replace("-", " ").strip()
    address = None
    a = ADDRESS_PAT.search(text_like)
    if a:
        address = re.sub(r"\s+", " ", a.group(1)).strip()
    emails = sorted(set(EMAIL_PAT.findall(text_like)))
    return {"address": address, "hotline": hotline, "emails": emails}

def parse_iso_date(s: str):
    try:
        return datetime.datetime.fromisoformat(s.replace("Z", "+00:00")).date()
    except Exception:
        pass
    m = re.search(r"(20\d{2})-(\d{1,2})-(\d{1,2})", s)
    if m:
        y, mth, d = map(int, m.groups())
        try:
            return datetime.date(y, mth, d)
        except Exception:
            return None
    return None

def extract_dates_from_html(html: str):
    """Return (published_at, updated_at) if found in HTML metas/time/JSON-LD."""
    soup = BeautifulSoup(html, "html.parser")
    pub, upd = None, None

    # meta tags candidates
    meta_pairs = [
        ("property", "article:published_time"),
        ("name", "article:published_time"),
        ("property", "og:updated_time"),
        ("name", "last-modified"),
        ("name", "pubdate"),
        ("name", "date"),
        ("property", "article:modified_time"),
    ]
    for attr, key in meta_pairs:
        for m in soup.find_all("meta", attrs={attr: key}):
            val = (m.get("content") or "").strip()
            dt = parse_iso_date(val)
            if not dt:
                continue
            if "published" in key or "pub" in key:
                if not pub or dt < pub:  # keep earliest publish if multiple
                    pub = dt
            else:
                upd = dt if (not upd or dt > upd) else upd

    # <time datetime=...>
    for t in soup.find_all("time"):
        v = t.get("datetime") or t.get("content") or ""
        dt = parse_iso_date(v)
        if dt:
            pub = pub or dt

    # JSON-LD Article/NewsArticle
    for tag in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(tag.string or "")
        except Exception:
            continue
        candidates = data if isinstance(data, list) else [data]
        for obj in candidates:
            if not isinstance(obj, dict):
                continue
            dtype = (obj.get("@type") or "")
            if isinstance(dtype, list):
                dtype = " ".join(dtype)
            if "Article" in dtype or "NewsArticle" in dtype or "BlogPosting" in dtype:
                dp = obj.get("datePublished") or obj.get("dateCreated")
                dm = obj.get("dateModified") or obj.get("dateUpdated")
                if dp:
                    dt = parse_iso_date(str(dp))
                    if dt:
                        pub = pub or dt
                if dm:
                    dt = parse_iso_date(str(dm))
                    if dt:
                        upd = dt if (not upd or dt > upd) else upd

    return pub, upd

def fetch(session, url, timeout=TIMEOUT, retries=2, base_delay=REQUEST_DELAY):
    for attempt in range(retries + 1):
        try:
            return session.get(url, timeout=timeout)
        except Exception:
            if attempt >= retries:
                return None
            backoff_sleep(base_delay, attempt)

# ==========================
# Crawl (with robots + sitemap)
# ==========================
def discover_sitemaps(host_root: str):
    sitemaps = []
    try:
        robots_url = urljoin(host_root, "/robots.txt")
        r = session.get(robots_url, timeout=10)
        if r.ok:
            for line in r.text.splitlines():
                line = line.strip()
                if line.lower().startswith("sitemap:"):
                    sm = line.split(":", 1)[1].strip()
                    if sm:
                        sitemaps.append(sm)
    except Exception:
        pass
    return sitemaps

def parse_xml_links(xml_text: str):
    try:
        return re.findall(r"<loc>(.*?)</loc>", xml_text, flags=re.I)
    except Exception:
        return []

def crawl():
    robots = {}
    crawl_delays = {}

    q = deque()
    seen = set()
    pages = []
    count = 0

    # seed
    for s in SEEDS:
        if is_allowed(s):
            q.append((canon(s), 0))

    # add sitemaps for each host
    roots = set()
    for s in list(SEEDS):
        p = urlparse(s)
        roots.add(f"{p.scheme}://{p.netloc}")

    for root in list(roots):
        if root not in robots:
            rp = robotparser.RobotFileParser()
            try:
                rp.set_url(urljoin(root, "/robots.txt"))
                rp.read()
            except Exception:
                pass
            robots[root] = rp
            crawl_delays[root] = get_crawl_delay(rp, REQUEST_DELAY)

        for sm in discover_sitemaps(root):
            sm = canon(sm)
            if is_allowed(sm):
                q.append((sm, 0))

    while q and count < MAX_PAGES:
        url, depth = q.popleft()
        url = canon(url)
        if url in seen:
            continue
        seen.add(url)

        if not is_allowed(url):
            continue

        p = urlparse(url)
        host_root = f"{p.scheme}://{p.netloc}"
        rp = robots.get(host_root)
        if not rp:
            rp = robotparser.RobotFileParser()
            try:
                rp.set_url(urljoin(host_root, "/robots.txt"))
                rp.read()
            except Exception:
                pass
            robots[host_root] = rp
            crawl_delays[host_root] = get_crawl_delay(rp, REQUEST_DELAY)

        if rp and hasattr(rp, "can_fetch") and not rp.can_fetch(USER_AGENT, url):
            continue

        r = fetch(session, url)
        if not r or not r.ok:
            continue

        fetched_at = datetime.datetime.utcnow().isoformat() + "Z"
        ctype = r.headers.get("Content-Type", "").lower()

        # sitemaps
        if "xml" in ctype and depth < MAX_DEPTH + 1:
            links = parse_xml_links(r.text)
            for loc in links:
                loc = canon(loc)
                if is_allowed(loc) and not should_skip_link(loc):
                    q.append((loc, 0))
            time.sleep(crawl_delays.get(host_root, REQUEST_DELAY))
            continue

        if "text/html" in ctype:
            html = r.text
            title = get_title(html)
            text = html_to_text(html)

            # dates from HTML + headers + URL
            pub, upd = extract_dates_from_html(html)
            if not pub:
                # HTTP Last-Modified as a fallback publish/update hint
                lm = r.headers.get("Last-Modified")
                if lm:
                    try:
                        pub = datetime.datetime.strptime(lm, "%a, %d %b %Y %H:%M:%S %Z").date()
                    except Exception:
                        pass
            url_date = parse_url_date(url)
            if not pub and url_date:
                pub = url_date

            # save raw HTML
            fname = file_name(url, "text/html")
            fpath = os.path.join(OUT_DIR, fname)
            with open(fpath, "w", encoding="utf-8", errors="ignore") as f:
                f.write(html)

            fields = extract_structured_fields(text)

            pages.append({
                "local_path": fpath,
                "source_url": url,
                "content_type": "text/html",
                "title": title,
                "text": text,
                "address": fields.get("address") or "",
                "hotline": fields.get("hotline") or "",
                "emails": ";".join(fields.get("emails") or []),
                "published_at": pub.isoformat() if isinstance(pub, datetime.date) else "",
                "updated_at": upd.isoformat() if isinstance(upd, datetime.date) else "",
                "fetched_at": fetched_at,
            })
            count += 1

            # enqueue
            if depth < MAX_DEPTH:
                soup = BeautifulSoup(html, "html.parser")
                for a in soup.find_all("a", href=True):
                    href = a["href"].strip()
                    if not href:
                        continue
                    href = urljoin(url, href)
                    if should_skip_link(href):
                        continue
                    if is_allowed(href):
                        q.append((canon(href), depth + 1))

        elif any(x in ctype for x in ["application/pdf", "application/octet-stream"]):
            fname = file_name(url, "application/pdf")
            fpath = os.path.join(OUT_DIR, fname)
            with open(fpath, "wb") as f:
                f.write(r.content)

            pdf_text = ""
            if pdf_extract_text:
                try:
                    pdf_text = pdf_extract_text(fpath) or ""
                    pdf_text = re.sub(r"\s+", " ", pdf_text).strip()
                except Exception:
                    pdf_text = ""

            # PDFs rarely have embedded dates; rely on URL & header if any
            pub = None
            lm = r.headers.get("Last-Modified")
            if lm:
                try:
                    pub = datetime.datetime.strptime(lm, "%a, %d %b %Y %H:%M:%S %Z").date()
                except Exception:
                    pass
            url_date = parse_url_date(url)
            if not pub and url_date:
                pub = url_date

            fields = extract_structured_fields(pdf_text or "")
            pages.append({
                "local_path": fpath,
                "source_url": url,
                "content_type": "application/pdf",
                "title": "",
                "text": pdf_text,
                "address": fields.get("address") or "",
                "hotline": fields.get("hotline") or "",
                "emails": ";".join(fields.get("emails") or []),
                "published_at": pub.isoformat() if isinstance(pub, datetime.date) else "",
                "updated_at": "",
                "fetched_at": fetched_at,
            })
            count += 1

        time.sleep(crawl_delays.get(host_root, REQUEST_DELAY))

    # write manifest
    manifest_path = os.path.join(OUT_DIR, "manifest.csv")
    cols = [
        "local_path", "source_url", "content_type", "title", "text",
        "address", "hotline", "emails",
        "published_at", "updated_at", "fetched_at"
    ]
    pd.DataFrame(pages)[cols].to_csv(manifest_path, index=False)
    print(f"Saved {len(pages)} items → {manifest_path}")

if __name__ == "__main__":
    crawl()
