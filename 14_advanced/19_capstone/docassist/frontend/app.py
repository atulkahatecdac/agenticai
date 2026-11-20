# The chat UI. It only talks to the backend over HTTP: it never sees the
# OpenAI key or the database. Run locally from this folder:
#   streamlit run app.py --server.port 8522
import os
import uuid

import requests
import streamlit as st

# Locally: http://localhost:8022. In Docker Compose: http://backend:8000
BACKEND_URL = os.environ.get("BACKEND_URL", "http://localhost:8022")

st.set_page_config(page_title="DocAssist", page_icon="📄")
st.title("📄 DocAssist")

# The session id lives in the URL (?sid=...), so a page refresh - or a
# restart of every container - continues the same conversation.
if "sid" not in st.query_params:
    st.query_params["sid"] = uuid.uuid4().hex[:8]
session_id = st.query_params["sid"]

with st.sidebar:
    st.header("Documents")
    pdf = st.file_uploader("Add a PDF", type="pdf")
    if pdf and st.button("Add to knowledge base"):
        with st.spinner("Reading, chunking and embedding..."):
            r = requests.post(f"{BACKEND_URL}/documents",
                              files={"file": (pdf.name, pdf.getvalue())}, timeout=120)
        if r.ok:
            st.success(f"{r.json()['chunks']} chunks stored")
        else:
            st.error(r.text)
    docs = requests.get(f"{BACKEND_URL}/documents", timeout=10).json()["documents"]
    st.markdown("\n".join(f"- {d}" for d in docs) or "No documents yet")

    st.divider()
    st.caption(f"Conversation: {session_id}")
    if st.button("New conversation"):
        st.query_params["sid"] = uuid.uuid4().hex[:8]
        st.rerun()

# The history comes from Postgres (through the backend), not from Streamlit
history = requests.get(f"{BACKEND_URL}/history/{session_id}", timeout=10).json()["messages"]
for message in history:
    st.chat_message(message["role"]).write(message["content"])

if question := st.chat_input("Ask about your documents"):
    st.chat_message("user").write(question)
    with st.spinner("Thinking..."):
        r = requests.post(f"{BACKEND_URL}/chat",
                          json={"session_id": session_id, "question": question}, timeout=120)
    data = r.json()
    with st.chat_message("assistant"):
        st.write(data["reply"])
        if data["steps"]:
            st.caption("Agent: " + " · ".join(data["steps"]))
