# 02_fastapi_production – FastAPI the way real services are laid out

Module 02 builds single-file FastAPI apps. This folder shows the same ideas arranged the way a team would
maintain them: routers, dependency injection, file uploads, tests, and Streamlit caching.

**Start with `simple_main.py`**: the whole API in one file (a Pydantic model and a `.txt`
upload). The `app/` folder is the same API split up the way it grows in a real project.

| File | What it shows |
|---|---|
| `simple_main.py` | Step 1 – one file: `/health`, `POST /chat`, `POST /summarize` (`.txt` upload) |
| `app/main.py` | Only wiring: `include_router(...)`, `/health` |
| `app/config.py` | Settings read once from `.env` (`APP_MODEL`, `APP_MAX_UPLOAD_MB`) |
| `app/dependencies.py` | `get_llm` (one shared LLM client, passed in with `Depends()`) |
| `app/routers/chat.py` | `POST /chat` and `POST /chat/stream` (Server-Sent Events) |
| `app/routers/documents.py` | `POST /documents/summarize` – a `.txt`/`.pdf` upload (`UploadFile`), type and size checks |
| `test_api.py` | *Optional, not covered in the intro session.* 6 pytest tests; `app.dependency_overrides` swaps in a fake LLM, so no OpenAI key is needed. Testing comes back in modules 07 (`07_7`) and 18 (CI) |
| `frontend.py` | Streamlit uploader using `st.cache_resource` (one HTTP client) and `st.cache_data` (no repeat LLM call) |

## Run

```bash
cd 14_advanced/02_fastapi_production
uvicorn simple_main:app --reload      # step 1 – http://localhost:8000/docs
pytest -q test_api.py                 # optional – offline, 6 passed
uvicorn app.main:app --reload         # http://localhost:8000/docs
streamlit run frontend.py             # second terminal
```
