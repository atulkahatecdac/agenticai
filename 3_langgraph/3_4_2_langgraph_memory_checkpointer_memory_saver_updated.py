from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from operator import add

def add_points(state):
    score = state.get("score", 0)
    points = state.get("points", 0)
    state["score"] = score + points
    state["message"] = f"Added {points} points! Total score: {state['score']}"
    return state

# Build graph
graph = StateGraph(dict)
graph.add_node("add_points",
 add_points,
 reducers={"score": add}
 )
graph.set_entry_point("add_points")
graph.add_edge("add_points", END)

# WITHOUT memory - score resets each time
print("=== WITHOUT Memory ===")
app_no_memory = graph.compile()

r1 = app_no_memory.invoke({"points": 10})
print(r1["message"])  # Score: 10

r2 = app_no_memory.invoke({"points": 5})
print(r2["message"])  # Score: 5 (resets!)

# WITH memory - score persists
print("\n=== WITH Memory ===")
memory = MemorySaver()
app_with_memory = graph.compile(checkpointer=memory)

# creates a configuration dictionary that identifies a specific conversation or session in 
# LangGraph's checkpoint system.
# config is just a Python dictionary with a specific structure that LangGraph expects
# "configurable" is a required key that LangGraph looks for
# "thread_id": "game_1" is a unique identifier for this particular conversation thread

config = {"configurable": {"thread_id": "game_1"}}

# First call- initialize score
r1 = app_with_memory.invoke({ "score":0,"points": 10}, config=config)
print(r1["message"])  # Score: 10
# Second call- include score manually
r2 = app_with_memory.invoke({ "score": r1["score"],"points": 5}, config=config)
print(r2["message"])  # Score: 15

# Third call -include score manually 
r3 = app_with_memory.invoke({ "score": r2["score"],"points": 20}, config=config)
print(r3["message"])  # Score: 35