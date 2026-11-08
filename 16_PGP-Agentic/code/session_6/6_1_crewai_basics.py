import sys
from dotenv import load_dotenv
from crewai import Agent, Task, Crew, LLM

load_dotenv(override=True)
sys.stdout.reconfigure(encoding="utf-8")

# =====================================================================
# CrewAI basics: the smallest possible crew.
#   Agent - who does the work (role, goal, backstory, LLM)
#   Task  - what to produce (description, expected output, which agent)
#   Crew  - runs the tasks with the agents
# One agent, one task, no tools, no context, no memory.
#
# Runs on a local model - no API key needed:
#   ollama pull qwen3:8b
# =====================================================================

local_llm = LLM(model="ollama/qwen3:8b", base_url="http://localhost:11434")

explainer = Agent(
    role="Tech Explainer",
    goal="Explain technical ideas to complete beginners",
    backstory="You are a patient teacher who explains things simply, without jargon.",
    llm=local_llm,
    verbose=True,
)

explain_task = Task(
    description="Explain {topic} to a beginner.",
    expected_output="A 3-4 sentence plain-English explanation with one everyday example",
    agent=explainer,
)

crew = Crew(
    agents=[explainer],
    tasks=[explain_task],
    verbose=True,
)

if __name__ == "__main__":
    result = crew.kickoff(inputs={"topic": "an AI agent"})
    print("\n" + "=" * 70)
    print(result)
