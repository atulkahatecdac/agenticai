# pip install python-dotenv crewai langsmith

import os
from dotenv import load_dotenv
from crewai import Agent, Task, Crew
from langsmith import traceable

# ------------------------------------------------------------------
# ENV (LangSmith)
# ------------------------------------------------------------------
load_dotenv(override=True)

#os.environ["LANGCHAIN_TRACING_V2"] = "true"
#os.environ["LANGCHAIN_PROJECT"] = "market-research-crew"

# ------------------------------------------------------------------
# AGENTS
# ------------------------------------------------------------------

market_researcher = Agent(
    role="Senior Market Researcher",
    goal="Analyze market trends and consumer behavior in the tech industry",
    backstory="Experienced researcher focused on emerging technology adoption.",
)

data_analyst = Agent(
    role="Data Analyst",
    goal="Extract statistical patterns and quantitative insights",
    backstory="Specialist in interpreting complex datasets and trends.",
)

content_strategist = Agent(
    role="Content Marketing Strategist",
    goal="Translate research insights into actionable marketing strategy",
    backstory="Expert at turning research into compelling business narratives.",
)

# ------------------------------------------------------------------
# TASKS (expected_output IS REQUIRED)
# ------------------------------------------------------------------

research_task = Task(
    description="""
    Research current AI adoption in small and medium businesses.
    Focus on adoption trends, barriers, common use cases, and perceived ROI.
    """,
    expected_output="A structured research summary on AI adoption trends and challenges in SMBs.",
    agent=market_researcher,
)

analysis_task = Task(
    description="""
    Analyze the research findings and identify key patterns and statistics.
    Highlight correlations, adoption drivers, and notable insights.
    """,
    expected_output="A data-driven analysis highlighting key adoption patterns and insights.",
    agent=data_analyst,
    context=[research_task],
)

content_task = Task(
    description="""
    Create a marketing strategy based on the research and analysis.
    Include key messaging, personas, and campaign recommendations.
    """,
    expected_output="A complete marketing strategy document with personas and messaging framework.",
    agent=content_strategist,
    context=[research_task, analysis_task],
)

# ------------------------------------------------------------------
# CREW
# ------------------------------------------------------------------

crew = Crew(
    agents=[market_researcher, data_analyst, content_strategist],
    tasks=[research_task, analysis_task, content_task],
    process="sequential",
)

# ------------------------------------------------------------------
# LANGSMITH ROOT TRACE (REQUIRED)
# ------------------------------------------------------------------

@traceable(name="market-research-crew")
def run_market_research_crew():
    return crew.kickoff()

# ------------------------------------------------------------------
# MAIN
# ------------------------------------------------------------------

if __name__ == "__main__":
    print("Running CrewAI market research crew...\n")
    result = run_market_research_crew()
    print("=" * 60)
    print("FINAL OUTPUT")
    print("=" * 60)
    print(result)
