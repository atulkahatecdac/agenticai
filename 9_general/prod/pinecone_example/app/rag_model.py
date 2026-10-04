from openai import OpenAI
from pinecone import Pinecone
from config import OPENAI_API_KEY, PINECONE_API_KEY

client = OpenAI(api_key=OPENAI_API_KEY)
pc = Pinecone(api_key=PINECONE_API_KEY)

index = pc.Index("faq-embeddings")
NAMESPACE = "ns-1"   # must match the namespace used in 9_prod_pinecone_embedding_creation.py


def get_rag_response(query):

    # 1. Create embedding for the query
    query_embedding = client.embeddings.create(
        model="text-embedding-3-small",
        input=query
    ).data[0].embedding

    # 2. Search Pinecone
    results = index.query(
        vector=query_embedding,
        top_k=3,
        include_metadata=True,
        namespace=NAMESPACE
    )

    # 3. Extract retrieved documents (the ingest script stores "question" and "answer")
    documents = [
        f"Q: {match['metadata']['question']}\nA: {match['metadata']['answer']}"
        for match in results["matches"]
    ]

    # 4. Combine retrieved documents
    retrieved_context = "\n\n---\n\n".join(documents)

    # 5. Give ONLY retrieved context to the LLM
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": """
You are a customer-support assistant. Answer using ONLY the FAQ entries in the RAG CONTEXT.

- If the context contains the relevant facts, answer from them, even when the customer's exact
  wording is not in the context. Example: if the context lists the accepted payment methods and
  the customer asks about a method that is not in the list, say it is not accepted and list the
  accepted ones.
- Do not add facts that are not in the context, and do not use your own knowledge.
  If the context is vague (e.g. "select international destinations"), say exactly that and
  suggest contacting support for details - do not claim a specific case is included.
- Only if no FAQ entry is relevant to the question, reply exactly:
  I don't have enough information in the provided documents.
- Keep the answer to one or two sentences.
"""
            },
            {
                "role": "user",
                # No trailing "ANSWER:" line - with it, gpt-4o-mini falls back to the
                # "not enough information" reply even when the context has the answer.
                "content": f"RAG CONTEXT:\n{retrieved_context}\n\nCUSTOMER QUESTION:\n{query}"
            }
        ],
        max_tokens=150,
        temperature=0
    )

    return response.choices[0].message.content


if __name__ == "__main__":
    print(get_rag_response("What is the refund policy?"))
