# RAG Document Chatbot

A lightweight Document RAG Chatbot: upload a PDF, ask questions, get
answers with source citations, plus AI-suggested and follow-up questions.

> **Status:** the **frontend is fully implemented** and consumes the
> backend's REST contract as-is. The **backend's actual RAG logic is
> not implemented yet** -- PDF parsing, chunking, embedding, retrieval,
> answer generation, and question generation are all stubs (see the
> `TODO` / `NotImplementedError` markers throughout `backend/app/services`
> and `backend/app/api`). Until those are implemented, every backend call
> from the UI will error -- the frontend's error handling (see "Frontend"
> below) is what you'll see in the meantime, which is expected.

## Stack

| Layer      | Technology |
|------------|------------|
| Backend    | FastAPI, Python 3.11 |
| LLM        | Gemini (`gemini-3.1-flash-lite`) |
| Embeddings | Google `gemini-embedding-001` |
| Vector DB  | ChromaDB (persistent, embedded, single collection) |
| Orchestration | LangChain |
| PDF parsing | PyMuPDF |
| Frontend   | Streamlit |
| Packaging  | Docker, docker-compose |

## Architecture Constraints

This application is intentionally designed for a **single active document**.

Not implemented, by design:
- Multi-session support
- Multiple concurrent documents
- User authentication
- Database persistence for chat history
- Redis
- SQL databases

Behavior:
- Only one document can be active at a time.
- When a new PDF is uploaded:
  1. The existing Chroma collection is deleted.
  2. The previous uploaded PDF file is removed.
  3. The existing chat history is cleared.
  4. A new vector index is generated for the new PDF.
  5. 5 new recommended questions are generated.
- Chat history is maintained only for the currently active document.
- Chat history is stored in memory on the backend (or in Streamlit
  `session_state` on the frontend) for the duration of the running
  process -- there is no database or cache backing it, and it does not
  survive a restart. That's intentional.

This design keeps the application lightweight and suitable for free-tier
deployment.

## Folder structure

```
rag/
├── backend/
│   ├── app/
│   │   ├── api/             # FastAPI route handlers (document, chat, health)
│   │   ├── services/        # Business logic (PDF/chunk/embedding/vector/rag/llm/question/state) -- stubs
│   │   ├── models/          # Pydantic request/response schemas (the API's data contract)
│   │   ├── core/             # Config, prompts, Chroma/Gemini client wiring, custom exceptions
│   │   ├── middleware/        # Request logging middleware
│   │   ├── utils/              # Logging setup, fixed constants, input validators
│   │   └── main.py              # App factory, lifespan (startup/shutdown) checks, CORS, routers
│   ├── uploads/               # Temp storage for the single active PDF (gitignored, volume-mounted)
│   ├── chroma_db/              # ChromaDB persistent storage, one collection "document_rag" (gitignored, volume-mounted)
│   ├── logs/                    # Rotating log files (gitignored, volume-mounted)
│   ├── requirements.txt
│   ├── .env.example
│   └── Dockerfile
│
├── frontend/
│   ├── app.py                 # Streamlit entry point: page config, CSS, session state, routing
│   ├── views/                   # Top-level screens: upload_view.py, chat_view.py (see "Frontend" below)
│   ├── components/               # Reusable UI pieces: sidebar, chat_window, uploader, citation,
│   │                              # suggested_questions, error_banner
│   ├── services/                  # api_client.py -- HTTP client wrapping the backend REST API
│   ├── core/                       # Frontend config (backend URL, timeouts, model display labels)
│   ├── utils/                       # Fixed UI constants + formatting helpers
│   ├── assets/custom.css
│   ├── .streamlit/config.toml
│   ├── requirements.txt
│   ├── .env.example
│   └── Dockerfile
│
├── docker-compose.yml
├── .gitignore
└── README.md
```

## Design notes

- **Single active document, no sessions.** There is no `session_id`
  anywhere in the API. `POST /api/v1/document` uploads a PDF and always
  replaces whatever was previously active. `GET /api/v1/document` returns
  the current one (or `null`). `DELETE /api/v1/document` clears it (and
  its index and history) without requiring a new upload. That's the
  entire surface the frontend needs: `POST /document`, `GET /document`
  (optional, on refresh), `POST /chat`, `DELETE /document`.
- **Flat, self-contained responses -- no follow-up calls.** `POST
  /api/v1/document` returns `{filename, pages, chunks, status,
  suggested_questions}` in one shot, so the UI can immediately show the
  uploaded file, page/chunk counts, and 5 suggested questions without a
  second request. `POST /api/v1/chat` likewise returns `{answer,
  citations, suggested_questions}` -- and `suggested_questions` is 5
  fresh contextual follow-ups generated right after the answer. See
  `models/schemas.py` (`DocumentInfo`, `ChatResponse`, `Citation`) for the
  exact shapes.
- **Citations carry rich metadata, not just a page number.** Each
  `Citation` is `{filename, document_title, hierarchy, page, chunk_id,
  chunk_index, total_chunks, char_start, char_end, text}`, where
  `hierarchy` is an ordered heading breadcrumb (e.g. `["HR Policies",
  "Leave Policy", "Annual Leave"]`, outermost first), not a single
  section title. `ChunkService` is expected to derive it by walking
  PDFService's detected headings with a level-aware stack, and
  `RAGService` passes both chunk text *and* this metadata into the answer
  prompt -- not just raw text -- so the model has document/section
  context and the frontend can render references like "Employee Handbook
  → HR Policies → Leave Policy → Annual Leave (Page 12)" instead of a
  bare page number. Chroma metadata values must be primitives, so
  `hierarchy` needs serializing (e.g. `" > ".join(...)`) on write and
  parsing back out on read -- see `VectorService`.
- **Chat is scoped to the active document.** `POST /api/v1/chat` answers
  against whatever's currently indexed; `GET /api/v1/chat/history` returns
  the in-memory conversation so far, and `DELETE /api/v1/chat/history`
  clears just the conversation -- keeping the document, its Chroma
  collection, and its uploaded file untouched (unlike `DELETE
  /api/v1/document`, which clears everything). All of it is wiped the
  moment a new PDF is uploaded.
- **Debug retrieval diagnostics, gated by a flag.** When
  `Settings.ENABLE_DEBUG_METADATA` (env `ENABLE_DEBUG_METADATA`, default
  `false`) is true, `POST /api/v1/chat` additionally returns `debug:
  {retrieved_chunks, similarity_scores}` -- useful while tuning
  `CHUNK_SIZE`/`CHUNK_OVERLAP`/retrieval quality. Must stay `false` in
  production; see `models/schemas.ChatDebugInfo`.
- **Synchronous upload.** `POST /api/v1/document` blocks until parsing,
  chunking, embedding, and indexing finish, then returns the document
  info plus 5 suggested questions in one response.
- **Suggested questions use Gemini structured output, not free-text
  parsing.** `QuestionService` is expected to call
  `LLMService.generate_structured()` with `GenerationConfig(
  response_mime_type="application/json", response_schema=...)` (see
  `core/prompts.SUGGESTED_QUESTIONS_RESPONSE_SCHEMA`), so
  `suggested_questions` is always a clean JSON array of strings -- no
  regex/markdown-fence stripping of a free-form completion.
- **Upload validation is real, not stubbed.** Extension, MIME type, and
  size-limit checks (`app/utils/validators.py`) run before anything is
  processed. Limits and allowed types are environment-configurable
  (`MAX_UPLOAD_SIZE_MB`, `ALLOWED_FILE_EXTENSIONS`, `ALLOWED_MIME_TYPES` in
  `backend/.env`), defaulting to PDF-only, 20 MB.
- **Startup fails fast.** `main.py`'s lifespan handler verifies Gemini
  credentials and the ChromaDB connection before the app accepts traffic;
  either failure aborts startup. `GET /health` re-checks both live for
  ongoing monitoring.

## Frontend

The Streamlit UI in `frontend/` is **fully implemented** against the
backend's REST contract above -- it does not implement or assume any
backend logic itself.

- **`views/`, not `pages/`.** The spec called for an `app.py` /
  `components/` / `services/` / `core/` / `utils/` layout with page-level
  modules. Those live in `frontend/views/` (`upload_view.py`,
  `chat_view.py`) rather than a directory literally named `pages/`,
  because Streamlit auto-detects any `pages/` folder next to the entry
  script and injects its own multipage sidebar navigation -- which would
  both fight the custom sidebar design and be semantically wrong here
  (this app transitions between "upload" and "chat" automatically based
  on whether a document is active, it's not user-driven page navigation).
  `app.py` picks a view each rerun by calling its `render()` function directly.
- **State lives in `st.session_state`, not the URL or a backend session.**
  Active document, chat history, and the current suggested-question chips
  are all `session_state` keys (`utils/constants.py`), matching the
  backend's "no sessions" design. `services/api_client.py` is the only
  module that talks HTTP; every component/view goes through it.
- **"Clear Chat" calls `DELETE /api/v1/chat/history`.** The chat window's
  Clear Chat control (`components/chat_window.py`) hits the dedicated
  endpoint and swaps in the `suggested_questions` it returns (the
  document's original, upload-time suggestions) -- it does not touch the
  active document, its index, or its uploaded file.
- **Upload progress is simulated.** `POST /document` is one synchronous
  backend call, so "Extracting text... / Creating embeddings... /
  Indexing document..." (`components/uploader.py`) is a cosmetic sequence
  around that single request, not real progress events. Streamlit blocks
  on the same script run while the request is in flight, so the rest of
  the UI is naturally non-interactive until it completes.
- **Auto-scroll is a best-effort DOM hack.** Streamlit has no native
  auto-scroll API; `components/chat_window.py` uses a small embedded-iframe
  script reaching into the parent document (`window.parent.document`), a
  common community workaround. It targets Streamlit's internal `.main`
  class, which may need adjusting across Streamlit versions.
- **Errors are mapped to friendly messages**, not raw exceptions:
  `services/api_client.BackendAPIError` carries a `kind`
  (`timeout`/`unavailable`/`http_error`) and `status_code`;
  `components/error_banner.py` maps those to the "No document uploaded" /
  "Upload failed" / "Assistant unavailable" / "Backend unavailable" /
  "Request timed out" messages, with raw details in a collapsed expander.

## Implementation Notes

- Use a single Chroma collection named `document_rag`
  (`Settings.CHROMA_COLLECTION_NAME`).
- Keep all business logic inside the service layer (`app/services/*`) --
  API handlers stay thin, validating input and delegating.
- Use Gemini's JSON/structured output mode for `suggested_questions`
  (`GenerationConfig(response_mime_type="application/json",
  response_schema=...)`, or LangChain's `with_structured_output`) instead
  of parsing free-form text -- see `core/prompts.py`.
- Do not modify the architecture described above (folder structure,
  config/logging/health/CORS setup, single-document model) beyond what a
  feature genuinely requires.
- Build a clean MVP focused on readability and maintainability.
- Optimize for interview evaluation rather than production-scale
  features -- no need to over-engineer for concurrency, multi-tenancy, or
  horizontal scaling.

## Getting started

### 1. Configure environment variables

```bash
cp backend/.env.example backend/.env      # then set GEMINI_API_KEY
cp frontend/.env.example frontend/.env
```

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
python -m venv .venv && .venv\Scripts\activate   # Windows
pip install -r requirements.txt
uvicorn app.main:app --reload

# Frontend (separate terminal)
cd frontend
python -m venv .venv && .venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
```

## Next steps (not yet implemented)

- `PDFService`, `ChunkService`, `EmbeddingService`, `VectorService` -- the indexing pipeline, including rich chunk metadata (document title, heading hierarchy, char offsets)
- `RAGService`, `LLMService` -- retrieval + grounded answer generation, prompting with chunk metadata, and (when `ENABLE_DEBUG_METADATA=true`) surfacing retrieval diagnostics
- `QuestionService` -- recommended and follow-up question generation via Gemini structured output
- `DocumentStateService` -- in-memory active-document + chat-history store, including `clear_history()` for `DELETE /chat/history`
