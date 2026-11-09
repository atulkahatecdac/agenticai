from typing import TypedDict

import streamlit as st
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, START, END
from pydantic import BaseModel, Field

load_dotenv(override=True)

# =====================================================================
# Meal plan generator: generate -> verify -> (revise or stop), the same
# reflection shape as multi_turn_reflection.py in this folder, but the
# "critique" here is grounded in REAL arithmetic, not just an LLM's
# opinion. Calorie/macro TARGETS (Mifflin-St Jeor BMR x activity
# multiplier, then macro splits adjusted for the stated health
# condition) are computed in plain Python before any LLM call. The
# generate node asks for a STRUCTURED meal plan (per-item calories/
# protein/carbs/fat, not freeform prose) specifically so the totals can
# be SUMMED in Python and checked against those targets - the LLM never
# has to be trusted to have added its own numbers correctly. verify
# feeds those computed totals into the critique prompt so the LLM's
# qualitative judgment (dietary-preference compliance, health-condition
# appropriateness, meal realism) is grounded in numbers that are known
# to be right, not re-estimated from scratch.
#
# Not medical advice - a demo of constraint-directed iterative
# refinement, not a clinical nutrition tool. See the in-app disclaimer.
# =====================================================================

THRESHOLD = 9
MAX_ITERATIONS = 4
CALORIE_TOLERANCE = 0.10  # +/-10% counts as "on target"

writer_llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.6)
judge_llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

ACTIVITY_MULTIPLIERS = {
    "Sedentary (little/no exercise)": 1.2,
    "Lightly active (1-3 days/week)": 1.375,
    "Moderately active (3-5 days/week)": 1.55,
    "Very active (6-7 days/week)": 1.725,
}

PROTEIN_G_PER_KG = {
    "Sedentary (little/no exercise)": 0.8,
    "Lightly active (1-3 days/week)": 1.0,
    "Moderately active (3-5 days/week)": 1.2,
    "Very active (6-7 days/week)": 1.6,
}

HEALTH_CONDITIONS = [
    "None",
    "Diabetes (Type 2)",
    "Hypertension",
    "High Cholesterol",
    "Hypothyroidism",
    "Obesity / Weight Management",
]


def calculate_targets(
    age: int, sex: str, weight_kg: float, height_cm: float, activity_level: str, conditions: list[str]
) -> dict:
    """All real arithmetic, no LLM involved - Mifflin-St Jeor BMR, activity-scaled TDEE,
    then macro grams derived from body weight/calories, with a couple of well-known,
    named adjustments for the stated health condition(s)."""
    if sex == "Male":
        bmr = 10 * weight_kg + 6.25 * height_cm - 5 * age + 5
    else:
        bmr = 10 * weight_kg + 6.25 * height_cm - 5 * age - 161

    tdee = bmr * ACTIVITY_MULTIPLIERS[activity_level]

    calorie_target = tdee
    if "Obesity / Weight Management" in conditions:
        calorie_target = tdee - 500  # moderate ~0.5kg/week deficit

    protein_g_per_kg = PROTEIN_G_PER_KG[activity_level]
    if "Obesity / Weight Management" in conditions:
        protein_g_per_kg += 0.4  # preserve lean mass under a calorie deficit
    protein_g = weight_kg * protein_g_per_kg
    protein_cal = protein_g * 4

    fat_pct = 0.30
    if "High Cholesterol" in conditions:
        fat_pct = 0.25  # lean toward less total fat
    fat_cal = calorie_target * fat_pct
    fat_g = fat_cal / 9

    carb_cal = calorie_target - protein_cal - fat_cal
    if "Diabetes (Type 2)" in conditions:
        carb_cal = min(carb_cal, calorie_target * 0.40)  # cap carb share
    carb_g = max(carb_cal, 0) / 4

    return {
        "bmr": round(bmr),
        "tdee": round(tdee),
        "calories": round(calorie_target),
        "protein_g": round(protein_g),
        "carbs_g": round(carb_g),
        "fat_g": round(fat_g),
    }


class FoodItem(BaseModel):
    name: str = Field(description="Food/dish name, e.g. 'Grilled paneer with quinoa'.")
    quantity: str = Field(description="Portion size, e.g. '150g' or '1 cup'.")
    calories: float
    protein_g: float
    carbs_g: float
    fat_g: float


class MealPlan(BaseModel):
    breakfast: list[FoodItem]
    lunch: list[FoodItem]
    dinner: list[FoodItem]


def totals_of(plan: MealPlan) -> dict:
    items = plan.breakfast + plan.lunch + plan.dinner
    return {
        "calories": sum(i.calories for i in items),
        "protein_g": sum(i.protein_g for i in items),
        "carbs_g": sum(i.carbs_g for i in items),
        "fat_g": sum(i.fat_g for i in items),
    }


class MealPlanState(TypedDict):
    targets: dict
    dietary_pref: str
    conditions: list[str]
    country: str
    plan: MealPlan
    totals: dict
    feedback: str
    score: int
    iteration: int


def generate(state: MealPlanState) -> MealPlanState:
    targets = state["targets"]
    base = f"""Create a one-day meal plan (breakfast, lunch, dinner) for this person.

Country: {state['country']} - prefer foods, dishes, and ingredients that are commonly eaten and
easy to find in this country, not generic/Western defaults unless that IS this country's cuisine.
Dietary preference: {state['dietary_pref']}
Health condition(s): {', '.join(state['conditions'])}

Daily targets:
- Calories: {targets['calories']} kcal
- Protein: {targets['protein_g']} g
- Carbohydrates: {targets['carbs_g']} g
- Fat: {targets['fat_g']} g

For every food item, state a realistic per-item calorie/protein/carb/fat estimate - these will
be summed and checked, so make your own per-item numbers internally consistent (protein_g*4 +
carbs_g*4 + fat_g*9 should be close to the item's own calories)."""

    if state.get("feedback"):
        prompt = f"""{base}

Your previous attempt scored below the bar. Revise the plan using this feedback - keep what
worked, fix what didn't:

Previous totals: {state['totals']}
Feedback: {state['feedback']}"""
    else:
        prompt = base

    plan = writer_llm.with_structured_output(MealPlan).invoke(prompt)
    totals = totals_of(plan)
    return {"plan": plan, "totals": totals, "iteration": state["iteration"] + 1}


class Critique(BaseModel):
    score: int = Field(description="Quality score 1-10.")
    feedback: str = Field(description="Specific, actionable feedback for improving the plan.")


def verify(state: MealPlanState) -> MealPlanState:
    targets = state["targets"]
    totals = state["totals"]
    lo, hi = 1 - CALORIE_TOLERANCE, 1 + CALORIE_TOLERANCE

    prompt = f"""Grade this one-day meal plan 1-10. Only score 9+ if ALL of these hold:
- Total calories ({totals['calories']:.0f}) are within {int(CALORIE_TOLERANCE*100)}% of the
  target ({targets['calories']} kcal, i.e. between {targets['calories']*lo:.0f} and
  {targets['calories']*hi:.0f}) - these totals were computed by summing the plan's own stated
  per-item values in code, they are exact, do not recompute them yourself
- Protein ({totals['protein_g']:.0f}g) meets or comes close to the target
  ({targets['protein_g']}g) - err toward meeting/exceeding protein rather than falling short
- Carbs ({totals['carbs_g']:.0f}g) and fat ({totals['fat_g']:.0f}g) are reasonably close to
  their targets ({targets['carbs_g']}g, {targets['fat_g']}g)
- Every food item is consistent with the dietary preference: {state['dietary_pref']}
- Food choices are appropriate for the stated health condition(s): {', '.join(state['conditions'])}
  (e.g. limited refined sugar/high-GI carbs for diabetes, limited sodium for hypertension,
  limited saturated fat for high cholesterol)
- Food choices fit {state['country']}'s cuisine - dishes/ingredients someone in that country would
  actually recognize and be able to find, not generic/Western defaults unless that IS this
  country's cuisine
- The three meals are realistic, varied, and nutritionally sensible - not just a checklist of
  items chosen to hit a number

Meal plan:
Breakfast: {state['plan'].breakfast}
Lunch: {state['plan'].lunch}
Dinner: {state['plan'].dinner}"""

    verdict = judge_llm.with_structured_output(Critique).invoke(prompt)
    return {"score": verdict.score, "feedback": verdict.feedback}


def should_continue(state: MealPlanState) -> str:
    if state["score"] >= THRESHOLD or state["iteration"] >= MAX_ITERATIONS:
        return "done"
    return "revise"


graph = StateGraph(MealPlanState)
graph.add_node("generate", generate)
graph.add_node("verify", verify)
graph.add_edge(START, "generate")
graph.add_edge("generate", "verify")
graph.add_conditional_edges("verify", should_continue, {"revise": "generate", "done": END})
app = graph.compile()


# =====================================================================
# Streamlit UI.
# =====================================================================

st.set_page_config(page_title="Meal Plan Generator", page_icon="\U0001F957")
st.title("Meal Plan Generator")
st.caption(
    "Generate -> verify -> revise, looping until the plan hits your calorie/macro targets or "
    "4 attempts are used. Verification is grounded in real computed totals, not an LLM's opinion "
    "of its own arithmetic."
)
st.info(
    "This is a general wellness planning demo, not medical advice. For a health "
    "condition-specific diet, consult a registered dietitian or physician.",
    icon="⚠️",
)

with st.form("profile_form"):
    col1, col2 = st.columns(2)
    with col1:
        age = st.number_input("Age", min_value=13, max_value=100, value=30)
        weight_kg = st.number_input("Weight (kg)", min_value=30.0, max_value=250.0, value=70.0, step=0.5)
        sex = st.selectbox("Sex (needed for the BMR formula)", ["Male", "Female"])
    with col2:
        height_cm = st.number_input("Height (cm)", min_value=120.0, max_value=230.0, value=170.0, step=0.5)
        activity_level = st.selectbox("Activity level (needed for the TDEE formula)", list(ACTIVITY_MULTIPLIERS))
        dietary_pref = st.selectbox("Dietary preference", ["Vegetarian", "Non-Vegetarian", "Vegan"])

    conditions = st.multiselect("Health condition(s)", HEALTH_CONDITIONS, default=["None"])
    country = st.text_input("Country (for regionally appropriate food suggestions)", value="India")
    submitted = st.form_submit_button("Generate My Meal Plan")

if submitted:
    conditions = [c for c in conditions if c != "None"] or ["None"]
    targets = calculate_targets(age, sex, weight_kg, height_cm, activity_level, conditions)

    st.subheader("Your daily targets")
    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("BMR", f"{targets['bmr']} kcal")
    m2.metric("TDEE", f"{targets['tdee']} kcal")
    m3.metric("Calorie target", f"{targets['calories']} kcal")
    m4.metric("Protein target", f"{targets['protein_g']} g")
    m5.metric("Carbs / Fat target", f"{targets['carbs_g']}g / {targets['fat_g']}g")

    progress_area = st.empty()
    state: MealPlanState = {
        "targets": targets,
        "dietary_pref": dietary_pref,
        "conditions": conditions,
        "country": country.strip() or "India",
        "plan": None,  # type: ignore[typeddict-item]
        "totals": {},
        "feedback": "",
        "score": 0,
        "iteration": 0,
    }

    with st.spinner("Generating and refining your meal plan..."):
        log_lines = []
        for step_output in app.stream(state):
            for node_name, node_state in step_output.items():
                state.update(node_state)
                if node_name == "verify":
                    log_lines.append(f"Attempt {state['iteration']}: score {state['score']}/10 - {state['feedback']}")
                    progress_area.text("\n".join(log_lines))

    st.subheader(f"Final meal plan (score {state['score']}/10, {state['iteration']} attempt(s))")

    totals = state["totals"]
    t1, t2, t3, t4 = st.columns(4)
    t1.metric("Total calories", f"{totals['calories']:.0f} kcal", f"{totals['calories']-targets['calories']:+.0f}")
    t2.metric("Total protein", f"{totals['protein_g']:.0f} g", f"{totals['protein_g']-targets['protein_g']:+.0f}")
    t3.metric("Total carbs", f"{totals['carbs_g']:.0f} g", f"{totals['carbs_g']-targets['carbs_g']:+.0f}")
    t4.metric("Total fat", f"{totals['fat_g']:.0f} g", f"{totals['fat_g']-targets['fat_g']:+.0f}")

    plan: MealPlan = state["plan"]
    for meal_name, items in [("Breakfast", plan.breakfast), ("Lunch", plan.lunch), ("Dinner", plan.dinner)]:
        st.markdown(f"### {meal_name}")
        st.table(
            [
                {
                    "Item": i.name,
                    "Qty": i.quantity,
                    "Calories": i.calories,
                    "Protein (g)": i.protein_g,
                    "Carbs (g)": i.carbs_g,
                    "Fat (g)": i.fat_g,
                }
                for i in items
            ]
        )

    if state["score"] < THRESHOLD:
        st.warning(
            f"Reached the {MAX_ITERATIONS}-attempt limit without hitting the quality bar "
            f"(score {state['score']}/10) - showing the last, best attempt rather than looping forever."
        )
