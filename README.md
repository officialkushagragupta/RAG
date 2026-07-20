# RAG Document Chatbot

A single-document RAG chatbot: upload a PDF, ask natural-language questions
about it, and get grounded answers with rich, page/section-level citations.
Built for lightweight, free-tier-friendly deployment rather than
multi-tenant production scale.

## Features

- **PDF upload & indexing** — text and heading structure extracted via
  PyMuPDF, chunked, embedded, and stored in ChromaDB.
- **Grounded Q&A with citations** — answers are generated only from
  retrieved chunks; each citation carries document title, an ordered
  heading breadcrumb (e.g. *HR Policies → Leave Policy → Annual Leave*),
  page number, and a preview snippet — not just a bare page number.
- **Suggested questions** — 5 questions generated immediately after
  indexing, and 5 fresh contextual follow-ups after every answer, both via
  Gemini's structured JSON output (no free-text parsing).
- **Single active document** — no accounts, sessions, or persistence
  beyond the current process; uploading a new PDF replaces the previous
  one entirely (index, file, and chat history).

## Stack

| Layer         | Technology |
|---------------|------------|
| Backend       | FastAPI, Python 3.11 |
| LLM           | Gemini (`gemini-3.1-flash-lite`) |
| Embeddings    | Gemini (`gemini-embedding-001`, truncated to 768 dims) |
| Vector DB     | ChromaDB (persistent, embedded, single collection) |
| Orchestration | LangChain (text splitting), `google-generativeai` (LLM/embeddings) |
| PDF parsing   | PyMuPDF |
| Frontend      | Streamlit |
| Packaging     | Docker, docker-compose |

## Architecture

**Single active document, no sessions.** There is no `session_id`
anywhere in the API or the code — state is process-global, not scoped to
a user or session. This keeps the whole system simple: no accounts, no
database, no Redis, just a running process holding one document's index
and conversation at a time.

**Uploading a new PDF always replaces the previous one:**
1. The existing Chroma collection is deleted.
2. The previous uploaded file is removed from disk.
3. The chat history is cleared.
4. The new PDF is parsed, chunked, embedded, and indexed.
5. 5 new suggested questions are generated.

Chat history lives in memory only (`DocumentStateService`) for the
lifetime of the running backend process — it does not survive a restart,
and that's intentional: it keeps the app lightweight and deployable on
free hosting tiers with no database dependency.

### Folder structure

```
rag/
├── backend/
│   ├── app/
│   │   ├── api/            # FastAPI route handlers (document, chat, health)
│   │   ├── services/       # Business logic: PDF, chunking, embeddings,
│   │   │                   #   vector store, RAG, LLM, questions, state
│   │   ├── models/         # Pydantic request/response schemas
│   │   ├── core/           # Config, prompts, Chroma/Gemini client wiring, exceptions
│   │   ├── middleware/     # Request logging
│   │   ├── utils/          # Logging setup, constants, input validators
│   │   └── main.py         # App factory, lifespan checks, CORS, routers
│   ├── uploads/            # Active PDF (gitignored, volume-mounted)
│   ├── chroma_db/          # ChromaDB storage, collection "document_rag" (gitignored, volume-mounted)
│   ├── logs/                # Rotating log files (gitignored, volume-mounted)
│   ├── requirements.txt
│   ├── .env.example
│   └── Dockerfile
│
├── frontend/
│   ├── app.py               # Streamlit entry point: page config, CSS, routing
│   ├── views/                # Top-level screens: upload_view.py, chat_view.py
│   ├── components/           # sidebar, chat_window, uploader, citation,
│   │                         #   suggested_questions, error_banner, header
│   ├── services/              # api_client.py -- HTTP client for the backend REST API
│   ├── core/                   # Frontend config (backend URL, timeouts, display labels)
│   ├── utils/                   # Constants + formatting helpers
│   ├── assets/                   # custom.css, logo/favicon
│   ├── .streamlit/config.toml
│   ├── requirements.txt
│   ├── .env.example
│   └── Dockerfile
│
├── docker-compose.yml
├── .gitignore
└── README.md
```

## API reference

All routes are under `API_V1_PREFIX` (default `/api/v1`), except `/health`.

| Method | Path              | Description |
|--------|-------------------|-------------|
| POST   | `/document`       | Upload a PDF; replaces the active document and returns `{filename, pages, chunks, status, suggested_questions}` in one call. |
| GET    | `/document`       | Return the active document's info, or `null`. |
| DELETE | `/document`       | Clear the active document, its index, and its chat history. |
| POST   | `/chat`           | Ask a question; returns `{answer, citations, suggested_questions, debug?}`. |
| GET    | `/chat/history`   | Return the full conversation history. |
| DELETE | `/chat/history`   | Clear only the chat history — the document and its index are untouched. |
| GET    | `/health`          | Liveness + live Gemini/ChromaDB connectivity check. |

Interactive docs are available at `http://localhost:8000/docs` once the
backend is running.

## Getting started

### 1. Configure environment variables

```bash
cp backend/.env.example backend/.env      # then set GEMINI_API_KEY
cp frontend/.env.example frontend/.env
```

See [Configuration](#configuration) below for what each variable does.

### 2. Run with Docker (recommended)

```bash
docker compose up --build
```

- Backend: http://localhost:8000 (docs at `/docs`, health at `/health`)
- Frontend: http://localhost:8501

### 3. Run locally without Docker

```bash
# Backend
cd backend
python -m venv venv && venv\Scripts\activate   # Windows
pip install -r requirements.txt
uvicorn app.main:app --reload

# Frontend (separate terminal)
cd frontend
python -m venv venv && venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
```

Run `streamlit run app.py`, not `python app.py` — the latter runs
Streamlit in "bare mode" with no session context and no server.

## Configuration

Key backend (`backend/.env`) settings:

| Variable | Default | Notes |
|---|---|---|
| `GEMINI_API_KEY` | *(required)* | Startup fails fast if missing/invalid. |
| `GEMINI_MODEL_NAME` | `gemini-3.1-flash-lite` | Any current Gemini model your API key has access to. |
| `EMBEDDING_MODEL_NAME` | `models/gemini-embedding-001` | |
| `EMBEDDING_DIMENSION` | `768` | Truncated via Matryoshka representation learning (native size is 3072; 1536/768 are Google's validated smaller sizes). Smaller = less ChromaDB storage/RAM — chosen for free-tier hosting. Query and document embeddings must always use the same dimension. |
| `MAX_UPLOAD_SIZE_MB` | `20` | |
| `ALLOWED_FILE_EXTENSIONS` / `ALLOWED_MIME_TYPES` | `.pdf` / `application/pdf` | |
| `CHUNK_SIZE` / `CHUNK_OVERLAP` | `1000` / `200` | Passed to LangChain's `RecursiveCharacterTextSplitter`. |
| `MAX_CHAT_HISTORY_TURNS` | `10` | Bounds in-memory chat history. |
| `ENABLE_DEBUG_METADATA` | `false` | When `true`, `POST /chat` includes a `debug` block (retrieved chunk count + similarity scores) for tuning retrieval quality. Must stay `false` in production. |
| `CORS_ORIGINS` | `http://localhost:8501` | Comma-separated, or `*`. |

Frontend (`frontend/.env`) settings mostly mirror the backend for display
purposes and client-side hints only — the backend is always the source of
truth and re-validates everything server-side.

## Frontend notes

- **`views/`, not `pages/`.** Screens live in `frontend/views/`
  (`upload_view.py`, `chat_view.py`) rather than a directory literally
  named `pages/`, because Streamlit auto-detects a `pages/` folder next
  to the entry script and injects its own multipage navigation — which
  would fight the custom sidebar and doesn't fit here anyway (the app
  switches between upload/chat automatically based on state, it's not
  user-driven page navigation). `app.py` calls each view's `render()`
  directly.
- **No emoji, no default Streamlit look.** The UI follows an editorial
  black/cream visual theme (`assets/custom.css`, `.streamlit/config.toml`)
  with a logo mark and matching favicon, plain text labels instead of
  emoji icons, and Streamlit's default alert/button styling overridden
  throughout.
- **Errors never show a raw traceback.** `services/api_client.py` wraps
  every backend call in `BackendAPIError` (with a `kind` and
  `status_code`); `components/error_banner.py` maps that to a friendly
  message. `app.py` also wraps the whole render in a last-resort
  try/except, and `.streamlit/config.toml` sets `showErrorDetails =
  "none"` as a final backstop — full tracebacks always still print to the
  terminal running `streamlit run`, just never to the browser.
- **"Clear Chat" vs "Clear Current Document."** Clear Chat calls `DELETE
  /chat/history` (keeps the document and its index); Clear Current
  Document calls `DELETE /document` (wipes everything). They are
  deliberately separate controls.
