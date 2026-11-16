# pip install chromadb openai python-dotenv

# Retrieval + Reasoning for home loan eligibility.
#   RETRIEVAL finds the facts: the customer's profile and the interest rate
#     (CSV lookups, like a core-banking query) and the policy rules
#     (semantic search over the policy + RBI documents in ChromaDB).
#   REASONING is plain Python: DTI, EMI and the maximum loan are computed
#     in code. The LLM only EXPLAINS the decision - it never does the maths.

import os
import sys
import csv
import json
import chromadb
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv(override=True)
sys.stdout.reconfigure(encoding="utf-8")  # ₹ isn't in Windows' default console codepage

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "loan_data")
client = OpenAI()

MIN_CREDIT_SCORE = 650
MAX_DTI = 0.50  # all EMIs together may use at most 50% of monthly income


def lakh(amount: float) -> str:
    return f"₹{amount / 1_00_000:.1f} lakh"


# ---- Retrieval 1: structured lookups (customer + rate card) ----
def load_csv(name: str) -> list[dict]:
    with open(os.path.join(DATA_DIR, name), newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


CUSTOMERS = {row["customer_id"]: row for row in load_csv("customers.csv")}
RATE_CARD = load_csv("interest_rate_card.csv")


def interest_rate_for(score: int) -> float:
    for row in RATE_CARD:
        if int(row["credit_score_min"]) <= score <= int(row["credit_score_max"]) and row["annual_interest_rate_percent"]:
            return float(row["annual_interest_rate_percent"])
    return 0.0  # below the lowest lending band


# ---- Retrieval 2: semantic search over the policy documents ----
policy_db = chromadb.Client().create_collection("loan_policy")
for name in ["loan_eligibility_policy.md", "rbi_guidelines.md"]:
    sections = open(os.path.join(DATA_DIR, name), encoding="utf-8").read().split("\n## ")
    policy_db.add(ids=[f"{name}-{i}" for i in range(len(sections))], documents=sections)


def retrieve_policy(query: str) -> list[str]:
    return policy_db.query(query_texts=[query], n_results=3)["documents"][0]


# ---- Reasoning: deterministic underwriting maths ----
def emi(principal: float, rate: float, years: int) -> float:
    r, n = rate / 1200, years * 12
    return principal * r * (1 + r) ** n / ((1 + r) ** n - 1)


def evaluate(customer: dict, amount: float, years: int) -> dict:
    score = int(customer["credit_score"])
    income = float(customer["annual_salary"]) / 12
    existing = float(customer["existing_monthly_emis"])

    if score < MIN_CREDIT_SCORE:
        return {"decision": "declined", "reason": f"Credit score {score} is below the minimum of {MIN_CREDIT_SCORE}."}

    rate = interest_rate_for(score)
    affordable_emi = max(MAX_DTI * income - existing, 0)
    max_loan = affordable_emi / emi(1, rate, years)  # EMI is linear in principal
    new_emi = emi(amount, rate, years)

    return {
        "decision": "approved" if amount <= max_loan else "conditionally_approved",
        "interest_rate_percent": rate,
        "monthly_income": round(income),
        "existing_emis": round(existing),
        "proposed_emi": round(new_emi),
        "dti_with_new_loan": round((existing + new_emi) / income, 2),
        "dti_limit": MAX_DTI,
        "max_eligible_loan": round(max_loan),
    }


# ---- LLM: explain the computed decision, invent nothing ----
def explain(question: str, decision: dict, policy: list[str]) -> str:
    response = client.responses.create(
        model="gpt-4o-mini",
        instructions=(
            "You are a home loan advisor. Explain this decision to the customer in plain language, "
            "in Indian Rupees. Use ONLY the numbers in DECISION - never calculate your own. "
            "Cite the relevant POLICY rule. If not fully approved, suggest one concrete next step."
        ),
        input=f"Question: {question}\n\nPOLICY:\n{chr(10).join(policy)}\n\nDECISION:\n{json.dumps(decision, indent=2)}",
    )
    return response.output_text


def run(question: str, customer_id: str, amount: float, years: int):
    customer = CUSTOMERS[customer_id]
    decision = evaluate(customer, amount, years)
    policy = retrieve_policy("home loan eligibility credit score DTI maximum loan amount")

    print("=" * 70)
    print(f"{customer['name']}: {question}")
    print(f"Profile: salary {lakh(float(customer['annual_salary']))}/yr, credit score {customer['credit_score']}, "
          f"existing EMIs ₹{customer['existing_monthly_emis']}/mo")
    if "max_eligible_loan" in decision:
        print(f"Computed: max eligible {lakh(decision['max_eligible_loan'])}, DTI {decision['dti_with_new_loan']:.0%}")
    print(f"Decision: {decision['decision'].upper()}\n")
    print(explain(question, decision, policy), "\n")


if __name__ == "__main__":
    run("Can I get a ₹50 lakh home loan? My salary is ₹18 lakh a year, I already have a car loan, "
        "and my credit score is 760.", "CUST1001", 50_00_000, 20)
    run("I'd like a ₹40 lakh home loan over 15 years.", "CUST1005", 40_00_000, 15)   # score 620
    run("Can I get an ₹80 lakh home loan over 15 years?", "CUST1009", 80_00_000, 15)  # exceeds DTI
