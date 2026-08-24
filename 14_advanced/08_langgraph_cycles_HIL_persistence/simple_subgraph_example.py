import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", category=PendingDeprecationWarning)
warnings.filterwarnings("ignore", category=FutureWarning)

from typing import TypedDict
from langgraph.graph import StateGraph, START, END

# Three independent subgraphs (savings, credit card, loan), each its own
# compiled StateGraph, invoked from adapter nodes in one parent graph.


class SavingsState(TypedDict):
    savings_summary: str


def check_savings(state: SavingsState) -> SavingsState:
    return {"savings_summary": "Savings: $12,500 balance"}


savings_builder = StateGraph(SavingsState)
savings_builder.add_node("check_savings", check_savings)
savings_builder.add_edge(START, "check_savings")
savings_builder.add_edge("check_savings", END)
savings_subgraph = savings_builder.compile()


class CreditCardState(TypedDict):
    credit_card_summary: str


def check_credit_card(state: CreditCardState) -> CreditCardState:
    return {"credit_card_summary": "Credit card: $850 owed, $5,000 limit"}


credit_card_builder = StateGraph(CreditCardState)
credit_card_builder.add_node("check_credit_card", check_credit_card)
credit_card_builder.add_edge(START, "check_credit_card")
credit_card_builder.add_edge("check_credit_card", END)
credit_card_subgraph = credit_card_builder.compile()


class LoanState(TypedDict):
    loan_summary: str


def check_loan(state: LoanState) -> LoanState:
    return {"loan_summary": "Loan: $18,000 remaining, next EMI due in 12 days"}


loan_builder = StateGraph(LoanState)
loan_builder.add_node("check_loan", check_loan)
loan_builder.add_edge(START, "check_loan")
loan_builder.add_edge("check_loan", END)
loan_subgraph = loan_builder.compile()


class CustomerState(TypedDict):
    savings_summary: str
    credit_card_summary: str
    loan_summary: str
    account_overview: str


def run_savings_subgraph(state: CustomerState) -> CustomerState:
    result = savings_subgraph.invoke({"savings_summary": ""})
    return {"savings_summary": result["savings_summary"]}


def run_credit_card_subgraph(state: CustomerState) -> CustomerState:
    result = credit_card_subgraph.invoke({"credit_card_summary": ""})
    return {"credit_card_summary": result["credit_card_summary"]}


def run_loan_subgraph(state: CustomerState) -> CustomerState:
    result = loan_subgraph.invoke({"loan_summary": ""})
    return {"loan_summary": result["loan_summary"]}


def combine(state: CustomerState) -> CustomerState:
    overview = f"{state['savings_summary']} | {state['credit_card_summary']} | {state['loan_summary']}"
    return {"account_overview": overview}


graph = StateGraph(CustomerState)
graph.add_node("savings_subgraph", run_savings_subgraph)
graph.add_node("credit_card_subgraph", run_credit_card_subgraph)
graph.add_node("loan_subgraph", run_loan_subgraph)
graph.add_node("combine", combine)

graph.add_edge(START, "savings_subgraph")
graph.add_edge(START, "credit_card_subgraph")
graph.add_edge(START, "loan_subgraph")
graph.add_edge("savings_subgraph", "combine")
graph.add_edge("credit_card_subgraph", "combine")
graph.add_edge("loan_subgraph", "combine")
graph.add_edge("combine", END)

app = graph.compile()

if __name__ == "__main__":
    result = app.invoke({
        "savings_summary": "",
        "credit_card_summary": "",
        "loan_summary": "",
        "account_overview": "",
    })
    print(result)
