import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", category=PendingDeprecationWarning)
warnings.filterwarnings("ignore", category=FutureWarning)

import sys
from typing import Any
from dotenv import load_dotenv

# LLM output can contain characters outside Windows' default console
# codepage (cp1252, e.g. "≤") - reconfigure stdout to UTF-8 so printing
# results/callback data doesn't crash on them.
sys.stdout.reconfigure(encoding="utf-8")
from langchain_openai import ChatOpenAI
from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_community.callbacks import get_openai_callback

load_dotenv(override=True)

llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
prompt = ChatPromptTemplate.from_template("Answer briefly: {question}")
chain = prompt | llm | StrOutputParser()

# =====================================================================
# 1. Custom callback handler
# Callbacks are hooks that fire at specific points in a Runnable's
# lifecycle (chain start/end, LLM start/end, tool start/end, ...) -
# useful for logging, debugging, or forwarding events to an external
# monitoring system, all without touching the chain's own logic.
# There are many more hooks than shown here (on_tool_start, on_retriever_end,
# on_llm_error, ...) - this is just a representative few.
# =====================================================================
print("=" * 70)
print("1. Custom callback handler - logging lifecycle events")
print("=" * 70)

class LifecycleLogger(BaseCallbackHandler):
    def on_chain_start(self, serialized, inputs, **kwargs: Any) -> None:
        print(f"[chain started] input={inputs}")

    def on_chain_end(self, outputs, **kwargs: Any) -> None:
        print("[chain ended]")

    def on_llm_start(self, serialized, prompts, **kwargs: Any) -> None:
        print(f"[llm call started] {len(prompts)} prompt(s)")

    def on_llm_end(self, response, **kwargs: Any) -> None:
        print("[llm call ended]")

result = chain.invoke(
    {"question": "What is a p-value?"},
    config={"callbacks": [LifecycleLogger()]},
)
print(f"\nResult: {result}")

# =====================================================================
# 2. get_openai_callback
# Built-in context manager that tallies prompt/completion tokens and
# estimated cost for every OpenAI call made inside the `with` block -
# the standard way to monitor spend during development without
# instrumenting every call by hand.
# =====================================================================
print("\n" + "=" * 70)
print("2. get_openai_callback - token usage and cost tracking")
print("=" * 70)

with get_openai_callback() as cb:
    chain.invoke({"question": "What is linear regression?"})
    chain.invoke({"question": "What is a confidence interval?"})

print(f"Prompt tokens:     {cb.prompt_tokens}")
print(f"Completion tokens: {cb.completion_tokens}")
print(f"Total tokens:      {cb.total_tokens}")
print(f"Total cost (USD):  ${cb.total_cost:.6f}")

# =====================================================================
# 3. Streaming callback (on_llm_new_token)
# Fires once per token as the model generates it, instead of waiting for
# the full response - this is what powers "typing" style UIs. Requires
# streaming=True on the LLM so tokens are actually delivered incrementally.
# =====================================================================
print("\n" + "=" * 70)
print("3. Streaming callback - on_llm_new_token fires per generated token")
print("=" * 70)

class TokenPrinter(BaseCallbackHandler):
    def on_llm_new_token(self, token: str, **kwargs: Any) -> None:
        print(token, end="", flush=True)

streaming_llm = ChatOpenAI(model="gpt-4o-mini", temperature=0, streaming=True, callbacks=[TokenPrinter()])
streaming_chain = prompt | streaming_llm | StrOutputParser()

print("Response: ", end="")
streaming_chain.invoke({"question": "What is standard deviation?"})
print()
