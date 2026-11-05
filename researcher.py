"""
Deep History Studio — researcher.
Pulls REAL source text for a topic (Wikipedia REST API, free, no key)
and writes a source digest to memory/sources/<topic>.json.
The writer may only narrate from this digest. No digest = no episode.
Stdlib only.
"""
import json
import os
import re
import time
import urllib.parse
import urllib.request

from config import WIKI_MAX_PAGES, WIKI_EXTRACT_CHARS, SOURCES_DIR

UA = {"User-Agent": "DeepHistoryStudio/1.0 (educational video research)"}
SEARCH_API = "https://en.wikipedia.org/w/api.php?action=query&list=search&format=json&srlimit={limit}&srsearch={q}"
EXTRACT_API = "https://en.wikipedia.org/w/api.php?action=query&prop=extracts&explaintext=1&format=json&titles={title}"
LOC_SEARCH_API = "https://www.loc.gov/search/?q={q}&fo=json&c={limit}"
LOC_MAX_ITEMS = 4
CROSSREF_SEARCH_API = ("https://api.crossref.org/works?query.bibliographic={q}"
                       "&rows={limit}&select=DOI,title,publisher,published,issued,author,abstract,URL")
CROSSREF_MAX_ITEMS = 3


def http_json(url, tries=3):
    err = None
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.loads(r.read().decode())
        except Exception as e:
            err = e
            time.sleep(1.5 * (i + 1))
    raise RuntimeError(f"research: fetch failed: {url} -> {err}")


def slugify(s):
    return re.sub(r"[^a-z0-9]+", "-", (s or "topic").lower()).strip("-") or "topic"


def search_pages(topic, limit):
    """Find the most relevant Wikipedia articles for the topic."""
    q = urllib.parse.quote(topic)
    data = http_json(SEARCH_API.format(limit=limit, q=q))
    hits = []
    for item in (data.get("query", {}).get("search") or []):
        title = item.get("title", "")
        snippet = re.sub(r"<[^>]+>", "", item.get("snippet", ""))
        if title:
            hits.append({"title": title, "hint": snippet})
    return hits


def page_extract(title):
    """Full plain-text extract of one Wikipedia article."""
    t = urllib.parse.quote(title)
    data = http_json(EXTRACT_API.format(title=t))
    pages = data.get("query", {}).get("pages", {})
    for _, page in pages.items():
        return page.get("extract", "") or ""
    return ""


def clean(text):
    """Strip wiki cruft so the writer gets clean prose."""
    text = re.sub(r"\n=+\s*.+?\s*=+\n", "\n\n", text)   # section headers
    text = re.sub(r"\[\d+\]", "", text)                  # [12] citations
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()



def _field_text(value):
    """Normalize optional LOC JSON fields that may be strings or string arrays."""
    if isinstance(value, list):
        return "; ".join(str(x).strip() for x in value if x)
    if isinstance(value, str):
        return value.strip()
    return ""


def parse_loc_results(payload, limit=LOC_MAX_ITEMS):
    """Turn LOC catalog records into attributed, metadata-only research sources."""
    sources = []
    for item in (payload.get("results") or [])[:limit]:
        if not isinstance(item, dict):
            continue
        title = _field_text(item.get("title"))
        description = _field_text(item.get("description"))
        if not title or len(description) < 80:
            continue
        date = _field_text(item.get("date"))
        creator = _field_text(item.get("contributor"))
        collection = _field_text(item.get("partof"))
        rights = _field_text(item.get("rights"))
        url = _field_text(item.get("url") or item.get("id"))
        if not url:
            continue
        text = "\n".join(
            line for line in [
                f"Library of Congress catalog record: {title}",
                f"Date: {date}" if date else "",
                f"Creator/contributor: {creator}" if creator else "",
                f"Collection: {collection}" if collection else "",
                f"Catalog description: {description}",
            ] if line
        )
        sources.append({
            "title": title,
            "url": url,
            "text": clean(text)[:WIKI_EXTRACT_CHARS],
            "source_type": "Library of Congress catalog",
            "evidence_level": "catalog metadata; corroboration only",
            "date": date or None,
            "creator": creator or None,
            "rights": rights or "not stated in catalog response",
        })
    return sources


def search_loc_records(topic, limit=LOC_MAX_ITEMS):
    """Search the free LOC JSON API; no API key is required."""
    q = urllib.parse.quote(topic)
    url = LOC_SEARCH_API.format(q=q, limit=int(limit))
    payload = http_json(url)
    return parse_loc_results(payload, limit=limit)


def parse_crossref_results(payload, limit=CROSSREF_MAX_ITEMS):
    """Parse Crossref scholarly metadata; abstracts remain attributed leads, not primary proof."""
    message = payload.get("message") or {}
    sources = []
    for item in (message.get("items") or [])[:limit]:
        if not isinstance(item, dict):
            continue
        title = _field_text(item.get("title"))
        if not title:
            continue
        doi = _field_text(item.get("DOI"))
        url = _field_text(item.get("URL")) or (f"https://doi.org/{doi}" if doi else "")
        if not url:
            continue
        authors = []
        for author in item.get("author") or []:
            if not isinstance(author, dict):
                continue
            name = " ".join(x for x in [
                str(author.get("given") or "").strip(),
                str(author.get("family") or "").strip()
            ] if x)
            if name:
                authors.append(name)
        date_obj = item.get("published") or item.get("issued") or {}
        parts = (date_obj.get("date-parts") or [[]]) if isinstance(date_obj, dict) else [[]]
        year = str(parts[0][0]) if parts and parts[0] else ""
        abstract = item.get("abstract") or ""
        abstract = clean(re.sub(r"<[^>]+>", " ", str(abstract)))
        publisher = _field_text(item.get("publisher"))
        record = [
            f"Crossref scholarly record: {title}",
            f"Authors: {', '.join(authors[:8])}" if authors else "",
            f"Year: {year}" if year else "",
            f"Publisher: {publisher}" if publisher else "",
            f"DOI: {doi}" if doi else "",
            f"Publisher-supplied abstract: {abstract[:2500]}" if abstract else "",
        ]
        sources.append({
            "title": title,
            "url": url,
            "text": "\\n".join(x for x in record if x)[:WIKI_EXTRACT_CHARS],
            "source_type": "Crossref scholarly metadata",
            "evidence_level": "publisher-supplied bibliographic metadata/abstract; corroborate with primary sources",
            "date": year or None,
            "creator": ", ".join(authors[:8]) or None,
            "doi": doi or None,
            "rights": "abstract rights remain with the publisher; use as attributed research context",
        })
    return sources


def search_crossref_records(topic, limit=CROSSREF_MAX_ITEMS):
    """Search Crossref's public REST API; no API key is required."""
    q = urllib.parse.quote(topic)
    url = CROSSREF_SEARCH_API.format(q=q, limit=int(limit))
    return parse_crossref_results(http_json(url), limit=limit)

def build_digest(topic):
    """Search multiple free catalogs; never turn metadata into invented facts."""
    print(f"[research] topic: {topic}")
    sources = []

    try:
        hits = search_pages(topic, WIKI_MAX_PAGES + 2)
    except Exception as e:
        print(f"[research] Wikipedia search unavailable: {e}")
        hits = []
    for hit in hits[:WIKI_MAX_PAGES]:
        title = hit["title"]
        try:
            raw = page_extract(title)
        except Exception as e:
            print(f"[research] {title} failed: {e}")
            continue
        text = clean(raw)[:WIKI_EXTRACT_CHARS]
        if len(text) < 400:
            continue
        sources.append({
            "title": title,
            "url": f"https://en.wikipedia.org/wiki/{urllib.parse.quote(title.replace(' ', '_'))}",
            "text": text,
            "source_type": "Wikipedia article extract",
            "evidence_level": "secondary source",
        })
        print(f"[research] + Wikipedia: {title} ({len(text)} chars)")
        time.sleep(1)

    try:
        loc_sources = search_loc_records(topic)
        sources.extend(loc_sources)
        for source in loc_sources:
            print(f"[research] + LOC catalog: {source['title']}")
    except Exception as e:
        print(f"[research] Library of Congress search unavailable: {e}")

    try:
        scholarly = search_crossref_records(topic)
        sources.extend(scholarly)
        for source in scholarly:
            print(f"[research] + Crossref: {source['title']}")
    except Exception as e:
        print(f"[research] Crossref search unavailable: {e}")

    if not sources:
        raise RuntimeError(f"research: no usable sources found for '{topic}'")
    digest = {
        "topic": topic,
        "generated_at": int(time.time()),
        "source_count": len(sources),
        "rule": "The narrator may ONLY state facts present in source texts. LOC catalog descriptions are metadata and corroboration, not proof of every detail. Crossref metadata/abstracts are attributed scholarly leads, not primary evidence; verify important claims against primary sources. If sources disagree or are silent, say so.",
        "sources": sources,
    }
    return digest


def digest_path(topic):
    os.makedirs(SOURCES_DIR, exist_ok=True)
    return os.path.join(SOURCES_DIR, f"{slugify(topic)}.json")


def research_topic(topic, force=False):
    """Research (or reuse cached) sources for a topic. Returns (path, digest)."""
    path = digest_path(topic)
    if not force and os.path.exists(path):
        with open(path) as f:
            print(f"[research] cached digest: {path}")
            return path, json.load(f)
    digest = build_digest(topic)
    with open(path, "w") as f:
        json.dump(digest, f, indent=1)
    print(f"[research] digest saved: {path} ({digest['source_count']} sources)")
    return path, digest


def load_digest(topic):
    path = digest_path(topic)
    if not os.path.exists(path):
        return None
    with open(path) as f:
        return json.load(f)


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("usage: python researcher.py <topic>")
        raise SystemExit(1)
    _, d = research_topic(sys.argv[1], force=True)
    print(f"[research] done: {d['source_count']} sources for '{sys.argv[1]}'")
