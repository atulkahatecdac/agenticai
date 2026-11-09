# pip install langchain-openai langsmith
import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", category=PendingDeprecationWarning)
warnings.filterwarnings("ignore", category=FutureWarning)

import os
import sys
import time
from dotenv import load_dotenv

load_dotenv(override=True)

# .env's LANGSMITH_PROJECT is shared with other exercises in this repo
# (e.g. a CrewAI market-research demo) - use a dedicated project here so
# this script's traces don't get mixed in with unrelated ones.
#os.environ["LANGSMITH_PROJECT"] = "agenticai-09-langsmith-demo"

# LLM output can contain characters outside Windows' default console
# codepage (cp1252) - reconfigure stdout to UTF-8 so printing doesn't crash.
sys.stdout.reconfigure(encoding="utf-8")

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.tracers.context import tracing_v2_enabled
from langsmith import traceable, Client
from langsmith.run_helpers import get_current_run_tree

llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
prompt = ChatPromptTemplate.from_template("Answer briefly: {question}")
chain = prompt | llm | StrOutputParser()

# =====================================================================
# 1. Automatic tracing via environment variables
# With LANGSMITH_TRACING=true and LANGSMITH_API_KEY set (see .env), every
# LangChain call in this process is automatically traced to LangSmith -
# no code changes needed. tracing_v2_enabled() just lets us grab the
# resulting run's URL afterward to prove it actually landed there.
# =====================================================================
print("=" * 70)
print("1. Automatic tracing (LANGSMITH_TRACING env var)")
print("=" * 70)

with tracing_v2_enabled(project_name=os.environ["LANGSMITH_PROJECT"]) as tracer:
    result = chain.invoke({"question": "What is a p-value?"})
    print(f"Result: {result}")
    print(f"View trace: {tracer.get_run_url()}")

# =====================================================================
# 2. @traceable - tracing custom (non-LangChain) functions
# Wraps an ordinary Python function so it shows up as its own span in
# LangSmith, correctly nested around whatever LangChain calls happen
# inside it. Useful for tracing business logic / preprocessing steps
# that sit alongside your LLM calls, not just the LLM calls themselves.
# =====================================================================
print("\n" + "=" * 70)
print("2. @traceable - tracing custom functions alongside LLM calls")
print("=" * 70)

# @traceable establishes its OWN trace context (separate from
# tracing_v2_enabled's LangChainTracer) - the nested chain.invoke() below
# correctly attaches as a child span under it automatically. Fetch the URL
# from inside the function, while that context is still active.
@traceable(name="answer_question_pipeline")
def answer_question(raw_question: str) -> str:
    normalized = raw_question.strip().rstrip("?") + "?"
    run = get_current_run_tree()
    print(f"View trace: {run.get_url()}")
    return chain.invoke({"question": normalized})

result = answer_question("what is linear regression")
print(f"Result: {result}")

# =====================================================================
# 3. Tags and metadata on individual calls
# Passed through `config`, these show up as filterable fields in the
# LangSmith UI - e.g. filter runs by tag, or group them by a user/session
# id - without needing a separate project per use case.
# =====================================================================
print("\n" + "=" * 70)
print("3. Tags and metadata on individual calls")
print("=" * 70)

with tracing_v2_enabled(project_name=os.environ["LANGSMITH_PROJECT"]) as tracer:
    result = chain.invoke(
        {"question": "What is a confidence interval?"},
        config={
            "run_name": "confidence_interval_lookup",
            "tags": ["demo", "09_langsmith"],
            "metadata": {"user_id": "atul", "topic": "statistics"},
        },
    )
    print(f"Result: {result}")
    print(f"View trace: {tracer.get_run_url()}")
    last_run_id = tracer.latest_run.id
    # Runs are submitted to LangSmith asynchronously in the background -
    # without this, reading the run back immediately can 404 since it
    # hasn't finished uploading yet.
    tracer.wait_for_futures()

# =====================================================================
# 4. Client - fetching run data back from LangSmith
# The same Client used for tracing can pull run data back down
# programmatically - useful for automated eval pipelines that grade past
# runs, or dashboards that don't go through the LangSmith UI directly.
# =====================================================================
print("\n" + "=" * 70)
print("4. Client - fetching run data back from LangSmith")
print("=" * 70)

client = Client()

# Even after wait_for_futures(), LangSmith's backend can take a moment to
# finish indexing a run before it's readable AND fully finalized (status
# starts out "pending" until the backend processes the run's end event) -
# retry until it's actually done, not just until the read succeeds.
run = None
for attempt in range(10):
    try:
        candidate = client.read_run(last_run_id)
        if candidate.end_time is not None:
            run = candidate
            break
    except Exception:
        pass
    time.sleep(2)

if run is None:
    print("Run not yet finalized server-side (indexing delay) - try again in a few seconds.")
else:
    print(f"Run name:     {run.name}")
    print(f"Run status:   {run.status}")
    print(f"Total tokens: {run.total_tokens}")
    print(f"Latency:      {(run.end_time - run.start_time).total_seconds():.2f}s")
