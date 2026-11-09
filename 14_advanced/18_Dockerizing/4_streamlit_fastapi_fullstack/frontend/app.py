"""Frontend of the full-stack app: a Streamlit UI that only collects the
question and shows the answer - all the work happens in the FastAPI backend.

The one line that matters for Docker is BACKEND_URL. On your laptop the
backend is http://localhost:8000. Inside the frontend CONTAINER, localhost is
the frontend container itself, so docker-compose.yml sets
BACKEND_URL=http://backend:8000 - "backend" being the compose service name.

LOCAL RUN (no Docker), from this frontend/ folder, with the backend running:
    pip install -r requirements.txt
    streamlit run app.py
"""
import os

import requests
import streamlit as st

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")

st.set_page_config(page_title="Agentic AI App")
st.title("Agentic AI App")
st.caption(f"Streamlit → FastAPI ({BACKEND_URL}) → LLM")

q = st.text_input("Ask a question")

if st.button("Run"):
    if not q.strip():
        st.warning("Please enter a question.")
    else:
        with st.spinner("Thinking..."):
            try:
                r = requests.post(f"{BACKEND_URL}/ask", json={"query": q}, timeout=120)
                r.raise_for_status()
                st.write(r.json()["answer"])
            except requests.exceptions.ConnectionError:
                st.error(f"Backend not reachable at {BACKEND_URL}.")
            except requests.exceptions.RequestException as e:
                st.error(f"Backend error: {e}")
