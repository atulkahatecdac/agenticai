from typing import Literal
from pydantic import BaseModel
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv(override=True)

client = OpenAI()


class InvestmentRecommendation(BaseModel):
    risk_profile: Literal["Low", "Medium", "High"]
    recommended_product: str
    expected_return: float  # approximate annual return, in percent
    reason: str


def get_customer_profile() -> str:
    name = input("Customer name: ").strip()
    age = input("Age: ").strip()
    investment_amount = input("Investment amount ($): ").strip()
    time_horizon = input("Investment time horizon (years): ").strip()
    risk_tolerance = input("Risk tolerance (low/medium/high, or leave blank if unsure): ").strip()

    profile = (
        f"Name: {name}\n"
        f"Age: {age}\n"
        f"Investment amount: ${investment_amount}\n"
        f"Time horizon: {time_horizon} years\n"
    )
    if risk_tolerance:
        profile += f"Stated risk tolerance: {risk_tolerance}\n"
    else:
        profile += "Stated risk tolerance: not specified — infer a reasonable one from the other details\n"

    return profile


def recommend_investment(customer_profile: str) -> InvestmentRecommendation:
    response = client.responses.parse(
        model="gpt-4o-mini",
        input=[
            {
                "role": "system",
                "content": (
                    "You are a financial advisor assistant. Based on the customer profile, "
                    "recommend ONE suitable investment product, classify their risk profile, "
                    "and give a realistic expected annual return."
                ),
            },
            {"role": "user", "content": customer_profile},
        ],
        text_format=InvestmentRecommendation,  # Model must return an InvestmentRecommendation object
    )
    return response.output_parsed  # A validated InvestmentRecommendation instance, not a string


if __name__ == "__main__":
    customer_profile = get_customer_profile()
    recommendation = recommend_investment(customer_profile)

    print("\nInvestment Recommendation")
    print("--------------------------")
    print(f"Risk Profile        : {recommendation.risk_profile}")
    print(f"Recommended Product : {recommendation.recommended_product}")
    print(f"Expected Return (%) : {recommendation.expected_return}")
    print(f"Reason              : {recommendation.reason}")
