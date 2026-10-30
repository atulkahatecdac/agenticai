import os
# pip install langgraph langgraph-checkpoint-sqlite

import sqlite3
from typing import TypedDict
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from langgraph.checkpoint.sqlite import SqliteSaver

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


# -------------------------------
# State
# -------------------------------
class NotesState(TypedDict):
    action: str
    note: str
    notes: list[str]
    message: str


# -------------------------------
# Node
# -------------------------------
def manage_notes(state: NotesState) -> NotesState:
    action = state.get("action")
    note = state.get("note", "")
    notes = state.get("notes", [])

    if action == "add":
        notes.append(note)
        return {
            "notes": notes,
            "message": f"Added note: {note}"
        }

    if action == "list":
        if not notes:
            return {
                "notes": notes,
                "message": "No notes found."
            }

        note_list = "\n".join(
            f"{i + 1}. {note}"
            for i, note in enumerate(notes)
        )

        return {
            "notes": notes,
            "message": f"Saved notes:\n{note_list}"
        }

    return {
        "notes": notes,
        "message": "Unknown action."
    }


# -------------------------------
# Build Graph Once
# -------------------------------
def build_graph(checkpointer=None):
    graph = StateGraph(NotesState)

    graph.add_node("manage_notes", manage_notes)
    graph.set_entry_point("manage_notes")
    graph.add_edge("manage_notes", END)

    return graph.compile(checkpointer=checkpointer)


# -------------------------------
# Example 1: No Memory
# -------------------------------
def run_without_memory():
    print("\n=== 1. WITHOUT MEMORY ===")

    app = build_graph()

    result1 = app.invoke({
        "action": "add",
        "note": "Learn LangGraph",
        "notes": [],
        "message": ""
    })
    print(result1["message"])

    result2 = app.invoke({
        "action": "list",
        "note": "",
        "notes": [],
        "message": ""
    })
    print(result2["message"])


# -------------------------------
# Example 2: MemorySaver
# -------------------------------
def run_with_memory_saver():
    print("\n=== 2. WITH MEMORYSAVER ===")

    memory = MemorySaver()
    app = build_graph(checkpointer=memory)

    config = {
        "configurable": {
            "thread_id": "memory_demo"
        }
    }

    app.invoke({
        "action": "add",
        "note": "Learn MemorySaver",
        "notes": [],
        "message": ""
    }, config=config)

    current_state = app.get_state(config).values

    app.invoke({
        "action": "add",
        "note": "MemorySaver works only while program is running",
        "notes": current_state["notes"],
        "message": ""
    }, config=config)

    current_state = app.get_state(config).values

    result = app.invoke({
        "action": "list",
        "note": "",
        "notes": current_state["notes"],
        "message": ""
    }, config=config)

    print(result["message"])


# -------------------------------
# Example 3: SQLiteSaver
# -------------------------------
def run_with_sqlite_saver():
    print("\n=== 3. WITH SQLITESAVER ===")

    conn = sqlite3.connect(os.path.join(BASE_DIR, "notes_memory.db"), check_same_thread=False)
    app = build_graph(checkpointer=SqliteSaver(conn))

    config = {
        "configurable": {
            "thread_id": "sqlite_demo"
        }
    }

    current_state = app.get_state(config).values
    notes = current_state.get("notes", [])

    result = app.invoke({
        "action": "add",
        "note": "This note is saved in SQLite",
        "notes": notes,
        "message": ""
    }, config=config)

    print(result["message"])

    current_state = app.get_state(config).values

    result = app.invoke({
        "action": "list",
        "note": "",
        "notes": current_state["notes"],
        "message": ""
    }, config=config)

    print(result["message"])

    conn.close()


# -------------------------------
# Example 4: Read Saved SQLite Data
# -------------------------------
def read_sqlite_memory():
    print("\n=== 4. READ SAVED SQLITE MEMORY ===")

    conn = sqlite3.connect(os.path.join(BASE_DIR, "notes_memory.db"), check_same_thread=False)
    app = build_graph(checkpointer=SqliteSaver(conn))

    config = {
        "configurable": {
            "thread_id": "sqlite_demo"
        }
    }

    state = app.get_state(config).values

    if not state:
        print("No saved state found.")
    else:
        print("Saved state:")
        print(state)

    conn.close()


# -------------------------------
# Run All Examples
# -------------------------------
if __name__ == "__main__":
    run_without_memory()
    run_with_memory_saver()
    run_with_sqlite_saver()
    read_sqlite_memory()