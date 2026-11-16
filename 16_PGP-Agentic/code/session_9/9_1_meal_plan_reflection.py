# Self-reflection: generate -> verify -> revise, until score >= 9 or 4 attempts.
# The critique is grounded in REAL arithmetic:
#   - Python computes the calorie/protein targets (Mifflin-St Jeor BMR x activity)
#   - the LLM returns a STRUCTURED plan with per-item numbers, which Python sums
#   - the judge grades using those exact totals instead of re-estimating them
# Run with:  streamlit run 9_1_meal_plan_reflection.py
# A demo of iterative refinement - not medical or nutrition advice.

import streamlit as st
from dotenv import load_dotenv
from pydantic import BaseModel
from langchain_openai import ChatOpenAI

load_dotenv(override=True)

THRESHOLD = 9
MAX_ITERATIONS = 4

writer = ChatOpenAI(model="gpt-4o-mini", temperature=0.6)
judge = ChatOpenAI(model="gpt-4o-mini", temperature=0)

ACTIVITY = {"Sedentary": 1.2, "Lightly active": 1.375, "Moderately active": 1.55, "Very active": 1.725}


def calculate_targets(age: int, sex: str, weight: float, height: float, activity: str) -> dict:
    bmr = 10 * weight + 6.25 * height - 5 * age + (5 if sex == "Male" else -161)
    calories = bmr * ACTIVITY[activity]
    return {"calories": round(calories), "protein_g": round(weight * 1.2)}


class FoodItem(BaseModel):
    meal: str  # breakfast, lunch or dinner
    name: str
    quantity: str
    calories: float
    protein_g: float


class MealPlan(BaseModel):
    items: list[FoodItem]


class Critique(BaseModel):
    score: int  # 1-10
    feedback: str


def generate(targets: dict, preference: str, country: str, feedback: str = "") -> MealPlan:
    prompt = (
        f"Create a one-day meal plan (breakfast, lunch, dinner) using {preference} dishes common in "
        f"{country}. Targets: {targets['calories']} kcal and {targets['protein_g']} g protein. "
        "Give realistic calories and protein for every item - they will be summed and checked."
    )
    if feedback:
        prompt += f"\n\nYour previous plan fell short. Fix this: {feedback}"
    return writer.with_structured_output(MealPlan).invoke(prompt)


def verify(plan: MealPlan, totals: dict, targets: dict, preference: str, country: str) -> Critique:
    return judge.with_structured_output(Critique).invoke(
        f"Grade this meal plan 1-10. Score 9+ only if ALL hold:\n"
        f"- total calories {totals['calories']:.0f} are within 10% of {targets['calories']}\n"
        f"- total protein {totals['protein_g']:.0f} g is at least close to {targets['protein_g']} g\n"
        f"- every item is {preference} and fits {country}'s cuisine\n"
        f"- the meals are realistic and varied\n"
        "The totals were summed in code and are exact - do not recompute them.\n\n"
        f"Plan: {[(i.meal, i.name, i.quantity) for i in plan.items]}"
    )


# ---- Streamlit UI ----
st.title("Meal Plan Generator")
st.caption("Generate → verify → revise until the score is 9+ or 4 attempts are used. "
           "A demo, not medical advice.")

with st.form("profile"):
    c1, c2 = st.columns(2)
    age = c1.number_input("Age", 13, 100, 30)
    sex = c1.selectbox("Sex", ["Male", "Female"])
    weight = c1.number_input("Weight (kg)", 30.0, 250.0, 70.0)
    height = c2.number_input("Height (cm)", 120.0, 230.0, 170.0)
    activity = c2.selectbox("Activity level", list(ACTIVITY))
    preference = c2.selectbox("Diet", ["Vegetarian", "Non-Vegetarian", "Vegan"])
    country = st.text_input("Country", "India")
    submitted = st.form_submit_button("Generate")

if submitted:
    targets = calculate_targets(age, sex, weight, height, activity)
    st.write(f"**Targets:** {targets['calories']} kcal, {targets['protein_g']} g protein")

    feedback = ""
    for attempt in range(1, MAX_ITERATIONS + 1):
        with st.spinner(f"Attempt {attempt}..."):
            plan = generate(targets, preference, country, feedback)
            totals = {"calories": sum(i.calories for i in plan.items),
                      "protein_g": sum(i.protein_g for i in plan.items)}
            critique = verify(plan, totals, targets, preference, country)
        st.write(f"Attempt {attempt}: score **{critique.score}/10** "
                 f"({totals['calories']:.0f} kcal, {totals['protein_g']:.0f} g protein) - {critique.feedback}")
        if critique.score >= THRESHOLD:
            break
        feedback = critique.feedback

    st.subheader(f"Final plan (score {critique.score}/10)")
    st.table([i.model_dump() for i in plan.items])
    if critique.score < THRESHOLD:
        st.warning(f"Stopped after {MAX_ITERATIONS} attempts - showing the last plan.")
