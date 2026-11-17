import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", category=PendingDeprecationWarning)
warnings.filterwarnings("ignore", category=FutureWarning)

import os
import sys
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_community.agent_toolkits import SQLDatabaseToolkit
from langchain_community.utilities import SQLDatabase
from langgraph.errors import GraphRecursionError
from langgraph.prebuilt import create_react_agent

load_dotenv(override=True)

# Tool output can contain characters outside Windows' default console
# codepage (cp1252) - reconfigure stdout to UTF-8 so printing doesn't crash.
sys.stdout.reconfigure(encoding="utf-8")

llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

# -----------------------------
# Same database, tools and system prompt as 06_3_sql_database_toolkit_agent.py
# (reuses the sales.db created by 03_llm_examples/03_8_create_sales_db.py).
# -----------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "..", "03_llm_examples", "sales.db")
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

# -----------------------------
# The same agent as 06_3, but without writing the loop ourselves.
# LangGraph's prebuilt create_react_agent IS that loop: an "agent" node
# calls the LLM, a "tools" node runs whatever tools it asked for (and
# sends tool errors back to the LLM instead of crashing - our try/except
# in 06_3), and it repeats until the LLM answers without a tool call.
# LangGraph itself is Module 07; here we only use the ready-made agent.
# -----------------------------
agent = create_react_agent(llm, tools, prompt=SYSTEM_PROMPT)

def run_agent(question: str, max_steps: int = 8) -> str:
    final_answer = ""
    try:
        # stream_mode="updates" yields one {node_name: new_messages} dict
        # per step, so we can still print every tool call and result.
        for update in agent.stream(
            {"messages": [("user", question)]},
            # Each step is two graph steps (agent + tools), so this is our
            # max_steps from 06_3. Hitting it raises GraphRecursionError.
            {"recursion_limit": 2 * max_steps + 1},
            stream_mode="updates",
        ):
            for node, data in update.items():
                for msg in data["messages"]:
                    if node == "agent" and msg.tool_calls:
                        for call in msg.tool_calls:
                            print(f"Calling tool: {call['name']}({call['args']})")
                    elif node == "tools":
                        print(f"Tool result:\n{msg.content}\n")
                    else:
                        final_answer = msg.content
    except GraphRecursionError:
        return f"Stopped: no final answer after {max_steps} steps."
    return final_answer

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
