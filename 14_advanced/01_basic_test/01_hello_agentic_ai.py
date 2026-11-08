# Hello, Agentic AI: one LangChain call to a local model.
#
# Needs Ollama running with the qwen3 model (no API key):
#   ollama pull qwen3:8b

from langchain_ollama import ChatOllama

llm = ChatOllama(model="qwen3:8b", reasoning=False)  # reasoning=False: answer only, no <think> text

response = llm.invoke("Give me a simple Java program that "
                      " accepts a number from the user and prints "
                      " its factorial")

print(response.content)
