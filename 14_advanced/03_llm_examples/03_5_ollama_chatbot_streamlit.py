# Run with: streamlit run 14_advanced/03_llm_examples/03_5_ollama_chatbot_streamlit.py
#
# Same Ollama chatbot as 03_4_ollama_chatbot.py, with a Streamlit UI instead of a
# terminal loop. Streamlit reruns this whole script on every interaction, so
# the conversation history lives in st.session_state instead of a plain list.

import streamlit as st
from openai import OpenAI

client = OpenAI(
    base_url="http://localhost:11434/v1",
    api_key="ollama"
)

st.title("Ollama Chatbot")

if "messages" not in st.session_state:
    st.session_state.messages = []

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.write(message["content"])

user_input = st.chat_input("Ask something")

if user_input:
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.write(user_input)

    response = client.chat.completions.create(
        model="qwen3:8b",
        messages=st.session_state.messages
    )
    reply = response.choices[0].message.content

    st.session_state.messages.append({"role": "assistant", "content": reply})
    with st.chat_message("assistant"):
        st.write(reply)
