# pip install flask pandas python-dotenv langgraph langchain-community langchain-huggingface requests langchain-google-genai

import os
import requests
import pandas as pd
from flask import Flask, request, render_template_string
from typing import TypedDict
from dotenv import load_dotenv
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from langgraph.graph import StateGraph, END
from langchain_community.vectorstores import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_google_genai import ChatGoogleGenerativeAI

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# -------------------------------
# Setup
# -------------------------------
load_dotenv()

app = Flask(__name__)

class ChatState(TypedDict):
    query: str
    answer: str

# -------------------------------
# Data / Vector DB
# -------------------------------
data_path = os.path.join(BASE_DIR, "Dataset_banking_chatbot.csv")
df = pd.read_csv(data_path, encoding="latin-1")

texts = df["Query"].astype(str).tolist()
metadatas = df[["Response"]].to_dict(orient="records")

embeddings = HuggingFaceEmbeddings(
    model_name="sentence-transformers/all-MiniLM-L6-v2"
)

llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash",
    temperature=0
)

vectordb = Chroma(
    persist_directory=os.path.join(BASE_DIR, "banking_chromadb"),
    embedding_function=embeddings,
    collection_name="banking_faqs"
)

if vectordb._collection.count() == 0:
    vectordb.add_texts(texts=texts, metadatas=metadatas)
    vectordb.persist()

# -------------------------------
# Notifications
# -------------------------------
# Created a new topic in notify.sh named atulkahate_urgent_tickets
ntfy_topic = os.getenv("NTFY_TOPIC")
ntfy_url = f"https://ntfy.sh/{ntfy_topic}"

def send_ntfy(message):
    requests.post(ntfy_url, data=message.encode("utf-8"))

# -------------------------------
# LLM based intent detection
# -------------------------------
def classify_intent(query: str) -> str:
    prompt = f"""
Classify this banking query into exactly one label:

account_opening
loan
other

Query: {query}

Return only the label.
"""
    response = llm.invoke(prompt)
    return response.content.strip().lower()

# Send an email if user wants to apply for a loan
def send_email(message: str) -> str:
    from_email = "ekahate@gmail.com"  # Our Gmail address
    app_password = os.getenv("GMAIL_APP_PASSWORD")

    to_email = "newdelthis@gmail.com"
    subject = "Loan Application Request"
    body = f"Customer wants to apply for a loan:\n\n{message}"

    msg = MIMEMultipart()
    msg['From'] = from_email
    msg['To'] = to_email
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'plain'))

    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(from_email, app_password)
        server.send_message(msg)
        server.quit()
        print("***Debug*** Email sent successfully")
        return "Email sent successfully"
    except Exception as e:
        print(f"***Debug*** Email failed: {str(e)}")
        return f"Email send failed: {str(e)}"


# -------------------------------
# Banking node
# -------------------------------
def banking_node(state: ChatState) -> ChatState:
    results = vectordb.similarity_search(
        state["query"],
        k=1
    )

    if not results:
        state["answer"] = "Sorry I could not find the answer"
        return state

    doc = results[0]
    response = doc.metadata["Response"]

    intent = classify_intent(state["query"])

    if intent == "account_opening":
        message = (
            "New bank account request\n\n"
            + "User query\n"
            + state["query"]
            + "\n\n"
            + "System response\n"
            + response
        )
        send_ntfy(message)

    if intent == "loan":
        send_email(state["query"])

    state["answer"] = response
    return state

graph = StateGraph(ChatState)
graph.add_node("banking", banking_node)
graph.set_entry_point("banking")
graph.add_edge("banking", END)

banking_app = graph.compile()

# --------------------------------------------------
# HTML
# --------------------------------------------------
HTML = """
<!DOCTYPE html>
<html>
<head>
<title>Banking Assistant</title>
<style>
body{font-family:Arial;width:900px;margin:auto;margin-top:40px}
textarea{width:100%;height:80px}
.answer{margin-top:20px;padding:15px;border:1px solid #999;background:#f2f2f2;white-space:pre-wrap}
.examples li{margin:6px 0}
</style>
</head>
<body>

<h2>Banking Assistant</h2>

<form method="post">

<textarea
name="question"
placeholder="Ask a banking question..."></textarea>

<br><br>

<input type="submit" value="Ask">

</form>

<div class="examples">
<h3>Example Questions</h3>
<ul>
<li>I want to open a new bank account</li>
<li>I want to apply for a home loan</li>
<li>How can I check my account balance</li>
</ul>
</div>

{% if question %}

<h3>Question</h3>
<p>{{question}}</p>

<h3>Answer</h3>

<div class="answer">
{{answer}}
</div>

{% endif %}

</body>
</html>
"""

# --------------------------------------------------
# Flask Route
# --------------------------------------------------
@app.route("/", methods=["GET", "POST"])
def home():

    question = ""
    answer = ""

    if request.method == "POST":

        question = request.form["question"]

        answer = banking_app.invoke({"query": question})["answer"]

    return render_template_string(
        HTML,
        question=question,
        answer=answer
    )

# --------------------------------------------------
# Main
# --------------------------------------------------
if __name__ == "__main__":
    app.run(debug=True, use_reloader=False)