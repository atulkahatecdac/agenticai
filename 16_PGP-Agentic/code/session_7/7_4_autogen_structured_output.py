import os
# pip install pandas pydantic autogen-agentchat autogen-ext python-dotenv

import asyncio
import pandas as pd
from typing import Optional
from pydantic import BaseModel
from autogen_ext.models.openai import OpenAIChatCompletionClient
from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.messages import StructuredMessage
from dotenv import load_dotenv

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Define structured output model
class JobInfo(BaseModel):
    company_name: Optional[str] = None
    role: Optional[str] = None
    location: Optional[str] = None

# Load data and pick sample rows
df = pd.read_csv(os.path.join(BASE_DIR, "clean_jobs.csv"))
descriptions = df.loc[[4, 104, 204, 304, 404], "description"].tolist()

# Setup model client
load_dotenv(override=True)
model_client = OpenAIChatCompletionClient(model="gpt-4o")

# Create AssistantAgent with structured output
agent = AssistantAgent(
    name="job_extractor",
    model_client=model_client,
    system_message="Extract company name, role, and location from the job description.",
    output_content_type=JobInfo,
    model_client_stream=True,
)

async def main():
    for i, desc in enumerate(descriptions, start=1):
        print(f"\n--- Job {i} ---")

        async for message in agent.run_stream(task=desc):
            if isinstance(message, StructuredMessage):
                job_info = message.content
                if isinstance(job_info, JobInfo):
                    print(f"\rCompany: {job_info.company_name or 'N/A'} | "
                          f"Role: {job_info.role or 'N/A'} | "
                          f"Location: {job_info.location or 'N/A'}", end="")

        print()  # newline per job

    await model_client.close()
    print("\nAll selected jobs processed.")

if __name__ == "__main__":
    asyncio.run(main())
