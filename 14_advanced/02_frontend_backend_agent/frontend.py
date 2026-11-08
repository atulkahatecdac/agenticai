"""frontend.py - Streamlit UI. It only collects the question and shows the answer;
all the work happens in the FastAPI back end.

Run (terminal 2, from this folder, after the backend is up):
    streamlit run frontend.py
Then open http://localhost:8501
"""
import requests
import streamlit as st

BACKEND_URL = "http://127.0.0.1:8000/ask"

st.title("Agentic AI App")
st.caption("Streamlit → FastAPI → LangChain agent (with web search)")

q = st.text_input("Ask...")

if st.button("Run"):
    if not q.strip():
        st.warning("Please enter a question.")
    else:
        with st.spinner("The agent is thinking..."):
            try:
                r = requests.post(BACKEND_URL, json={"query": q}, timeout=120)
                r.raise_for_status()
                st.write(r.json()["answer"])
            except requests.exceptions.ConnectionError:
                st.error("Backend not reachable - start it first: uvicorn backend:app --reload --port 8000")
            except requests.exceptions.RequestException as e:
                st.error(f"Backend error: {e}")
