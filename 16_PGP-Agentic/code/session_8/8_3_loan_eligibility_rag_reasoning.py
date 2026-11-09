# pip install chromadb openai python-dotenv

import os
import sys
import csv
import json
import chromadb
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv(override=True)
sys.stdout.reconfigure(encoding="utf-8")  # ₹ isn't in Windows' default console codepage

DATA_DIR = os.path.join(os.path.dirname(__file__), "loan_data")
MODEL = "gpt-4o-mini"
openai_client = OpenAI()

# =====================================================================
# Retrieval + Reasoning for home loan eligibility.
#
# RETRIEVAL provides the facts, from two different kinds of source -
# realistically, "retrieval" isn't always a vector search:
#   - Semantic search (ChromaDB) over the bank's policy + RBI guideline
#     documents, for the textual rules and their justification.
#   - Structured lookups (CSV "databases") for the customer's actual
#     income/credit score/existing EMIs, and the current interest rate
#     card - the kind of query a core-banking system would answer, not
#     something to trust from the customer's own self-report.
#
# REASONING is deterministic Python, not the LLM: DTI ratio, EMI, and
# maximum eligible loan amount are all real financial formulas computed
# in code. An LLM is only used at the very end, to EXPLAIN a decision
# that has already been computed - never to compute or guess numbers
# itself. That split (compute deterministically, explain with an LLM)
# is what makes an eligibility assistant like this trustworthy enough
# to actually use.
# =====================================================================

DTI_CAP_SALARIED = 0.50
DTI_CAP_SELF_EMPLOYED = 0.45
MIN_CREDIT_SCORE = 650


def format_inr(amount: float) -> str:
    """Format a number using Indian digit grouping, e.g. 5000000 -> '₹50,00,000'."""
    amount = int(round(amount))
    sign = "-" if amount < 0 else ""
    digits = str(abs(amount))
    last3, rest = digits[-3:], digits[:-3]
    groups = []
    while len(rest) > 2:
        groups.insert(0, rest[-2:])
        rest = rest[:-2]
    if rest:
        groups.insert(0, rest)
    formatted = ",".join(groups + [last3]) if groups else last3
    return f"{sign}₹{formatted}"


# ---- Structured retrieval: customer profile + interest rate card ----
def load_csv(filename: str) -> list[dict]:
    with open(os.path.join(DATA_DIR, filename), newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


CUSTOMERS = load_csv("customers.csv")
RATE_CARD = load_csv("interest_rate_card.csv")


def get_customer_profile(customer_id: str) -> dict:
    for row in CUSTOMERS:
        if row["customer_id"] == customer_id:
            return row
    raise ValueError(f"No customer record found for {customer_id}")


def get_credit_band_and_rate(credit_score: int) -> tuple[str, float | None]:
    for row in RATE_CARD:
        if int(row["credit_score_min"]) <= credit_score <= int(row["credit_score_max"]):
            rate = float(row["annual_interest_rate_percent"]) if row["annual_interest_rate_percent"] else None
            return row["band"], rate
    raise ValueError(f"No interest rate band found for credit score {credit_score}")


# ---- Semantic retrieval: policy + RBI guideline documents ----
def load_policy_index():
    collection = chromadb.Client().create_collection("loan_policy")

    chunks = []
    for filename in ["loan_eligibility_policy.md", "rbi_guidelines.md"]:
        text = open(os.path.join(DATA_DIR, filename), encoding="utf-8").read()
        raw_sections = text.split("\n## ")
        sections = [raw_sections[0]] + [f"## {s}" for s in raw_sections[1:]]
        for i, section in enumerate(sections):
            chunks.append({"id": f"{filename}-{i}", "text": section.strip(), "source": filename})

    collection.add(
        ids=[c["id"] for c in chunks],
        documents=[c["text"] for c in chunks],
        metadatas=[{"source": c["source"]} for c in chunks],
    )
    return collection


POLICY_INDEX = load_policy_index()


def retrieve_policy_context(query: str, top_k: int = 3) -> list[str]:
    results = POLICY_INDEX.query(query_texts=[query], n_results=top_k)
    return results["documents"][0]


# ---- Reasoning: real underwriting math, not an LLM guess ----
def calculate_emi(principal: float, annual_rate_percent: float, tenure_years: int) -> float:
    monthly_rate = annual_rate_percent / 12 / 100
    months = tenure_years * 12
    factor = (1 + monthly_rate) ** months
    return principal * monthly_rate * factor / (factor - 1)


def calculate_max_principal(max_emi: float, annual_rate_percent: float, tenure_years: int) -> float:
    if max_emi <= 0:
        return 0.0
    monthly_rate = annual_rate_percent / 12 / 100
    months = tenure_years * 12
    factor = (1 + monthly_rate) ** months
    return max_emi * (factor - 1) / (monthly_rate * factor)


def get_max_ltv(loan_amount: float) -> float:
    if loan_amount <= 30_00_000:
        return 0.90
    if loan_amount <= 75_00_000:
        return 0.80
    return 0.75


def evaluate_application(customer: dict, loan_amount_requested: float, tenure_years: int, property_value: float | None) -> dict:
    credit_score = int(customer["credit_score"])
    band, annual_rate = get_credit_band_and_rate(credit_score)
    monthly_income = float(customer["annual_salary"]) / 12
    existing_emis = float(customer["existing_monthly_emis"])
    dti_cap = DTI_CAP_SELF_EMPLOYED if customer["employment_type"] == "Self-Employed" else DTI_CAP_SALARIED

    if credit_score < MIN_CREDIT_SCORE:
        return {
            "decision": "declined",
            "reason": f"Credit score {credit_score} is below the minimum policy threshold of {MIN_CREDIT_SCORE}.",
            "credit_band": band, "monthly_income": monthly_income, "existing_emis": existing_emis,
            "dti_cap": dti_cap, "loan_amount_requested": loan_amount_requested, "tenure_years": tenure_years,
        }

    max_affordable_emi = dti_cap * monthly_income - existing_emis
    max_eligible_loan_dti = calculate_max_principal(max_affordable_emi, annual_rate, tenure_years)

    max_eligible_loan_ltv = None
    if property_value:
        max_eligible_loan_ltv = property_value * get_max_ltv(loan_amount_requested)

    candidates = [v for v in (max_eligible_loan_dti, max_eligible_loan_ltv) if v is not None]
    max_eligible_loan = min(candidates)

    proposed_emi = calculate_emi(loan_amount_requested, annual_rate, tenure_years)
    dti_at_requested = round((existing_emis + proposed_emi) / monthly_income, 4)

    if max_affordable_emi <= 0:
        decision, reason = "declined", "No affordable EMI capacity remains after existing monthly obligations."
    elif loan_amount_requested <= max_eligible_loan:
        decision, reason = "approved", "Requested amount is within the applicant's maximum eligible loan amount."
    else:
        decision, reason = (
            "conditionally_approved",
            "Requested amount exceeds the maximum eligible loan amount for the given tenure.",
        )

    return {
        "decision": decision,
        "reason": reason,
        "credit_band": band,
        "annual_interest_rate_percent": annual_rate,
        "monthly_income": round(monthly_income, 2),
        "existing_monthly_emis": existing_emis,
        "dti_cap": dti_cap,
        "max_affordable_emi": round(max_affordable_emi, 2),
        "max_eligible_loan_by_dti": round(max_eligible_loan_dti, 2),
        "max_eligible_loan_by_ltv": round(max_eligible_loan_ltv, 2) if max_eligible_loan_ltv else None,
        "max_eligible_loan": round(max_eligible_loan, 2),
        "proposed_emi": round(proposed_emi, 2),
        "dti_at_requested_amount": dti_at_requested,
        "loan_amount_requested": loan_amount_requested,
        "tenure_years": tenure_years,
        "property_value": property_value,
    }


# ---- LLM: explain the already-computed decision, invent nothing ----
def explain_decision(customer_query: str, decision: dict, policy_context: list[str]) -> str:
    response = openai_client.responses.create(
        model=MODEL,
        instructions=(
            "You are a home loan advisor. Explain this eligibility decision to the customer "
            "in clear, friendly language, in Indian Rupees. Use ONLY the numbers in DECISION "
            "DATA below - never compute, adjust, or guess a number yourself. Cite the relevant "
            "rule(s) from POLICY CONTEXT to justify the decision. If conditionally approved or "
            "declined, clearly suggest a concrete next step."
        ),
        input=(
            f"Customer's question: {customer_query}\n\n"
            f"POLICY CONTEXT:\n{chr(10).join(policy_context)}\n\n"
            f"DECISION DATA (ground truth, already computed - do not recompute):\n{json.dumps(decision, indent=2)}"
        ),
    )
    return response.output_text


def run_application(customer_query: str, customer_id: str, loan_amount_requested: float, tenure_years: int, property_value: float | None = None):
    customer = get_customer_profile(customer_id)
    decision = evaluate_application(customer, loan_amount_requested, tenure_years, property_value)
    policy_context = retrieve_policy_context(
        "home loan DTI FOIR credit score eligibility maximum loan amount LTV"
    )

    print("=" * 70)
    print(f"Customer: {customer['name']} ({customer_id})")
    print(f"Question: {customer_query}\n")
    print(f"Retrieved profile: salary {format_inr(float(customer['annual_salary']))}/yr, "
          f"credit score {customer['credit_score']}, existing EMIs {format_inr(float(customer['existing_monthly_emis']))}/mo "
          f"({customer['existing_loans_description']})")
    print(f"Computed: DTI cap {decision['dti_cap']:.0%}, max eligible loan "
          f"{format_inr(decision.get('max_eligible_loan', 0))}, decision = {decision['decision'].upper()}\n")

    print(explain_decision(customer_query, decision, policy_context))
    print()


if __name__ == "__main__":
    run_application(
        customer_query="Can I get a ₹50 lakh home loan? My salary is ₹18 lakh/year, "
                       "I already have a car loan, and my credit score is 760.",
        customer_id="CUST1001",
        loan_amount_requested=50_00_000,
        tenure_years=20,
    )

    run_application(
        customer_query="I'd like a ₹40 lakh home loan over 15 years.",
        customer_id="CUST1005",  # credit score 620 - below policy floor
        loan_amount_requested=40_00_000,
        tenure_years=15,
    )

    run_application(
        customer_query="Can I get an ₹80 lakh home loan over 15 years? "
                       "The property I'm buying is valued at ₹1 crore.",
        customer_id="CUST1009",  # decent credit, but likely exceeds DTI-based eligibility
        loan_amount_requested=80_00_000,
        tenure_years=15,
        property_value=1_00_00_000,
    )
