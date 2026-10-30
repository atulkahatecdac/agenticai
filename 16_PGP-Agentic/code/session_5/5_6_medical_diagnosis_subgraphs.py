import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", category=PendingDeprecationWarning)
warnings.filterwarnings("ignore", category=FutureWarning)

import base64
import csv
import os
import sys
from typing import TypedDict
from dotenv import load_dotenv
from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, START, END

load_dotenv(override=True)
sys.stdout.reconfigure(encoding="utf-8")

llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.2)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PATIENT_DATA_PATH = os.path.join(BASE_DIR, "patient_data.csv")
LAB_RESULTS_PATH = os.path.join(BASE_DIR, "lab_results.csv")
XRAY_PATH = os.path.join(BASE_DIR, "Chest-x-ray.jpg")

# Real-world subgraph example: medical_history and lab_analysis are each
# their own compiled StateGraph with a narrow state schema, run in
# parallel with analyze_xray, then fan into diagnosis -> prescription.
# NOT a real diagnostic tool.


class MedicalState(TypedDict):
    patient_id: str
    patient_data: str
    history_summary: str
    lab_data: str
    abnormal_flags: list[str]
    lab_summary: str
    xray_analysis: str
    diagnosis: str
    prescription: str


class HistoryState(TypedDict):
    patient_data: str
    history_summary: str


def load_patient_data(state: HistoryState) -> HistoryState:
    with open(PATIENT_DATA_PATH, encoding="utf-8") as f:
        return {"patient_data": f.read()}


def summarize_history(state: HistoryState) -> HistoryState:
    prompt = f"Summarize this patient's history, symptoms and vitals for a physician:\n\n{state['patient_data']}"
    response = llm.invoke(prompt)
    return {"history_summary": response.content}


history_builder = StateGraph(HistoryState)
history_builder.add_node("load_patient_data", load_patient_data)
history_builder.add_node("summarize_history", summarize_history)
history_builder.add_edge(START, "load_patient_data")
history_builder.add_edge("load_patient_data", "summarize_history")
history_builder.add_edge("summarize_history", END)
medical_history_subgraph = history_builder.compile()


def run_medical_history(state: MedicalState) -> MedicalState:
    result = medical_history_subgraph.invoke({"patient_data": "", "history_summary": ""})
    return {"patient_data": result["patient_data"], "history_summary": result["history_summary"]}


class LabState(TypedDict):
    lab_data: str
    abnormal_flags: list[str]
    lab_summary: str


def load_lab_results(state: LabState) -> LabState:
    with open(LAB_RESULTS_PATH, encoding="utf-8") as f:
        return {"lab_data": f.read()}


def flag_abnormal_results(state: LabState) -> LabState:
    flags = []
    with open(LAB_RESULTS_PATH, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            result, low, high = float(row["Result"]), float(row["Normal Range Low"]), float(row["Normal Range High"])
            if result < low or result > high:
                direction = "high" if result > high else "low"
                flags.append(f"{row['Test']}: {row['Result']} {row['Unit']} ({direction}, normal {low}-{high})")
    return {"abnormal_flags": flags}


def summarize_labs(state: LabState) -> LabState:
    flags_text = "\n".join(state["abnormal_flags"]) or "All values within normal range."
    prompt = f"Interpret this lab panel for a physician, focusing on:\n{flags_text}\n\nFull panel:\n{state['lab_data']}"
    response = llm.invoke(prompt)
    return {"lab_summary": response.content}


lab_builder = StateGraph(LabState)
lab_builder.add_node("load_lab_results", load_lab_results)
lab_builder.add_node("flag_abnormal_results", flag_abnormal_results)
lab_builder.add_node("summarize_labs", summarize_labs)
lab_builder.add_edge(START, "load_lab_results")
lab_builder.add_edge("load_lab_results", "flag_abnormal_results")
lab_builder.add_edge("flag_abnormal_results", "summarize_labs")
lab_builder.add_edge("summarize_labs", END)
lab_analysis_subgraph = lab_builder.compile()


def run_lab_analysis(state: MedicalState) -> MedicalState:
    result = lab_analysis_subgraph.invoke({"lab_data": "", "abnormal_flags": [], "lab_summary": ""})
    return {
        "lab_data": result["lab_data"],
        "abnormal_flags": result["abnormal_flags"],
        "lab_summary": result["lab_summary"],
    }


def analyze_xray(state: MedicalState) -> MedicalState:
    with open(XRAY_PATH, "rb") as f:
        image_b64 = base64.b64encode(f.read()).decode("utf-8")
    message = HumanMessage(content=[
        {"type": "text", "text": "Preliminary read of this chest X-ray: note any signs of infection, "
                                  "consolidation, effusion or other abnormalities. State this is AI-assisted, not final."},
        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_b64}"}},
    ])
    response = llm.invoke([message])
    return {"xray_analysis": response.content}


def diagnosis(state: MedicalState) -> MedicalState:
    prompt = f"""Propose a preliminary diagnosis and brief reasoning, as a DRAFT for physician review.

History: {state['history_summary']}
Labs: {state['lab_summary']}
X-ray: {state['xray_analysis']}"""
    response = llm.invoke(prompt)
    return {"diagnosis": response.content}


def prescription(state: MedicalState) -> MedicalState:
    prompt = f"""Write a brief treatment plan for this diagnosis. Check the patient's existing \
medication for interactions before suggesting anything new.

Diagnosis: {state['diagnosis']}
Current medication (from history): {state['patient_data']}"""
    response = llm.invoke(prompt)
    return {"prescription": response.content}


graph = StateGraph(MedicalState)
graph.add_node("medical_history", run_medical_history)
graph.add_node("lab_analysis", run_lab_analysis)
graph.add_node("analyze_xray", analyze_xray)
graph.add_node("diagnosis", diagnosis)
graph.add_node("prescription", prescription)

graph.add_edge(START, "medical_history")
graph.add_edge(START, "lab_analysis")
graph.add_edge(START, "analyze_xray")
graph.add_edge("medical_history", "diagnosis")
graph.add_edge("lab_analysis", "diagnosis")
graph.add_edge("analyze_xray", "diagnosis")
graph.add_edge("diagnosis", "prescription")
graph.add_edge("prescription", END)

app = graph.compile()

if __name__ == "__main__":
    initial: MedicalState = {
        "patient_id": "P10045",
        "patient_data": "",
        "history_summary": "",
        "lab_data": "",
        "abnormal_flags": [],
        "lab_summary": "",
        "xray_analysis": "",
        "diagnosis": "",
        "prescription": "",
    }

    result = app.invoke(initial)

    print("\n=== FINAL PRESCRIPTION / TREATMENT PLAN ===")
    print(result["prescription"])
