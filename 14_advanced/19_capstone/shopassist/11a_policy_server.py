import os
from mcp.server import FastMCP

# A second, separate MCP server: it knows the store's policies.
# 08a knows orders; this one knows rules. Claude can use both (11b).
server = FastMCP("shopassist-policies")

POLICY_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "policies")


def load_policies():
    """Read every policies/*.txt file and split it into lines (one rule each)."""
    rules = []
    for name in sorted(os.listdir(POLICY_DIR)):
        if name.endswith(".txt"):
            with open(os.path.join(POLICY_DIR, name), encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        rules.append((name, line.strip()))
    return rules


RULES = load_policies()


@server.tool()
def search_policy(question: str) -> str:
    """Search the store's returns, refunds and shipping policies.
    Input: a short question or keywords, e.g. "refund time" or
    "can socks be returned". Returns up to 3 matching policy lines,
    each with the file it came from, or "No matching policy".
    Use this before answering any question about store rules;
    use lookup_order instead for facts about one order."""
    # Very small "retrieval": score each rule by how many question words
    # it contains. A real system would use embeddings (see docassist).
    words = {w.strip("?.,!").lower() for w in question.split() if len(w) > 2}
    scored = []
    for source, rule in RULES:
        score = sum(1 for w in words if w in rule.lower())
        if score:
            scored.append((score, source, rule))
    scored.sort(reverse=True)
    if not scored:
        return "No matching policy"
    return "\n".join(f"[{source}] {rule}" for _, source, rule in scored[:3])


if __name__ == "__main__":
    server.run(transport="stdio")
