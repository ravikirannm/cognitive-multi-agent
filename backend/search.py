import re
from typing import Dict, List

import requests
from bs4 import BeautifulSoup
from ddgs import DDGS

USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
)


def _clean_text(text: str) -> str:
    cleaned = re.sub(r"\s+", " ", text or "")
    return cleaned.strip()


def _extract_text_from_html(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    for script in soup(["script", "style", "noscript"]):
        script.decompose()

    paragraphs = []
    for tag in soup.find_all(["h1", "h2", "h3", "p"]):
        text = tag.get_text(separator=" ", strip=True)
        if text:
            paragraphs.append(text)

    text = "\n\n".join(paragraphs)
    return _clean_text(text)


def fetch_url_text(url: str, max_chars: int = 3000) -> str:
    try:
        headers = {"User-Agent": USER_AGENT}
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        if "text/html" not in response.headers.get("Content-Type", ""):
            return ""
        text = _extract_text_from_html(response.text)
        return text[:max_chars]
    except requests.RequestException:
        return ""


def web_search(query: str, max_results: int = 4) -> List[Dict[str, str]]:
    try:
        results = DDGS().text(query, max_results=max_results)
    except Exception:
        results = []

    if not results:
        return []

    return [
        {
            "title": result.get("title", ""),
            "snippet": result.get("body", ""),
            "url": result.get("href", ""),
        }
        for result in results
    ]


def collect_research_context(topics: List[str], max_results: int = 3) -> str:
    entries = []
    for topic in topics:
        entries.append(f"## Topic: {topic}")
        results = web_search(topic, max_results=max_results)
        for result in results:
            title = result["title"]
            url = result["url"]
            snippet = result["snippet"]
            if url:
                page_text = fetch_url_text(url, max_chars=2000)
            else:
                page_text = ""

            entries.append(f"- {title}")
            entries.append(f"  URL: {url}")
            if snippet:
                entries.append(f"  Snippet: {snippet}")
            if page_text:
                entries.append(f"  Page excerpt: {page_text[:800]}")
        entries.append("")

    if not entries:
        return "No external research context available."
    return "\n".join(entries)
