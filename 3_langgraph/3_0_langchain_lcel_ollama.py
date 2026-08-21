from langchain_core.prompts import ChatPromptTemplate
from langchain_ollama import ChatOllama

prompt = ChatPromptTemplate.from_template(
    "Explain {topic} in simple terms."
)

llm = ChatOllama(model="qwen3:8b")

chain = prompt | llm

response = chain.invoke(
    {"topic":"embeddings"}
)

print(response.content)
