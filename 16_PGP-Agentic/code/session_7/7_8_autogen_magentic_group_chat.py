# pip install pdfplumber autogen-agentchat autogen-ext python-dotenv requests

# Tested with this: https://ijrar.org/papers/IJRAR19K9780.pdf
import asyncio
import os
import tempfile
import requests
import pdfplumber
from dotenv import load_dotenv
from autogen_ext.models.openai import OpenAIChatCompletionClient
from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.teams import MagenticOneGroupChat

load_dotenv(override=True)

# -----------------------------
# Helper: Download + Extract PDF text
# -----------------------------
def extract_text_from_pdf(source: str) -> str:
    """
    Accepts either a URL or local file path and returns extracted text.
    """
    if source.startswith("http"):
        response = requests.get(source)
        response.raise_for_status()
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            tmp.write(response.content)
            tmp_path = tmp.name
    else:
        tmp_path = source  # Local file path

    text = ""
    with pdfplumber.open(tmp_path) as pdf:
        for page in pdf.pages:
            text += page.extract_text() or ""

    if source.startswith("http"):
        os.remove(tmp_path)

    return text[:20000]  # limit to 20k chars for efficiency


# -----------------------------
# Model client + Agents
# -----------------------------
model_client = OpenAIChatCompletionClient(model="gpt-4o-mini")

extractor = AssistantAgent(
    name="Extractor",
    model_client=model_client,
    system_message="You extract structured sections and data points from documents clearly."
)

summarizer = AssistantAgent(
    name="Summarizer",
    model_client=model_client,
    system_message="You summarize the extracted content concisely, highlighting important insights."
)

analyst = AssistantAgent(
    name="Analyst",
    model_client=model_client,
    system_message="You analyze the summarized content for patterns, risks, and recommendations."
)

reviewer = AssistantAgent(
    name="Reviewer",
    model_client=model_client,
    system_message="You review all outputs for clarity and correctness, and produce a final report."
)

team = MagenticOneGroupChat(
    participants=[extractor, summarizer, analyst, reviewer],
    model_client=model_client,
)

# -----------------------------
# Main
# -----------------------------
async def main():
    print("\n=== Automated PDF / URL Analyzer ===\n")
    source = input("Enter PDF file path or URL: ").strip()

    try:
        doc_text = extract_text_from_pdf(source)
        print(f"\nExtracted {len(doc_text)} characters from document.\n")
    except Exception as e:
        print(f"Failed to read PDF: {e}")
        return

    task = (
        "Analyze this document text in stages: extract, summarize, analyze, and review. "
        "Output a final analytical report.\n\n"
        f"{doc_text}"
    )

    print("\n=== Streaming Multi-Agent Collaboration ===\n")

    async for chunk in team.run_stream(task=task):
        # Stream each message as it arrives
        if hasattr(chunk, "content") and chunk.content:
            sender = getattr(chunk, "sender", "Agent")
            print(f"\033[96m[{sender}]\033[0m {chunk.content}\n")

    print("\n=== Final Report Generated ===\n")
    await model_client.close()


if __name__ == "__main__":
    asyncio.run(main())
