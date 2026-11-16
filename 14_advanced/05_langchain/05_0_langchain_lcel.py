# LCEL (LangChain Expression Language): every component is a Runnable, and
# the pipe operator | connects them - the output of one becomes the input of
# the next. The composed chain is itself a Runnable (invoke, batch, stream).

from dotenv import load_dotenv
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_openai import ChatOpenAI

load_dotenv(override=True)

# 1. Create prompt template
prompt = ChatPromptTemplate.from_template(
    "Tell me a short fact about {topic}."
)

# 2. Create LLM
llm = ChatOpenAI(model="gpt-4o-mini")

# 3. Create output parser (AIMessage -> plain string)
parser = StrOutputParser()

# 4. Compose the pipeline using LCEL (each is a Runnable)
chain = prompt | llm | parser

# 5. Run
result = chain.invoke({"topic": "Albert Einstein"})
print(result)
