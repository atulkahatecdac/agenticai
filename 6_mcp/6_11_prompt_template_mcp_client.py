import asyncio
from dotenv import load_dotenv
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from openai import OpenAI

load_dotenv(override=True)

llm = OpenAI()


async def render_and_draft(session: ClientSession, prompt_name: str, arguments: dict) -> str:
    # Ask the SERVER to render its prompt template with these arguments -
    # the client never sees or maintains the wording itself, just the
    # rendered result.
    rendered = await session.get_prompt(prompt_name, arguments)
    messages = [{"role": m.role, "content": m.content.text} for m in rendered.messages]

    response = llm.chat.completions.create(model="gpt-4o-mini", messages=messages)
    return response.choices[0].message.content


async def answer_customer_question(session: ClientSession, product_name: str, customer_question: str):
    print(f'\n=== Question about "{product_name}": {customer_question} ===')

    # Ground the answer in real data before rendering any prompt template.
    result = await session.call_tool("get_product_info", {"product_name": product_name})
    product_details = result.content[0].text

    if product_details == "NOT_FOUND":
        reply = await render_and_draft(
            session, "product_not_found_reply",
            {"product_name": product_name, "customer_question": customer_question},
        )
    else:
        reply = await render_and_draft(
            session, "answer_product_question",
            {"product_name": product_name, "product_details": product_details, "customer_question": customer_question},
        )

    print(reply)


async def main():
    server_params = StdioServerParameters(
        command="python",
        args=["c:/code/agenticai/6_mcp/6_11_prompt_template_mcp_server.py"],
    )

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            # Discover which prompt templates this server offers, and what
            # arguments each one needs - a client shouldn't have to hardcode
            # that knowledge in advance.
            available = await session.list_prompts()
            print("Available prompt templates:")
            for p in available.prompts:
                arg_names = [a.name for a in (p.arguments or [])]
                print(f"  - {p.name}({', '.join(arg_names)}): {p.description}")

            await answer_customer_question(
                session, "Wireless Mouse X200", "What's the price and does it come with a warranty?"
            )
            await answer_customer_question(
                session, "Noise Cancelling Headphones Pro", "Is this in stock right now?"
            )
            await answer_customer_question(
                session, "Drone", "Do you sell drones?"
            )


if __name__ == "__main__":
    asyncio.run(main())
