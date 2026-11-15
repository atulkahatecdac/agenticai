"""Streamlit front end for the Agent API, showing Streamlit's two caches.

Start the API first (uvicorn app.main:app), then:
    streamlit run frontend.py

Streamlit re-runs this whole script on every click. Without caching, every re-run would
open a new HTTP client and re-send the same file to the LLM - slow and billed per call.
"""
import os

import httpx
import streamlit as st
from dotenv import load_dotenv

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(BASE_DIR, "..", "..", ".env"), override=True)
API = os.getenv("AGENT_API_URL", "http://localhost:8000")
API_KEY = os.getenv("APP_API_KEY", "dev-key-change-me")
KEY = {"X-API-Key": API_KEY}


@st.cache_resource          # ONE shared object for every re-run and every user: clients, models, DB connections
def get_client() -> httpx.Client:
    return httpx.Client(base_url=API, timeout=60)


@st.cache_data(ttl=3600, show_spinner="Summarising…")   # results, keyed by the arguments: same file -> no new LLM call
def summarise(filename: str, data: bytes, content_type: str) -> dict:
    files = {"file": (filename, data, content_type)}
    r = get_client().post("/documents/summarize", files=files, headers=KEY)
    r.raise_for_status()
    return r.json()


st.title("Document summariser")
upload = st.file_uploader("Upload a .txt or .pdf file", type=["txt", "pdf"])
if upload:
    result = summarise(upload.name, upload.getvalue(), upload.type)
    st.caption(f"{result['filename']} – {result['characters']:,} characters")
    st.markdown(result["summary"])
    st.info("Click the button: the script re-runs, but the summary comes from st.cache_data – no new LLM call.")
    st.button("Re-run the script")
