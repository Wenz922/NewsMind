from openai import OpenAI
import google.generativeai as genai

from models import db, Article, ChatHistory
from modules.embedding_manager import generate_embedding, compute_similarity

import os
from datetime import datetime
from dotenv import load_dotenv


load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")


openai_client = OpenAI(api_key=OPENAI_API_KEY)
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)


# ---------- Retrieval ----------

def retrieve_relevant_articles(query: str, top_k: int = 3):
    """Embed the user query and find top-k most similar articles based on embeddings."""
    query_emb = generate_embedding(query)
    if not query_emb or query_emb == "[]":
        return []

    articles = Article.query.filter(Article.embedding.isnot(None)).all()
    scored = []

    for art in articles:
        if not art.embedding:
            continue
        sim = compute_similarity(query_emb, art.embedding)
        scored.append((sim, art))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [art for sim, art in scored[:top_k] if sim > 0]


def build_context_from_articles(articles):
    """Build a readable context block from article summaries."""
    blocks = []
    for idx, art in enumerate(articles, start=1):
        published = art.published_at or ""
        blocks.append(
            f"[{idx}] Title: {art.title}\n"
            f"Source: {art.source} | Category: {art.category} | Published: {published}\n"
            f"Summary:\n{art.summary}\n"
        )
    return "\n\n".join(blocks)


# ---------- LLM backends ----------

def _call_openai(system_prompt: str, user_prompt: str) -> str:
    """Answer user queries by retrieving related summaries and generating a reply by openai."""
    if not OPENAI_API_KEY:
        return "OpenAI API key is not configured."

    try:
        response = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            temperature=0.3,
            max_tokens=400,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"[ChatAgent/OpenAI] Error: {e}")
        return "Sorry, something went wrong with OpenAI right now."


def _call_gemini(system_prompt: str, user_prompt: str) -> str:
    """Answer user queries by retrieving related summaries and generating a reply by openai."""
    if not GEMINI_API_KEY:
        return "Gemini API key is not configured."

    try:
        model = genai.GenerativeModel("gemini-2.5-flash-lite")
        response = model.generate_content(
            [
                {"role": "system", "parts": [system_prompt]},
                {"role": "user", "parts": [user_prompt]},
            ]
        )
        # For simple use, join all text parts:
        return response.text.strip()
    except Exception as e:
        print(f"[ChatAgent/Gemini] Error: {e}")
        return "Sorry, something went wrong with Gemini right now."


def _call_llm(provider: str, system_prompt: str, user_prompt: str) -> str:
    """Call llm, either Gemini or OpenAI"""
    provider = (provider or "openai").lower()
    if provider == "gemini":
        return _call_gemini(system_prompt, user_prompt)
    # default fallback
    return _call_openai(system_prompt, user_prompt)


# ---------- Public RAG entrypoint ----------

def answer_question(user, question: str, provider: str = "openai", top_k: int = 3):
    """
        RAG pipeline:
        1. Retrieve relevant article summaries via embeddings.
        2. Call chosen LLM (OpenAI or Gemini).
        3. Store chat history in DB.
        """
    relevant_articles = retrieve_relevant_articles(question, top_k=top_k)

    if relevant_articles:
        context = build_context_from_articles(relevant_articles)
        user_prompt = (
            f"User question:\n{question}\n\n"
            f"Here are relevant news summaries:\n{context}\n\n"
            "Using ONLY the information in these summaries, "
            "answer the user's question concisely. If the information is not covered, "
            "say that you don't know based on the available news."
        )
    else:
        user_prompt = (
            f"User question:\n{question}\n\n"
            "There are currently no relevant news summaries available in the database. "
            "Explain that you cannot answer based on the available data."
        )

    system_prompt = (
        "You are NewsMind, a helpful personal news assistant. "
        "You must base your answers ONLY on the article summaries provided to you. "
        "If the answer is not in the summaries, you must say you don't know."
    )

    answer = _call_llm(provider, system_prompt, user_prompt)

    # Store chat history
    now = datetime.utcnow()
    user_msg = ChatHistory(
        role="user",
        message=f"[{provider}] {question}",
        timestamp=now,
        user_id=user.id,
        article_id=None,
    )
    bot_msg = ChatHistory(
        role="bot",
        message=answer,
        timestamp=now,
        user_id=user.id,
        article_id=None,
    )

    db.session.add(user_msg)
    db.session.add(bot_msg)
    db.session.commit()

    return answer, relevant_articles
