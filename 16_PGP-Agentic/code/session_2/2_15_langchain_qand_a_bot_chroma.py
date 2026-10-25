import os
from fastapi import FastAPI
from pydantic import BaseModel, Field
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma
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
PERSIST_PATH = os.path.join(BASE_DIR, "local_chroma_insurance_db")
PDF_PATH = os.path.join(BASE_DIR, "Introduction_to_Insurance.pdf")

embeddings = HuggingFaceEmbeddings(
    model_name="sentence-transformers/all-MiniLM-L6-v2",
    model_kwargs={'device': 'cpu'}
)

# 2. Ingestion Logic (Run only if DB is empty)
if not os.path.exists(PERSIST_PATH) or not os.listdir(PERSIST_PATH):
    print("Ingesting PDF...")
    loader = PyPDFLoader(PDF_PATH)
    data = loader.load()
    print(f"Pages loaded: {len(data)}")
    
    splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=100)
    docs = splitter.split_documents(data)
    print(f"Chunks created: {len(docs)}")
    
    if not docs:
        raise ValueError("ERROR!!! No text chunks created from PDF")
    
    vector_db = Chroma.from_documents(
        documents=docs, 
        embedding=embeddings, 
        persist_directory=PERSIST_PATH
    )
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
app = FastAPI(title="PDF Q&A Bot")

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