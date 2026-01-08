import requests
from models import db, Article
from newspaper import Article as NPArticle
from modules.summarizer import summarize_article, analyze_sentiment
from modules.embedding_manager import generate_embedding

import os
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()
NEWS_API_KEY = os.getenv("NEWS_API_KEY")
NEWS_API_URL = "https://newsapi.org/v2/everything"


def fetch_from_newsapi(topic, language="en", page_size=5):
    """
    Fetch default 5 articles from NewsAPI for a given topic/language and store data.
    Each article is extracted with full text by newspaper and summarized.
    """
    if not NEWS_API_KEY:
        raise RuntimeError("NEWS_API_KEY missing in environment")

    print(f"[NewsMind] Fetching '{topic}' news from NewsAPI...")
    new_articles = 0

    params = {
        "q": topic,
        "language": language,
        "sortBy": "publishedAt",
        "pageSize": page_size,
        "apiKey": NEWS_API_KEY
    }

    # Fetch news data from NesAPI
    try:
        response = requests.get(NEWS_API_URL, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
    except Exception as e:
        print(f"[NewsMind] Fetcher error: {e}")
        return 0

    if data.get("status") != "ok":
        print(f"[NewsMind] API error: {data.get('message')}")
        return 0

    # Process each article from the fetching
    for item in data.get("articles", []):
        author = item.get("author") or "Unknown"
        title = item.get("title")
        url = item.get("url")
        source = item.get("source", {}).get("name", "")
        published_at = item.get("publishedAt") or datetime.utcnow()

        # Skip bad data
        if not title or not url:
            continue
        # Skip duplicates
        if Article.query.filter_by(url=url).first():
            continue

        # Extract full text using Newspaper3k
        full_text = extract_full_text(url)
        if not full_text or len(full_text) < 200 or full_text.startswith("[Extractor]"):
            print(f"[NewsMind] Skipping (no valid text): {title[:50]}...")
            continue

        # Limit extremely long text
        full_text = full_text[:5000]

        # Summarize full article using OpenAI
        summary = summarize_article(title, full_text)
        # Sentiment Analysis using OpenAI
        sentiment = analyze_sentiment(summary)
        # Generate embedding: both title and summary
        combined_text = f"{title.strip()}\n\n{summary.strip()}"
        embedding = generate_embedding(combined_text)
    
        # Save to DB Article
        try:
            article = Article(
                title=title[:500],
                author=author[:100] if author else "Unknown",
                source=source[:200],
                url=url,
                category=topic,
                published_at=published_at,
                fetched_at=datetime.utcnow(),
                summary=summary,
                sentiment=sentiment,
                embedding=embedding
            )
            db.session.add(article)
            db.session.commit()

            new_articles += 1
            print(f"[NewsMind] Saved: '{title[:40]}...', topic={topic} sentiment={sentiment}")

        except Exception as e:
            print(f"[NewsMind] DB error: {e}")
            db.session.rollback()

    print(f"[NewsMind] Added {new_articles} new articles for '{topic}'.")
    return new_articles
#fetch_from_newsapi(topic="AI", page_size=5, language="en")


def extract_full_text(url):
    """
    Extract full article text (NOT saved in DB).
    Used when the user opens article page.
    """
    try:
        np_art = NPArticle(url)
        np_art.download()
        np_art.parse()
        text = np_art.text.strip()

        # Required minimum for meaningful summary
        if len(text) < 200:
            print(f"[NewsMind] Text too short for: {url}")
            return None

        return text

    except Exception as e:
        print(f"[NewsMind] Newspaper failed for {url}: {e}")
        return None
