# AI Assistant (Chatbot)

An AI assistant that can add meetings to Google Calendar, create Apple Notes, compose Gmail, learn from your documents, run scheduled tasks (daily words, quotes, book summaries, tech news), and accept text, voice, images, and files.

## Stack

- **Backend**: FastAPI, OpenAI (GPT-4, Whisper, embeddings), APScheduler, ChromaDB
- **Frontend**: Streamlit
- **Integrations**: Google Calendar, Gmail, Apple Notes (macOS), Reddit, optional Twitter/X

## Setup

1. **Clone and create virtual environment**

   ```bash
   cd "AI Agent"
   python3 -m venv .venv
   source .venv/bin/activate   # Windows: .venv\Scripts\activate
   pip install -r requirements.txt
   ```

2. **Environment variables**

   Copy `.env.example` to `.env` and set:

   - `OPENAI_API_KEY` – required for chat, embeddings, Whisper
   - For Google Calendar and Gmail: add OAuth credentials to `config/credentials.json` (from Google Cloud Console) and set `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `GOOGLE_REDIRECT_URI` if needed
   - Optional: `REDDIT_CLIENT_ID`, `REDDIT_CLIENT_SECRET`, `REDDIT_USER_AGENT` for Tuesday tech news; `TWITTER_BEARER_TOKEN` for Twitter tech news
   - Optional: `NOTIFICATION_EMAIL` for scheduled task delivery (daily words, quotes, book summary, tech news)

3. **Run backend and frontend**

   From project root, activate the virtual environment first, then run each app in its own terminal:

   ```bash
   source .venv/bin/activate   # Windows: .venv\Scripts\activate
   ```

   ```bash
   # Terminal 1 – backend
   python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload

   # Terminal 2 – frontend (with venv activated in this terminal too)
   streamlit run frontend/streamlit_app.py --server.port 8501
   ```

   Open http://localhost:8501 for the chat UI. API docs: http://localhost:8000/docs.

## Features

- **Chat**: Text and image input; function calling for calendar, notes, email, document search
- **Document learning**: Upload PDF, TXT, MD, DOCX via the file uploader; ask questions and get answers from your documents (RAG)
- **Voice**: Upload an audio file in the “Voice input” expander to transcribe with Whisper; use the text in chat
- **Scheduled tasks** (when backend is running):
  - 8:00 – 10 new words to learn
  - 11:00 – 5 inspiring quotes
  - Monday 9:00 – Book summary and key takeaways
  - Tuesday 9:00 – Tech news digest (AI agents, trends, startups; Reddit + optional Twitter)

Scheduled content is logged; if `NOTIFICATION_EMAIL` is set and Gmail is configured, it can be emailed.

## Project layout

- `backend/` – FastAPI app, task handlers, RAG, scheduler
- `frontend/` – Streamlit chat UI
- `config/` – Settings and (gitignored) Google credentials
- `data/` – Documents, embeddings, chat history

## Notes

- Apple Notes integration is macOS-only (AppleScript).
- Google Calendar and Gmail require OAuth; on first use you’ll be prompted to sign in.
- Tech news uses Reddit (and optionally Twitter) APIs; set the env vars above for full functionality.
