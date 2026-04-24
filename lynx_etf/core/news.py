"""News fetching for companies."""

from __future__ import annotations

from typing import Optional

import feedparser
import requests
import yfinance as yf

from lynx_etf.core.storage import get_news_dir, save_json, save_text
from lynx_etf.models import NewsArticle


def fetch_news_yfinance(ticker: str) -> list[NewsArticle]:
    """Fetch news from Yahoo Finance via yfinance."""
    try:
        t = yf.Ticker(ticker)
    except Exception:
        return []
    articles: list[NewsArticle] = []

    try:
        news_items = t.news or []
    except Exception:
        news_items = []

    for item in news_items:
        content = item.get("content", item) if isinstance(item, dict) else item
        if isinstance(content, dict):
            title = content.get("title", "")
            url = content.get("canonicalUrl", {})
            if isinstance(url, dict):
                url = url.get("url", "")
            elif not isinstance(url, str):
                url = content.get("link", "")
            pub = content.get("pubDate") or content.get("providerPublishTime", "")
            source = content.get("provider", {})
            if isinstance(source, dict):
                source = source.get("displayName", "")
            summary = content.get("summary", "")
        else:
            continue

        articles.append(NewsArticle(
            title=title,
            url=url if isinstance(url, str) else "",
            published=str(pub),
            source=source if isinstance(source, str) else "",
            summary=summary,
        ))

    return articles


def fetch_news_rss(company_name: str, ticker: str) -> list[NewsArticle]:
    """Fetch news via Google News RSS feed."""
    query = f"{company_name} {ticker} stock"
    feed_url = f"https://news.google.com/rss/search?q={query.replace(' ', '+')}&hl=en&gl=US&ceid=US:en"

    articles: list[NewsArticle] = []
    try:
        feed = feedparser.parse(feed_url)
        for entry in feed.entries[:20]:
            articles.append(NewsArticle(
                title=entry.get("title", ""),
                url=entry.get("link", ""),
                published=entry.get("published", ""),
                source=entry.get("source", {}).get("title", "") if isinstance(entry.get("source"), dict) else "",
                summary=entry.get("summary", ""),
            ))
    except Exception:
        pass

    return articles


def fetch_all_news(ticker: str, company_name: Optional[str] = None) -> list[NewsArticle]:
    """Fetch news from all sources and deduplicate."""
    articles: list[NewsArticle] = []

    # Yahoo Finance news
    yf_news = fetch_news_yfinance(ticker)
    articles.extend(yf_news)

    # Google News RSS
    name = company_name or ticker
    rss_news = fetch_news_rss(name, ticker)

    # Deduplicate by title similarity
    existing_titles = {a.title.lower().strip() for a in articles}
    for art in rss_news:
        if art.title.lower().strip() not in existing_titles:
            articles.append(art)
            existing_titles.add(art.title.lower().strip())

    # Save to local storage
    ndir = get_news_dir(ticker)
    save_json(ndir / "news_index.json", [
        {
            "title": a.title, "url": a.url, "published": a.published,
            "source": a.source, "summary": a.summary,
        }
        for a in articles
    ])

    return articles


def download_article(ticker: str, article: NewsArticle) -> Optional[str]:
    """Download a single news article's content."""
    if not article.url:
        return None

    ndir = get_news_dir(ticker)
    safe_title = "".join(c if c.isalnum() or c in " -_" else "" for c in article.title)[:60].strip()
    path = ndir / f"{safe_title}.txt"

    try:
        resp = requests.get(article.url, timeout=15, headers={
            "User-Agent": "Mozilla/5.0 (compatible; LynxFA/0.1)"
        })
        resp.raise_for_status()

        # Extract text content (simple extraction)
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(resp.text, "html.parser")

        # Remove scripts and styles
        for tag in soup(["script", "style", "nav", "header", "footer"]):
            tag.decompose()

        text = soup.get_text(separator="\n", strip=True)
        # Trim to reasonable size
        text = text[:50000]

        save_text(path, f"Title: {article.title}\nURL: {article.url}\n"
                       f"Published: {article.published}\nSource: {article.source}\n\n{text}")
        article.local_path = str(path)
        return str(path)
    except Exception:
        return None
