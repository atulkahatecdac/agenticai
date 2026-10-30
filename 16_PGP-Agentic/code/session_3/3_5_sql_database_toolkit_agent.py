import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", category=PendingDeprecationWarning)
warnings.filterwarnings("ignore", category=FutureWarning)

import os
import sys
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.messages import BaseMessage, SystemMessage, HumanMessage, ToolMessage
from langchain_community.agent_toolkits import SQLDatabaseToolkit
from langchain_community.utilities import SQLDatabase

load_dotenv(override=True)

# Tool output can contain characters outside Windows' default console
# codepage (cp1252) - reconfigure stdout to UTF-8 so printing doesn't crash.
sys.stdout.reconfigure(encoding="utf-8")

llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

# -----------------------------
# SQLDatabase - reuses the sales.db already created by
# 3_4_create_sales_db.py (a "sales" table with
# product_name, sale_date, quantity, revenue).
# -----------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "sales.db")
db = SQLDatabase.from_uri(f"sqlite:///{os.path.abspath(DB_PATH)}")
print(f"Connected to: {db.get_usable_table_names()}")

toolkit = SQLDatabaseToolkit(db=db, llm=llm)
tools = toolkit.get_tools()
print("Tools:", ", ".join(t.name for t in tools))

SYSTEM_PROMPT = (
    "Always look up the table schema before writing a query - "
    "never guess column names. Use sql_db_query_checker before "
    "sql_db_query."
)

llm_with_tools = llm.bind_tools(tools)
tools_by_name = {t.name: t for t in tools}

# -----------------------------
# The agent loop: same bind_tools idea as 3_2_tool_calling.py, but it keeps
# going. The LLM asks for tools, our code runs them and feeds the results
# back, until the LLM answers without asking for a tool. max_steps stops a
# confused agent from looping (and spending tokens) forever.
# -----------------------------
def run_agent(question: str, max_steps: int = 8) -> str:
    messages: list[BaseMessage] = [SystemMessage(SYSTEM_PROMPT), HumanMessage(question)]

    for _ in range(max_steps):
        ai_message = llm_with_tools.invoke(messages)
        messages.append(ai_message)

        if not ai_message.tool_calls:
            return ai_message.content

        for tool_call in ai_message.tool_calls:
            print(f"Calling tool: {tool_call['name']}({tool_call['args']})")
            # A failed tool is reported back to the LLM so it can try to
            # fix the problem, instead of crashing the whole agent.
            try:
                result = tools_by_name[tool_call["name"]].invoke(tool_call["args"])
            except Exception as e:
                result = f"Tool failed: {e}"
            print(f"Tool result:\n{result}\n")
            messages.append(ToolMessage(content=str(result), tool_call_id=tool_call["id"]))

    return f"Stopped: no final answer after {max_steps} steps."

if __name__ == "__main__":
    question = "Which product generated the highest total revenue, and what was that total?"
    answer = run_agent(question)

    print("\n" + "=" * 70)
    print("FINAL ANSWER")
    print("=" * 70)
    print(answer)

    question2 = "How many units of each product were sold in total, ranked highest to lowest?"
    answer2 = run_agent(question2)

    print("\n" + "=" * 70)
    print("FINAL ANSWER")
    print("=" * 70)
    print(answer2)
