# pip install autogen-ext[anthropic] yfinance
import asyncio
import yfinance as yf
from dotenv import load_dotenv
from autogen_ext.models.anthropic import AnthropicChatCompletionClient
from autogen_agentchat.messages import TextMessage
from autogen_agentchat.agents import AssistantAgent

load_dotenv(override=True)

# ---------- Finance helper ----------
async def get_investment_value(symbol: str, start_date: str, amount_inr: float):
    """Calculate today's value of an investment made on start_date."""
    ticker = yf.Ticker(symbol)
    data = ticker.history(start=start_date)
    if data.empty:
        return f"No data found for {symbol}"

    start_price = data["Close"].iloc[0]
    latest_price = data["Close"].iloc[-1]
    final_value = amount_inr * (latest_price / start_price)
    return {
        "symbol": symbol,
        "start_price": round(start_price, 2),
        "latest_price": round(latest_price, 2),
        "final_value": round(final_value, 2),
    }

# ---------- Claude model setup ----------
model_client = AnthropicChatCompletionClient(model="claude-sonnet-4-6")



# Agent 1 → Infosys stock
stock_return_agent = AssistantAgent(
    name="stock_return_agent",
    model_client=model_client,
    system_message="You are a financial analyst who explains stock investment returns clearly and concisely."
)

# Agent 2 → BSE Sensex index
index_return_agent = AssistantAgent(
    name="index_return_agent",
    model_client=model_client,
    system_message="You are a financial analyst who explains long-term index returns and market trends."
)

# ---------- Async main ----------
async def main():
    # Fetch data concurrently
    infosys_task = asyncio.create_task(get_investment_value("INFY.NS", "1995-01-01", 10000))
    sensex_task = asyncio.create_task(get_investment_value("^BSESN", "1995-01-01", 10000))

    infosys_data, sensex_data = await asyncio.gather(infosys_task, sensex_task)

    # Run Claude agents concurrently
    stock_task = asyncio.create_task(
        stock_return_agent.on_messages([
            TextMessage(
                content=f"Given this data {infosys_data}, summarize how much ₹10,000 invested in Infosys on 1 Jan 1995 "
                        f"would be worth today, including key stock growth insights.",
                source="User"
            )
        ], cancellation_token=None)
    )

    index_task = asyncio.create_task(
        index_return_agent.on_messages([
            TextMessage(
                content=f"Given this data {sensex_data}, summarize how much ₹10,000 invested in the BSE Sensex on "
                        f"1 Jan 1995 would be worth today, with a long-term market analysis.",
                source="User"
            )
        ], cancellation_token=None)
    )

    # Wait for both analyses to complete
    stock_result, index_result = await asyncio.gather(stock_task, index_task)

    # Display results
    print("\n" + "="*50 + "\nINFOSYS INVESTMENT RETURN\n" + "="*50)
    print(stock_result.chat_message.content)

    print("\n" + "="*50 + "\nSENSEX INVESTMENT RETURN\n" + "="*50)
    print(index_result.chat_message.content)

    await stock_return_agent.close()
    await index_return_agent.close()

if __name__ == "__main__":
    asyncio.run(main())
