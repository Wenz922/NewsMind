# NewsMind: Personalized Conversational News Assistant
**NewsMind** is a small end-to-end full-stack AI engineering demo that:

- Fetches fresh news from **NewsAPI**
- Extracts full article text using **Newspaper3k**
- Summarizes content with **LLMs (OpenAI, Gemini)**
- Generates **embeddings** for semantic search using `sentence-transformers`
- Analyzes **sentiment** of each article
- Lets users **interact with generated summaries**, like / view / open / note / ranking
- Provides a **RAG-based chatbot** to answer questions about the user’s news

The stack is **Flask + SQLite + SQLAlchemy**, with a web UI for registration, topic selection, digest, article view and chat.

---

## Features

### User & Topics
- User registration & login
- Per-user:
  - `preferred_language` (`en`, `zh`, `es`, `de`, `fr`)
  - `interests` (topics: `technology`, `science`, `business`, `politics`, `sports`, `health`, `world`, `entertainment`, `lifestyle`)

### News Digest
- Fetch news via **NewsAPI** per user-selected topics
- Extract full text using **Newspaper3k**
- Summarize each article into **2-3 bullet points** using **OpenAI**
- Store in `Article`:
  - `title`, `author`, `source`, `url`
  - `category` (topic)
  - `published_at`, `fetched_at`
  - `summary`
  - `embedding` (JSON list of floats)
  - `sentiment` (`positive`, `neutral`, `negative`)
- Route `/digest` shows latest summarized articles per topic.

### User–Article Interactions
- Stored in `UserArticle`:
  - `action` = JSON list of:
    - `"viewed"` (user opened full article)
    - `"liked"` (user clicked like)
    - `"linked"` (user opened original URL)
  - `rating` (1–10)
  - `notes`
  - `timestamp` (last change)

### RAG Chatbot
- Route `/chat`:
  - User asks questions
  - System embeds question and finds most relevant articles via cosine similarity
  - Builds context from article summaries
  - Calls selected LLM:
    - **OpenAI** (default, `gpt-4o-mini`)
    - **Gemini** (optional, `gemini-2.5-flash-lite`)
  - Answers **based on retrieved summaries** (RAG)
  - Logs conversation stored in `ChatHistory`

### LLM Selector
- In the chat UI the user can choose:
  - `OpenAI`
  - `Gemini`
- Choice is saved in the Flask session and reused.

### Logging
- Python `logging` writes to `logs/newsmind.log`
- Logs:
  - visits (home, register, digest, refresh, chat)
  - registrations, logins, logouts
  - topic selection
  - refresh actions & counts
  - article interactions (viewed, liked, linked)
  - chatbot activity and errors

---

## Installation

1. **Clone this repository**
   ```bash
   git clone https://github.com/Wenz922/NewsMind.git
   cd NewsMind
2. **Create and activate a virtual environment (example: Python 3.9+)**
   ```bash
   python -m venv venv
   source venv/bin/activate  # macOS/Linux
   venv\Scripts\activate  # Windows
3. **Install dependencies**
   ```bash
   pip3 install -r requirements.txt
4. **Create an `.env` file in the project root:**
   ```bash
   # Flask secret key
   SECRET_KEY='your_secret_key_here'
   
   # NewsAPI API key
   NEWSAPI_KEY='your_newsapi_key_here'
   
   # OpenAI API key
   OPENAI_API_KEY='your_openai_key_here'
   
   # Gemini API key
   GEMINI_API_KEY='your_gemini_api_key'

---

## Usage

### Database Setup
- On first run, `app.py will create the database automatically:
   ```bash
   python app.py
- It will create database: **users, articles, user_articles, chat_history** and **statistics**

### Running the App
- Run the web app (Flask)
   ```bash
   flask run
- Open in your browser
   ```bash
   http://127.0.0.1:5000

### Web Flow
1. **Open Home** - Go to `/` and click to register.
2. **Register an account** - Choose username, email, password, language.
3. **Login** - Login with your new account.
4. **Select topics** - Choose common topics (e.g. `Technology`, `Business`, `Science`, etc).
5. **Refresh news** - `/refresh` shows a loading screen,
   for each topic:
   - Fetch metadata from NewsAPI
   - Extract full text via Newspaper3k
   - Summarize with OpenAI
   - Analyze sentiment
   - Generate embeddings
   - Save into `articles`
6. **View digest** - `/digest` shows recent summaries per topic.
7. **Interact with articles** - You can do followings, these actions are stored in `user_articles`
   - Like (`"liked"`)
   - Open the full context (`"viewed"`) by `/article/<id>`
   - Open original URL (`"linked"`)
   - Rate (1–10)
   - Add notes
8. **Chat with NewsMind** - `/chat`:
   - Choose LLM: OpenAI or Gemini
   - Ask questions like “What happened in AI this week?”
   - System retrieves top relevant article summaries using embeddings.
   - LLM answers based only on those summaries (RAG).
   - Conversation is saved in `chat_history`.

### LLM Backends
- OpenAI (default)
  - Uses `openai` Python client.
  - Model: `gpt-4o-mini` (configurable in `summarizer.py` and `chat_agent.py`).
- Gemini (optional)
  - Uses google-generativeai.
  - Model: `gemini-2.5-flash-lite`.

### Embeddings & Retrieval
- Embeddings are generated using `SentenceTransformer("all-MiniLM-L6-v2")`
- Stored as JSON lists in `Article.embedding`
- Retrieval pipeline (**RAG chatbot**)
  - Embed user query
  - Compute cosine similarity between query embedding and each article embedding
  - Select top-k (e.g., 3) articles
  - Build context from summaries
  - Send context + question to LLM

### Testing Notes
- If Newspaper3k fails on some URLs or text is too short:
  - The fetcher logs it and skips those articles.
- If LLM API keys are missing or invalid:
  - Summarization and chat will return fallback error messages.
- If Gemini quota is 0:
  - 429 error in logs; you can either fix quota on Google side, or use only OpenAI for now.

---

## Project Structure

    NewsMind/
    ├── app.py                  # Flask web application
    ├── models.py               # Database models (User, Article, etc.)
    ├── modules/
    │   ├── news_fetcher.py     # Fetches news and extracts full content
    │   ├── summarizer.py       # Summarizes articles using OpenAI
    │   ├── embedding_manager.py# Creates vector embeddings
    │   ├── chat_agent.py       # Retrieves and answers user queries
    ├── templates/
    │   ├── base.html
    │   ├── index.html
    │   ├── register.html
    │   ├── select_topics.html
    │   ├── digest.html
    │   ├── article.html
    │   └── chat.html
    ├── static/
    │   └── styles.css
    ├── data/
    │   └── newsmind.sqlite     # SQLite database
    ├── logs/
    │   └── newsmind.log
    ├── .env                    # Environment variables
    ├── requirements.txt
    └── README.md

---

## Database Design
**Table:** `users`

| Field              | Type     | Description                  |
| ------------------ | -------- | ---------------------------- |
| id                 | Integer  | Primary key                  |
| username           | String   | Unique user name             |
| email              | String   | User email                   |
| password_hash      | String   | Hashed password              |
| preferred_language | String   | `en`, `zh`, `es`, `de`, `fr` |
| interests          | String   | Comma-separated topics       |
| created_at         | DateTime | Registration timestamp       |
| last_login         | DateTime | Last login time              |

**Table:** `articles`

| Field        | Type     | Description              |
| ------------ | -------- | ------------------------ |
| id           | Integer  | Primary key              |
| title        | String   | Article title            |
| author       | String   | Author name              |
| source       | String   | News source              |
| url          | String   | Article URL              |
| category     | String   | Topic keyword            |
| published_at | String   | Publication date         |
| fetched_at   | DateTime | When it was added        |
| summary      | Text     | LLM-generated summary    |
| embedding    | Text     | Vector embedding (JSON)  |
| sentiment    | String   | Sentiment score          |

**Table:** `user_articles`

| Field        | Type     | Description                  |
| ------------ | -------- | ---------------------------- |
| id           | Integer  | Primary key                  |
| action       | Text     | `liked`, `viewed`, `linked`  |
| rating       | Integer  | User adds 1-10 score         |
| notes        | Text     | User adds notes              |
| timestamp    | DateTime | Changing time                |
| user_id      | Integer  | Foreign key to User          |
| article_id   | Integer  | Foreign key to Article       |

**Table:** `chat_history`

| Field        | Type     | Description              |
| ------------ | -------- | ------------------------ |
| id           | Integer  | Primary key              |
| role         | String   | `user`, `bot`            |
| message      | Text     | Chatting messages        |
| timestamp    | DateTime | Messaging time           |
| user_id      | Integer  | Foreign key to User      |
| article_id   | Integer  | Foreign key to Article   |

**Table:** `statistics`

| Field          | Type     | Description              |
| -------------- | -------- | ------------------------ |
| id             | Integer  | Primary key              |
| topic          | String   | mentioned topics         |
| sentiment_avg  | Float    | Sentiment on average     |
| mention_count  | Integer  | Sum of mentioned topics  |
| date           | DateTime | Statistic time           |

---

## Supported Languages
| Code | Language         |
| ---- | ---------------- |
| `en` | English          |
| `zh` | Mandarin Chinese |
| `es` | Spanish          |
| `de` | German           |
| `fr` | French           |


---

## Further Development
- `main.py` for CLI interface
- Saving full context article instead of only summary in Database for precise usage of personalized RAG
- Per-user personalization of retrieval based on `UserArticle` actions.
- “My Activity” page summarizing viewed / liked / linked articles on `Statistics`.
- Sentiment-based filters in digest (e.g., “Only positive tech news”).
- Multi-language support for summaries + chat.
- Deployment to a server (e.g., Gunicorn + Nginx).

---

## License
- This is a personal / learning project.
- MIT License © 2026 Wenzheng Cai
