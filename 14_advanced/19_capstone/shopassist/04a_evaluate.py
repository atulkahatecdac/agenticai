from dotenv import load_dotenv
from anthropic import Anthropic

load_dotenv()
client = Anthropic()

MODEL = "claude-sonnet-5-5"

CASES = [
    ("I bought a jacket, delivered 20 days ago. Can I return it?", "YES"),
    ("The shoes arrived yesterday. I want to send them back.", "YES"),
    ("My order was delivered 45 days ago. Can I still return it?", "NO"),
    ("I got a gift card last week. Can I return it?", "NO"),
    ("The socks I ordered came 3 days ago. Return possible?", "NO"),
    ("Delivered 29 days ago, is a return still possible?", "YES"),
]

PROMPT_V1 = (
    "You are ShopAssist, an online store's support assistant. "
    "Returns are accepted within 30 days of delivery. "
    "Begin your answer with YES or NO, then one sentence."
)


def answer(system, text):
    response = client.messages.create(
        model=MODEL,
        max_tokens=100,
        output_config={"effort": "low"},
        system=system,
        messages=[{"role": "user", "content": text}],
    )
    for block in response.content:
        if block.type == "text":
            return block.text


def evaluate(name, system):
    score = 0
    for text, expected in CASES:
        reply = answer(system, text)
        ok = reply.strip().upper().startswith(expected)
        score += ok
        print("PASS" if ok else "FAIL", "|", text[:45], "|", reply[:40])
    print(name, "score:", score, "/", len(CASES))


evaluate("v1", PROMPT_V1)

PROMPT_V2 = PROMPT_V1 + (
    " Gift cards and socks cannot be returned."
)
evaluate("v2", PROMPT_V2)