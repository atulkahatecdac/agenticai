# Self-reflection in LangGraph: generate -> verify -> revise, until score >= 9
# or 4 attempts. The critique is grounded in REAL arithmetic:
#   - Python computes the calorie/protein targets (Mifflin-St Jeor BMR x activity)
#   - the LLM returns a STRUCTURED plan with per-item numbers, which Python sums
#   - the judge grades using those exact totals instead of re-estimating them
# Run with:  streamlit run 12_1_meal_plan_reflection.py
# A demo of iterative refinement - not medical or nutrition advice.

from typing import TypedDict
import streamlit as st
from dotenv import load_dotenv
from pydantic import BaseModel
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, START, END

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


class State(TypedDict, total=False):
    targets: dict
    preference: str
    country: str
    plan: MealPlan
    totals: dict
    score: int
    feedback: str
    attempt: int


def generate(state: State) -> dict:
    t = state["targets"]
    prompt = (
        f"Create a one-day meal plan (breakfast, lunch, dinner) using {state['preference']} dishes common in "
        f"{state['country']}. Targets: {t['calories']} kcal and {t['protein_g']} g protein. "
        "Give realistic calories and protein for every item - they will be summed and checked."
    )
    if state.get("feedback"):
        prompt += f"\n\nYour previous plan fell short. Fix this: {state['feedback']}"
    plan = writer.with_structured_output(MealPlan).invoke(prompt)
    totals = {"calories": sum(i.calories for i in plan.items), "protein_g": sum(i.protein_g for i in plan.items)}
    return {"plan": plan, "totals": totals, "attempt": state.get("attempt", 0) + 1}


def verify(state: State) -> dict:
    t, totals = state["targets"], state["totals"]
    critique = judge.with_structured_output(Critique).invoke(
        f"Grade this meal plan 1-10. Score 9+ only if ALL hold:\n"
        f"- total calories {totals['calories']:.0f} are within 10% of {t['calories']}\n"
        f"- total protein {totals['protein_g']:.0f} g is at least close to {t['protein_g']} g\n"
        f"- every item is {state['preference']} and fits {state['country']}'s cuisine\n"
        f"- the meals are realistic and varied\n"
        "The totals were summed in code and are exact - do not recompute them.\n\n"
        f"Plan: {[(i.meal, i.name, i.quantity) for i in state['plan'].items]}"
    )
    return {"score": critique.score, "feedback": critique.feedback}


def should_continue(state: State) -> str:
    return "done" if state["score"] >= THRESHOLD or state["attempt"] >= MAX_ITERATIONS else "revise"


graph = StateGraph(State)
graph.add_node("generate", generate)
graph.add_node("verify", verify)
graph.add_edge(START, "generate")
graph.add_edge("generate", "verify")
graph.add_conditional_edges("verify", should_continue, {"revise": "generate", "done": END})
app = graph.compile()


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

    state: State = {"targets": targets, "preference": preference, "country": country}
    with st.spinner("Generating and refining..."):
        for step in app.stream(state):  # one update per node run
            for node, update in step.items():
                state.update(update)
                if node == "verify":
                    st.write(f"Attempt {state['attempt']}: score **{state['score']}/10** "
                             f"({state['totals']['calories']:.0f} kcal, {state['totals']['protein_g']:.0f} g protein)"
                             f" - {state['feedback']}")

    st.subheader(f"Final plan (score {state['score']}/10)")
    st.table([i.model_dump() for i in state["plan"].items])
    if state["score"] < THRESHOLD:
        st.warning(f"Stopped after {MAX_ITERATIONS} attempts - showing the last plan.")
