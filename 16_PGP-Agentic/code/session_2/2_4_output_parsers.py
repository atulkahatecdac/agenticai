import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", category=PendingDeprecationWarning)
warnings.filterwarnings("ignore", category=FutureWarning)

from dotenv import load_dotenv
from pydantic import BaseModel, Field
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import (
    StrOutputParser,
    JsonOutputParser,
    PydanticOutputParser,
)

load_dotenv(override=True)

llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0)

# -----------------------------
# 1. StrOutputParser
# Just extracts the raw text from the LLM's response message.
# Useful whenever you don't need structure - chatbots, summaries, etc.
# -----------------------------
print("=" * 70)
print("1. StrOutputParser - plain text output")
print("=" * 70)

str_prompt = ChatPromptTemplate.from_template("Answer briefly: {question}")
str_chain = str_prompt | llm | StrOutputParser()

result = str_chain.invoke({"question": "What is the capital of Japan?"})
print(f"Type: {type(result).__name__}")
print(f"Result: {result}")

# -----------------------------
# 2. JsonOutputParser
# Asks the LLM to return JSON and parses it into a plain dict.
# No schema enforcement - the LLM decides the shape, you just get a dict back.
# -----------------------------
print("\n" + "=" * 70)
print("2. JsonOutputParser - unstructured dict output")
print("=" * 70)

json_parser = JsonOutputParser()
json_prompt = ChatPromptTemplate.from_messages([
    ("system", "Answer in JSON.\n{format_instructions}"),
    ("human", "Give me the name, country, and population of the city {city}."),
]).partial(format_instructions=json_parser.get_format_instructions())

json_chain = json_prompt | llm | json_parser
result = json_chain.invoke({"city": "Tokyo"})
print(f"Type: {type(result).__name__}")
print(f"Result: {result}")
print(f"Dict access: result['population'] = {result.get('population')}")

# -----------------------------
# 3. PydanticOutputParser
# Asks the LLM to return JSON matching a specific Pydantic schema, then
# validates and parses it into a typed, attribute-accessible object.
# If the LLM's output doesn't match the schema, this raises instead of
# silently returning malformed data - the main advantage over JsonOutputParser.
# -----------------------------
print("\n" + "=" * 70)
print("3. PydanticOutputParser - validated, typed object output")
print("=" * 70)

class CityInfo(BaseModel):
    name: str = Field(description="Name of the city")
    country: str = Field(description="Country the city is in")
    population: int = Field(description="Approximate population of the city")
    famous_for: list[str] = Field(description="A few things the city is famous for")

pydantic_parser = PydanticOutputParser(pydantic_object=CityInfo)
pydantic_prompt = ChatPromptTemplate.from_messages([
    ("system", "Answer strictly following this format.\n{format_instructions}"),
    ("human", "Tell me about the city {city}."),
]).partial(format_instructions=pydantic_parser.get_format_instructions())

pydantic_chain = pydantic_prompt | llm | pydantic_parser
result = pydantic_chain.invoke({"city": "Paris"})
print(f"Type: {type(result).__name__}")
print(f"Result: {result}")
print(f"Attribute access: result.population = {result.population}")
print(f"result.famous_for = {result.famous_for}")
