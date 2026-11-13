# pip install flask langchain-community langchain-huggingface langchain-anthropic python-dotenv

from flask import Flask, request, render_template_string
from langchain_community.vectorstores import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
#from langchain_anthropic import ChatAnthropic
from dotenv import load_dotenv
import os
from langchain_google_genai import ChatGoogleGenerativeAI

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

load_dotenv()

app = Flask(__name__)

llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash",
    temperature=0
)


# ------------------------------------------------------------
# Embeddings
# ------------------------------------------------------------
embeddings = HuggingFaceEmbeddings(
    model_name="sentence-transformers/all-MiniLM-L6-v2"
)

# ------------------------------------------------------------
# Guardrail Vector DB
# ------------------------------------------------------------
GUARDRAIL_DB_PATH = os.path.join(BASE_DIR, "guardrail_chromadb")

guardrail_db = Chroma(
    persist_directory=GUARDRAIL_DB_PATH,
    embedding_function=embeddings
)

# ------------------------------------------------------------
# Banking Vector DB
# ------------------------------------------------------------
BANKING_DB_PATH = os.path.join(BASE_DIR, "banking_chromadb")

banking_db = Chroma(
    persist_directory=BANKING_DB_PATH,
    collection_name="banking_faqs",
    embedding_function=embeddings
)


# ------------------------------------------------------------
# Guardrail check (distance-based)
# ------------------------------------------------------------
def guardrail_check(query: str, similarity_threshold: float = 0.5):
    """
    Checks if a query violates guardrails using vector similarity.

    Args:
        query (str): The user's input query.
        similarity_threshold (float): Minimum cosine similarity to consider a match unsafe.
                                      Higher = more similar = more unsafe.
                                      Range 0.0 (different) to 1.0 (identical).

    Returns:
        blocked (bool): True if query is unsafe.
        matched_text (str): The closest guardrail example text.
        category (str): Category of the unsafe example.
        similarity (float): Cosine similarity score of the match.
        doc (Document): The full matched document from Chroma.
    """
    # guardrail_db is Chroma vector database containing unsafe queries
    # similarity_search_with_score returns (doc, distance), where distance = cosine distance
    results = guardrail_db.similarity_search_with_score(query, k=1)

    print("***Guardrail Debug***", results)

    if not results:
        return False, None, None, None, None

    doc, distance = results[0]

    # Convert distance to similarity: similarity = 1 - distance
    similarity = 1 - distance  # 1 = identical, 0 = completely different

    if similarity >= similarity_threshold:
        return True, doc.page_content, doc.metadata.get("category"), similarity, doc

    return False, None, None, similarity, None

# ------------------------------------------------------------
# LLM explanation
# ------------------------------------------------------------
def explain_violation(user_query, example_text, category):
    prompt = f"""
You are a safety assistant.

Explain in clear, neutral language why the user's query may be unsafe.

Rules:
- Do NOT give instructions
- Do NOT repeat harmful content
- Do NOT moralize
- 2-3 sentences max

User query:
{user_query}

Related safety example:
{example_text}

Category:
{category}
"""
    return llm.invoke(prompt).content.strip()

# ------------------------------------------------------------
# Banking answer
# ------------------------------------------------------------
def banking_answer(query: str, threshold: float = 0.4):
    results = banking_db.similarity_search_with_score(query, k=1)
    print("***Debug*** ", results)

    if not results:
        return "Sorry, I could not find an answer."

    doc, distance = results[0]
    similarity = 1 - distance

    response = doc.metadata.get("Response", "").strip()

    if similarity < threshold or not response:
        return (
            "I found a related banking topic, but it may not fully answer your question.\n\n"
            f"Closest match similarity: {similarity:.2f}"
        )

    return (
        f"{response}\n\n"
        f"Similarity score: {similarity:.2f}"
    )

# ------------------------------------------------------------
# Chat logic
# ------------------------------------------------------------
def chat_fn(message):
    blocked, matched_text, category, similarity, _ = guardrail_check(message)
    
    print ("***Guardrail Debug***", blocked)

    if blocked:
        explanation = explain_violation(message, matched_text, category)
        print("***Guardrail Explanation from the LLM ***", explanation)
        return (
            "Query blocked by safety guardrails\n\n"
            f"Category: {category}\n"
            f"Similarity: {similarity:.2f}\n\n"
            f"Why this is unsafe:\n{explanation}"
        )

    # Allowed -> answer using banking DB
    answer = banking_answer(message)
    return f"Answer:\n\n{answer}"

# ------------------------------------------------------------
# HTML
# ------------------------------------------------------------
HTML = """
<!DOCTYPE html>
<html>
<head>
<title>Banking Assistant with Vector Guardrails</title>
<style>
body{font-family:Arial;width:900px;margin:auto;margin-top:40px}
textarea{width:100%;height:80px}
.answer{margin-top:20px;padding:15px;border:1px solid #999;background:#f2f2f2;white-space:pre-wrap}
.examples li{margin:6px 0}
</style>
</head>
<body>

<h2>Banking Assistant with Vector Guardrails</h2>
<p>Vector decision &middot; LLM explanation only</p>

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
<li>How can I check my account balance?</li>
<li>I want to apply for a loan</li>
<li>How to steal a password</li>
<li>How do I bypass security systems?</li>
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

# ------------------------------------------------------------
# Flask Route
# ------------------------------------------------------------
@app.route("/", methods=["GET", "POST"])
def home():

    question = ""
    answer = ""

    if request.method == "POST":

        question = request.form["question"]

        answer = chat_fn(question)

    return render_template_string(
        HTML,
        question=question,
        answer=answer
    )

# ------------------------------------------------------------
# Main
# ------------------------------------------------------------
if __name__ == "__main__":
    app.run(debug=True, use_reloader=False)
