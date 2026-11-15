# 02_fastapi_production – FastAPI the way real services are laid out

Module 02 builds single-file FastAPI apps. This folder shows the same ideas arranged the way a team would
maintain them: routers, dependency injection, file uploads, tests, and Streamlit caching.

**Start with `simple_main.py`**: the whole API in one file (a Pydantic model, a `Depends()` key check, a `.txt`
upload). The `app/` folder is the same API split up the way it grows in a real project.

| File | What it shows |
|---|---|
| `simple_main.py` | Step 1 – one file: `/health`, `POST /chat`, `POST /summarize` (`.txt` upload, needs `X-API-Key`) |
| `app/main.py` | Only wiring: `include_router(...)`, `/health` |
| `app/config.py` | Settings read once from `.env` (`APP_MODEL`, `APP_API_KEY`, `APP_MAX_UPLOAD_MB`) |
| `app/dependencies.py` | `get_llm` (one shared LLM client) and `require_api_key` (checks the `X-API-Key` header) |
| `app/routers/chat.py` | `POST /chat` and `POST /chat/stream` (Server-Sent Events) |
| `app/routers/documents.py` | `POST /documents/summarize` – a `.txt`/`.pdf` upload (`UploadFile`), type and size checks |
| `test_api.py` | 7 pytest tests; `app.dependency_overrides` swaps in a fake LLM, so no key is needed |
| `frontend.py` | Streamlit uploader using `st.cache_resource` (one HTTP client) and `st.cache_data` (no repeat LLM call) |

## Run

```bash
cd 14_advanced/02_fastapi_production
uvicorn simple_main:app --reload      # step 1 – http://localhost:8000/docs
pytest -q test_api.py                 # offline – 7 passed
uvicorn app.main:app --reload         # http://localhost:8000/docs
streamlit run frontend.py             # second terminal
```

`/documents` needs the `X-API-Key` header. Its value is `APP_API_KEY` from `.env` (default `dev-key-change-me`);
it protects your API and is not your OpenAI key. In Swagger UI (`/docs`) the endpoint shows an `x-api-key` field to fill in.
