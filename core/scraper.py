"""
Deep content scraper using Scrapling.
Fetches full article text from URLs found by Tavily/Gemini searches.
Falls back gracefully if a page can't be scraped.
"""

import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from rich.console import Console

console = Console()

try:
    from scrapling import Fetcher
    SCRAPLING_AVAILABLE = True
except ImportError:
    SCRAPLING_AVAILABLE = False


def _extract_article_text(html_response) -> dict:
    """Extract structured content from a Scrapling response."""
    try:
        title = ""
        title_el = html_response.css("title")
        if title_el:
            title = title_el[0].text.strip()

        # Try common article selectors in priority order
        content = ""
        selectors = [
            "article",
            '[role="main"]',
            ".article-body",
            ".story-body",
            ".post-content",
            ".entry-content",
            ".article-content",
            ".content-body",
            ".field-body",
            "#article-body",
            "#content",
            "main",
        ]

        for sel in selectors:
            elements = html_response.css(sel)
            if elements:
                paragraphs = elements[0].css("p")
                if paragraphs:
                    content = "\n\n".join(
                        p.text.strip() for p in paragraphs if p.text and len(p.text.strip()) > 20
                    )
                    if len(content) > 200:
                        break

        # Fallback: grab all <p> tags from body
        if len(content) < 200:
            paragraphs = html_response.css("p")
            content = "\n\n".join(
                p.text.strip() for p in paragraphs
                if p.text and len(p.text.strip()) > 30
            )

        # Extract metadata
        meta_desc = ""
        meta_el = html_response.css('meta[name="description"]')
        if meta_el:
            meta_desc = meta_el[0].attrib.get("content", "")

        meta_date = ""
        for date_sel in [
            'meta[property="article:published_time"]',
            'meta[name="date"]',
            'meta[name="publish-date"]',
            'time[datetime]',
        ]:
            date_el = html_response.css(date_sel)
            if date_el:
                meta_date = date_el[0].attrib.get("content", "") or date_el[0].attrib.get("datetime", "")
                break

        # Extract author
        author = ""
        for auth_sel in [
            'meta[name="author"]',
            'meta[property="article:author"]',
            ".author-name",
            ".byline",
            '[rel="author"]',
        ]:
            auth_el = html_response.css(auth_sel)
            if auth_el:
                author = auth_el[0].attrib.get("content", "") or auth_el[0].text or ""
                author = author.strip()
                break

        # Extract all links (for cross-referencing)
        internal_links = []
        for a in html_response.css("a[href]"):
            href = a.attrib.get("href", "")
            link_text = (a.text or "").strip()
            if href and link_text and len(link_text) > 5 and not href.startswith("#"):
                internal_links.append({"text": link_text[:100], "url": href})
                if len(internal_links) >= 20:
                    break

        return {
            "title": title,
            "content": content[:15000],  # Cap at 15k chars
            "meta_description": meta_desc,
            "date": meta_date,
            "author": author,
            "word_count": len(content.split()),
            "links": internal_links[:10],
        }
    except Exception as e:
        return {"title": "", "content": "", "error": str(e), "word_count": 0}


def scrape_url(url: str, timeout: int = 30) -> dict:
    """Scrape a single URL and return structured content."""
    if not SCRAPLING_AVAILABLE:
        return {"url": url, "content": "", "error": "scrapling not installed", "word_count": 0}

    try:
        fetcher = Fetcher()
        response = fetcher.get(url, timeout=timeout, stealthy_headers=True)
        extracted = _extract_article_text(response)
        extracted["url"] = url
        extracted["status"] = response.status
        return extracted
    except Exception as e:
        return {"url": url, "content": "", "error": str(e), "word_count": 0}


def scrape_urls(urls: list, max_workers: int = 5, timeout: int = 30, label: str = "") -> list:
    """Scrape multiple URLs in parallel. Returns list of extracted content dicts."""
    if not SCRAPLING_AVAILABLE:
        console.print("  [yellow]! Scrapling not installed -- skipping deep content fetch[/]")
        return []

    if not urls:
        return []

    urls = list(set(urls))[:30]  # Dedupe, cap at 30 URLs

    results = []
    successful = 0
    total_words = 0

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_url = {
            executor.submit(scrape_url, url, timeout): url
            for url in urls
        }

        for future in as_completed(future_to_url):
            url = future_to_url[future]
            try:
                result = future.result()
                if result.get("word_count", 0) > 50:
                    results.append(result)
                    successful += 1
                    total_words += result["word_count"]
            except Exception:
                pass

    if label:
        console.print(
            f"    Scraped {successful}/{len(urls)} pages "
            f"({total_words:,} words) [{label}]"
        )

    return results


def build_content_block(scraped_results: list) -> str:
    """Build a text block from scraped content for LLM consumption."""
    if not scraped_results:
        return ""

    block = ""
    for r in scraped_results:
        if r.get("word_count", 0) < 50:
            continue

        block += f"\n\n{'='*60}\n"
        block += f"SOURCE: {r.get('title', 'Unknown')}\n"
        block += f"URL: {r.get('url', '')}\n"
        if r.get("author"):
            block += f"AUTHOR: {r['author']}\n"
        if r.get("date"):
            block += f"DATE: {r['date']}\n"
        block += f"WORDS: {r.get('word_count', 0)}\n"
        block += f"{'='*60}\n\n"
        block += r.get("content", "")

    return block
