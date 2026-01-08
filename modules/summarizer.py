from openai import OpenAI

import os
from dotenv import load_dotenv


load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Initialize OpenAI client
client = OpenAI(api_key=OPENAI_API_KEY)


def summarize_article(title: str, text: str) -> str:
    """Generate a summary for a given article url."""
    if not OPENAI_API_KEY:
        raise Exception("OpenAI API key not set.")

    # Avoid sending extremely long content (saves tokens and avoids errors)
    max_chars = 6000
    safe_text = text[:max_chars]

    prompt = f"""
    You are a professional news summarization assistant.

    Summarize the article below into **2-3 concise bullet points**, 
    focusing only on the factual content. 
    Avoid personal opinions, speculation, or emotional wording.
    
    Each bullet MUST be on its own line and begin with a hyphen ("- "). Do NOT combine multiple bullet points into one line.
    The summary should be:
    - factual
    - concise
    - neutral in tone, written clear, plain

    Title: {title}

    Article Content:
    {safe_text}
    """

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            temperature=0.2,    # low randomness → factual summary
            max_tokens=250,     # prevents long outputs
            messages=[
                {
                    "role": "user",
                    "content": prompt
                }
            ],
        )
        summary = response.choices[0].message.content.strip()
        # Post-processing: normalize bullets
        cleaned_summary = summary.replace(". - ", "\n. - ").replace("•", "- ")
        # Remove double newlines between bullets
        while "\n\n-" in cleaned_summary:
            cleaned_summary = cleaned_summary.replace("\n\n-", "\n-")
        return cleaned_summary.strip()

    except Exception as e:
        print(f"[Summarizer] Error summarizing article '{title[:40]}...': {e}")
        return "Summary unavailable."


def analyze_sentiment(summary_text: str) -> str:
    """
    Classify sentiment of the summary into:
    - positive
    - neutral
    - negative

    Sentiment is intentionally based on the summary, not full article,
    since summaries contain distilled tone and reduce token usage.
    """
    prompt = f"""
    Determine the sentiment of the news summary below.

    Respond with ONLY one of the following words:
    - positive
    - neutral
    - negative

    Summary:
    {summary_text}
    """

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            temperature=0.0,    # classification should be deterministic
            max_tokens=5,
            messages=[
                {
                    "role": "user",
                    "content": prompt}
            ],
        )
        sentiment = response.choices[0].message.content.strip().lower()
        if sentiment not in ["positive", "neutral", "negative"]:
            return "neutral"
        return sentiment

    except Exception as e:
        print(f"[Sentiment Analyzer] Error: {e}")
        return "neutral"
