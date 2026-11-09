# pip install autogen-agentchat autogen-core autogen-ext

import asyncio
from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.ui import Console
from autogen_core.memory import ListMemory, MemoryContent, MemoryMimeType
from autogen_ext.models.openai import OpenAIChatCompletionClient

from dotenv import load_dotenv

load_dotenv(override=True)
# --------------------------------------------------------
# STEP 1: Create memory to store user preferences
# --------------------------------------------------------
user_memory = ListMemory()

# --------------------------------------------------------
# STEP 2: Create model client
# --------------------------------------------------------
client = OpenAIChatCompletionClient(model="gpt-4o-mini")

# --------------------------------------------------------
# STEP 3: Create the assistant
# --------------------------------------------------------
assistant_agent = AssistantAgent(
    name="multilingual_assistant",
    model_client=client,
    memory=[user_memory],
)

# --------------------------------------------------------
# STEP 4: Step-by-step interaction
# --------------------------------------------------------
async def main():
    # Ask the user for their preferred language
    preferred_language = input("Please enter your preferred language (e.g., French, Hindi, Spanish): ").strip()

    # Store this preference in memory
    await user_memory.add(
        MemoryContent(content=f"The user prefers replies in {preferred_language}.", mime_type=MemoryMimeType.TEXT)
    )

    # Let the user ask a question in English
    user_question = input("Ask me a question in English: ")

    # Run the assistant — it should recall the memory and reply in preferred language
    print("Assistant is thinking...\n")
    stream = assistant_agent.run_stream(
        task=f"The user asked: '{user_question}'. Respond in their preferred language."
    )
    await Console(stream)

# --------------------------------------------------------
# Run the async function
# --------------------------------------------------------
if __name__ == "__main__":
    asyncio.run(main())
