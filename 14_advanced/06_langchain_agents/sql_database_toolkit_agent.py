import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", category=PendingDeprecationWarning)
warnings.filterwarnings("ignore", category=FutureWarning)

import os
import sys
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.agents import create_tool_calling_agent, AgentExecutor
from langchain_community.agent_toolkits import SQLDatabaseToolkit
from langchain_community.utilities import SQLDatabase

load_dotenv(override=True)

# Tool output can contain characters outside Windows' default console
# codepage (cp1252) - reconfigure stdout to UTF-8 so printing doesn't crash.
sys.stdout.reconfigure(encoding="utf-8")

llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

# -----------------------------
# SQLDatabase - reuses the sales.db already created by
# 14_advanced/03_llm_examples/create_sales_db.py (a "sales" table with
# product_name, sale_date, quantity, revenue).
# -----------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "..", "03_llm_examples", "sales.db")
db = SQLDatabase.from_uri(f"sqlite:///{os.path.abspath(DB_PATH)}")
print(f"Connected to: {db.get_usable_table_names()}")

toolkit = SQLDatabaseToolkit(db=db, llm=llm)
tools = toolkit.get_tools()
print("Tools:", ", ".join(t.name for t in tools))

prompt = ChatPromptTemplate.from_messages([
    ("system", "Always look up the table schema before writing a query - "
               "never guess column names. Use sql_db_query_checker before "
               "sql_db_query."),
    ("human", "{input}"),
    MessagesPlaceholder("agent_scratchpad"),
])

agent = create_tool_calling_agent(llm, tools, prompt)
agent_executor = AgentExecutor(
    agent=agent,
    tools=tools,
    verbose=True,
    max_iterations=8,
)

if __name__ == "__main__":
    question = "Which product generated the highest total revenue, and what was that total?"
    result = agent_executor.invoke({"input": question})

    print("\n" + "=" * 70)
    print("FINAL ANSWER")
    print("=" * 70)
    print(result["output"])

    question2 = "How many units of each product were sold in total, ranked highest to lowest?"
    result2 = agent_executor.invoke({"input": question2})

    print("\n" + "=" * 70)
    print("FINAL ANSWER")
    print("=" * 70)
    print(result2["output"])
