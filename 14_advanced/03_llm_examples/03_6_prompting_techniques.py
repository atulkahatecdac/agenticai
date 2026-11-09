# Prompting technique showcase: zero-shot, one-shot, few-shot, chain-of-thought,
# tree-of-thought, and ReAct — all applied to one realistic use case:
# an e-commerce assistant deciding refund eligibility for a return request.

import re
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv(override=True)

client = OpenAI()
MODEL = "gpt-4o-mini"

RETURN_POLICY = """
Store Return Policy:
- Items can be returned within 30 days of delivery for a full refund.
- Returned items must be unopened, or opened but undamaged.
- Items that are opened AND damaged are not eligible for a refund.
- Orders older than 30 days are not eligible for a refund, regardless of condition.
"""

# Simulated orders database, used only by the ReAct example below.
ORDERS_DB = {
    "A1001": {"item": "Wireless Mouse", "days_since_delivery": 12, "condition": "unopened", "price": 25.99},
    "A1002": {"item": "Bluetooth Headphones", "days_since_delivery": 42, "condition": "opened, undamaged", "price": 59.99},
    "A1003": {"item": "Laptop Stand", "days_since_delivery": 6, "condition": "opened, damaged", "price": 34.50},
}

# The borderline case used by zero/one/few-shot/CoT/ToT: undamaged, but delivered
# 42 days ago, so it fails the 30-day window even though the condition is fine.
CASE_A1002 = """
Customer message: "I'd like to return order A1002. Can I get a refund?"
Order details — Item: Bluetooth Headphones, Days since delivery: 42, Condition: opened, undamaged, Price: $59.99
"""


# -------------------------------------------------
# 1. Zero-shot prompting — no examples, just policy + case
# -------------------------------------------------
def zero_shot_prompt():
    response = client.responses.create(
        model=MODEL,
        instructions=RETURN_POLICY,
        input=f"{CASE_A1002}\nIs this order eligible for a refund? Answer Yes/No and give the refund amount if applicable."
    )
    print(response.output_text)


# -------------------------------------------------
# 2. One-shot prompting — one worked example before the real case
# -------------------------------------------------
def one_shot_prompt():
    example = """
Example:
Customer message: "I want to return order B2001."
Order details — Item: Desk Lamp, Days since delivery: 10, Condition: unopened, Price: $19.99
Answer: Yes, eligible for a refund of $19.99 (within 30 days, unopened).
"""
    response = client.responses.create(
        model=MODEL,
        instructions=RETURN_POLICY,
        input=f"{example}\nNow evaluate this case:\n{CASE_A1002}\nAnswer:"
    )
    print(response.output_text)


# -------------------------------------------------
# 3. Few-shot prompting — a few examples covering different policy rules
# -------------------------------------------------
def few_shot_prompt():
    examples = """
Example 1:
Customer message: "I want to return order B2001."
Order details — Item: Desk Lamp, Days since delivery: 10, Condition: unopened, Price: $19.99
Answer: Yes, eligible for a refund of $19.99 (within 30 days, unopened).

Example 2:
Customer message: "I want to return order B2002."
Order details — Item: Coffee Mug, Days since delivery: 5, Condition: opened, damaged, Price: $12.00
Answer: No, not eligible. Item is opened and damaged.

Example 3:
Customer message: "I want to return order B2003."
Order details — Item: Yoga Mat, Days since delivery: 35, Condition: unopened, Price: $22.00
Answer: No, not eligible. Order is older than the 30-day return window.
"""
    response = client.responses.create(
        model=MODEL,
        instructions=RETURN_POLICY,
        input=f"{examples}\nNow evaluate this case:\n{CASE_A1002}\nAnswer:"
    )
    print(response.output_text)


# -------------------------------------------------
# 4. Chain-of-thought prompting — ask the model to reason step by step
# -------------------------------------------------
def chain_of_thought_prompt():
    response = client.responses.create(
        model=MODEL,
        instructions=RETURN_POLICY,
        input=(
            f"{CASE_A1002}\n"
            "Think through the policy step by step (first check the 30-day window, "
            "then check the condition), showing your reasoning. "
            "End with a line: 'Final Decision: ...'"
        )
    )
    print(response.output_text)


# -------------------------------------------------
# 5. Tree-of-thought prompting — explore a few reasoning branches, then
#    have the model evaluate them and converge on one final decision
# -------------------------------------------------
def tree_of_thought_prompt():
    branches = []
    for i in range(3):
        response = client.responses.create(
            model=MODEL,
            temperature=0.9,
            instructions=RETURN_POLICY,
            input=(
                f"{CASE_A1002}\n"
                f"Explore ONE possible line of reasoning (branch {i + 1}) about whether "
                "this return is eligible. Keep it to 2-3 sentences and end with a tentative decision."
            )
        )
        branches.append(response.output_text)
        print(f"Branch {i + 1}:\n{response.output_text}\n")

    branch_summary = "\n\n".join(f"Branch {i + 1}:\n{b}" for i, b in enumerate(branches))
    evaluation = client.responses.create(
        model=MODEL,
        instructions=RETURN_POLICY,
        input=(
            f"Here are three independent reasoning branches about the same refund decision:\n\n"
            f"{branch_summary}\n\n"
            "Evaluate them against the store policy, point out which one reasons correctly, "
            "and give ONE final decision with justification."
        )
    )
    print(f"Final synthesized decision:\n{evaluation.output_text}")


# -------------------------------------------------
# 6. ReAct prompting — interleave Thought / Action / Observation until the
#    model has enough information (via a real tool call) to give a Final Answer
# -------------------------------------------------
def lookup_order(order_id: str) -> str:
    order = ORDERS_DB.get(order_id)
    if not order:
        return f"No order found with ID {order_id}."
    return (
        f"Item: {order['item']}, Days since delivery: {order['days_since_delivery']}, "
        f"Condition: {order['condition']}, Price: ${order['price']}"
    )


REACT_INSTRUCTIONS = f"""
You are a customer-support assistant that decides refund eligibility using ReAct-style
reasoning. You do NOT know order details in advance — you must look them up.

{RETURN_POLICY}

Available tool:
- lookup_order[order_id]: returns the item name, days since delivery, and condition for that order.

Respond ONE step at a time using exactly this format:
Thought: <your reasoning about what to do next>
Action: lookup_order[<order_id>]

After you receive an Observation, continue with more Thought/Action steps if needed,
or finish with:
Thought: <final reasoning>
Final Answer: <Yes/No the order is eligible for a refund, and the refund amount if applicable>

Do not output an Observation yourself — it will be provided to you.
"""


def react_prompt(customer_message: str, max_steps: int = 4):
    messages = [
        {"role": "system", "content": REACT_INSTRUCTIONS},
        {"role": "user", "content": customer_message},
    ]

    for _ in range(max_steps):
        response = client.responses.create(model=MODEL, input=messages)
        text = response.output_text
        print(text, "\n")

        if "Final Answer:" in text:
            break

        messages.append({"role": "assistant", "content": text})

        match = re.search(r"Action:\s*lookup_order\[(.*?)\]", text)
        if not match:
            break

        observation = lookup_order(match.group(1).strip())
        print(f"Observation: {observation}\n")
        messages.append({"role": "user", "content": f"Observation: {observation}"})


# -------------------------------------------------
# Run all demos
# -------------------------------------------------
if __name__ == "__main__":
    print("=== Zero-shot ===")
    zero_shot_prompt()

    print("\n=== One-shot ===")
    one_shot_prompt()

    print("\n=== Few-shot ===")
    few_shot_prompt()

    print("\n=== Chain-of-thought ===")
    chain_of_thought_prompt()

    print("\n=== Tree-of-thought ===")
    tree_of_thought_prompt()

    print("\n=== ReAct ===")
    react_prompt("I'd like to return order A1003. Can I get a refund?")
