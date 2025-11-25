from models import db, Article
from openai import OpenAI

import os
from dotenv import load_dotenv


load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

client = OpenAI(api_key=OPENAI_API_KEY)


def summarize_article(title, text):
    """Generate a summary for a given article url."""
    if not OPENAI_API_KEY:
        raise Exception("OpenAI API key not set.")

    prompt = f"""Summarize the following article in 3 bullet points:
    Title: {title}
    
    Content:
    {text}
    """

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "user",
                    "content": prompt
                }
            ],
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"[Summarizer] Error: {e}")
        return "Summary unavailable."

#print(summarize_article())
