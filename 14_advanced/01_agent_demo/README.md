# 01 - Agent Demo: Birthday Gift Hunt

It's Mom's birthday. Dad has hidden her gift somewhere in the house and left a
trail of sticky notes. An LLM agent (OpenAI Agents SDK, running a **local
`qwen3:8b` model through Ollama**) searches the house room by room to find it.

Nothing about the route is hard-coded. The model reads a room, weighs the
notes, chooses where to go next, ignores pranks and old clues, and submits the
hiding place with evidence. Everyone has played a treasure hunt, so the
audience can follow every decision without background knowledge, yet the
answer can't come from the model's general knowledge. It has to search.

## Run

```bash
cd 14_advanced/01_agent_demo
streamlit run app.py               # web UI: Replay works with no Ollama at all

ollama pull qwen3:8b               # once, for Live mode; keep the Ollama app/server running
python hunt_agent.py               # console trace of a live run
python hunt_agent.py --save        # same, and save it as the run the app replays
```

The app is built for the first class of the course, so it is shown in plain language:

- **A floor plan of the house.** Rooms light up as the agent discovers and searches them; a 🤖 moves
  room to room and leaves a numbered, dotted trail. Spots inside a room (piano, sofa, wardrobe …) appear
  once the agent has walked into that room.
- **A thought bubble** with the agent's own reason for each step ("Walks into the Kitchen -
  *the note says the coldest thing in the house*"). Page ids in its text are replaced by room names.
- **A board of what it has found**: the sticky notes and wrapped boxes. When the hunt ends (or with the
  spoiler toggle), each is marked: Dad's real clue, a prank, last year's note, a guess, a decoy, the gift.
- **🔧 Under the hood** (a toggle, off by default): the same steps as the real tool calls and results,
  for when you move on to how it works.

Two modes, chosen in the sidebar:

- **Replay** steps through `recorded_run.json`, a real run of `qwen3:8b`. Press **Play** (set the
  seconds per step) or click **Next step** to talk through each decision. No Ollama, no waiting, and the
  opening demo can't fail on a slow laptop.
- **Live** runs the agent now; every run takes its own route. After a good run, **Use this run as the
  recorded replay** saves it over `recorded_run.json`.

No API key is needed. Set `OLLAMA_BASE_URL` if Ollama isn't on `http://localhost:11434/v1`.
You can type a different local model (e.g. `llama3.2`) in the sidebar to compare.
Tracing is turned off because, by default, it uploads to OpenAI.

## Files

| File | Role |
|---|---|
| `pages.json` | The 15 rooms and hiding spots (title, content, links), the mission, the answer and the required evidence |
| `hunt_engine.py` | Game state (`HuntState`), the 3 tools, and `replay()` that rebuilds the state from saved tool calls. No LLM code here |
| `hunt_agent.py` | The `Agent` (Ollama via `OpenAIChatCompletionsModel`) and the streamed run loop. Runnable as a CLI demo; `--save` records the run |
| `house_view.py` | The floor plan (SVG), plain-language wording for each step, and the found-notes board. No LLM or Streamlit code |
| `recorded_run.json` | The run the app replays |
| `app.py` | Streamlit UI: floor plan, thought bubble, found-notes board, route, under-the-hood view; Replay and Live modes |

## Tools

| Tool | What it does |
|---|---|
| `read_page(page_id, reason)` | Enters a room or opens a spot, and lists where you can go next. You can only reach places you've seen a way to |
| `list_links(page_id, reason)` | Peeks at where a room leads without searching it |
| `submit_answer(answer, evidence_page_ids, reason)` | Checks the hiding place **and** that the agent actually opened it and saw the gift |

Every tool takes a `reason` argument. This makes the agent's decision for each
step visible in the timeline without exposing hidden chain-of-thought.

## The house (spoilers)

```
p01 Hallway: "Note 1 is on the coldest thing in the house"
 ├─ p02 Kitchen: fridge note "Note 2 is where Mom's favourite songs are played"
 │    │          + brother's prank note "it's in the GARAGE (just kidding)"
 │    ├─ p03 Pantry: gold box = Diwali sweets for the neighbours (decoy)
 │    └─ p04 Back garden: freshly dug soil = the dog's bone (decoy)
 ├─ p05 Living room: Mom plays the piano; the music system is for Dad's cricket
 │    ├─ p06 Music shelf: Dad's note from LAST year, "look in the attic" (trap)
 │    ├─ p07 Piano: Note 2, "not IN the piano; in what she sits on; blue paper"
 │    │    └─ p14 Piano bench: blue gift, tag "Happy Birthday" ★ ANSWER
 │    └─ p08 Sofa: red gift for Rohan's friend (decoy)
 ├─ p09 Staircase
 │    ├─ p10 Kids' room: 5-year-old Meera "it's in Mom's wardrobe!" (unreliable)
 │    ├─ p11 Parents' room: Mom tidies it daily, Dad wouldn't hide it here
 │    │    └─ p15 Wardrobe: saris and photos (dead end)
 │    └─ p12 Attic: last year's torn wrapping paper (dead end)
 └─ p13 Garage: bikes and tools (the prank's dead end)
```

- `submit_answer` only accepts an answer naming the **bench** (or stool), with `p14` cited
  as evidence. Answering "the piano" after reading Note 2 is rejected.
- On test runs `qwen3:8b` solved it in 6-7 tool calls. Once it went straight there,
  and once it detoured to the garage first. The route varies from run to run.

## Points to make in class

- **Autonomy:** the route differs from run to run. The LLM, not the code, picks each step.
- **Tool use:** all knowledge about the house comes from calling Python functions.
- **Memory/state:** `HuntState` tracks rooms searched and places discovered, and the model's
  conversation history keeps track of the notes.
- **Reasoning over noise:** the prank note, last year's note, the decoy gifts and the
  unreliable sister. Ask the class which ones the agent fell for.
- **Guardrails in the environment:** the engine blocks guessed page ids, enforces a 20-call
  budget, and rejects answers without evidence. The SDK's `max_turns` is a backstop.
- **Runs fully locally:** the same Agents SDK code works with an open model via
  Ollama's OpenAI-compatible endpoint, by swapping only the `model=` argument.
