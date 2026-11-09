import os
from fastapi import FastAPI
from pydantic import BaseModel, Field
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser
from langserve import add_routes
from operator import itemgetter

from dotenv import load_dotenv

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(override=True)

# 1. Configuration & Embedding Setup
# Pick the vector store: "chroma" manages a directory of files and persists
# automatically; "faiss" is an index + a pickle of the documents, saved and
# loaded explicitly with save_local / load_local. The rest of the app is
# identical - the retriever hides which store is underneath.
VECTOR_STORE = "chroma"

PDF_PATH = os.path.join(BASE_DIR, "..", "..", "15_real", "Introduction_to_Insurance.pdf")
PERSIST_PATH = os.path.join(BASE_DIR, "local_chroma_insurance_db" if VECTOR_STORE == "chroma"
                            else "faiss_insurance_index")

embeddings = HuggingFaceEmbeddings(
    model_name="sentence-transformers/all-MiniLM-L6-v2",
    model_kwargs={'device': 'cpu'}
)

def load_chunks():
    print(f"Ingesting PDF into {VECTOR_STORE}...")
    data = PyPDFLoader(PDF_PATH).load()
    print(f"Pages loaded: {len(data)}")
    docs = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=100).split_documents(data)
    print(f"Chunks created: {len(docs)}")
    if not docs:
        raise ValueError("ERROR!!! No text chunks created from PDF")
    return docs

# 2. Ingestion Logic (only when there is no saved store yet)
already_saved = os.path.exists(PERSIST_PATH) and os.listdir(PERSIST_PATH)
if VECTOR_STORE == "faiss":
    from langchain_community.vectorstores import FAISS
    if not already_saved:
        vector_db = FAISS.from_documents(load_chunks(), embeddings)
        vector_db.save_local(PERSIST_PATH)
    else:
        # FAISS stores the documents in a pickle file, and unpickling can run
        # code - so LangChain makes you confirm you trust this file (we wrote it).
        vector_db = FAISS.load_local(PERSIST_PATH, embeddings,
                                     allow_dangerous_deserialization=True)
else:
    from langchain_chroma import Chroma
    if not already_saved:
        vector_db = Chroma.from_documents(documents=load_chunks(), embedding=embeddings,
                                          persist_directory=PERSIST_PATH)
    else:
        vector_db = Chroma(persist_directory=PERSIST_PATH, embedding_function=embeddings)

# 3. Define the RAG Chain using LCEL
retriever = vector_db.as_retriever(search_kwargs={"k": 3})
model = ChatOpenAI(model="gpt-4o-mini")

template = """Answer the question based only on the following context:
{context}

Question: {question}
"""
prompt = ChatPromptTemplate.from_template(template)

def format_docs(docs):
    return "\n\n".join(doc.page_content for doc in docs)

# The RAG Pipe
chain = (
    {
        # Use itemgetter("question") to extract the string from the ChatInput dict
        "context": itemgetter("question") | retriever | format_docs, 
        "question": itemgetter("question")
    }
    | prompt
    | model
    | StrOutputParser()
)

# 4. LangServe Deployment
app = FastAPI(title=f"PDF Q&A Bot ({VECTOR_STORE})")

class ChatInput(BaseModel):
    question: str = Field(..., description="Ask a question about the PDF")

add_routes(
    app,
    chain.with_types(input_type=ChatInput),
    path="/ask"
)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="localhost", port=8000, log_level="info")