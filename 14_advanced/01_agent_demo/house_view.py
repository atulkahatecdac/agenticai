"""
Birthday Gift Hunt - how the house looks on screen.

No LLM code and no Streamlit code here: just the floor plan, friendly names for
every room, and functions that turn the agent's tool calls into things a
beginner can follow:
  * house_svg()      - the floor plan, with the robot, its route and what it has found
  * describe()       - one tool call in plain English ("Walks into the kitchen")
  * friendly()       - replaces page ids like "p07" in the model's text with room names
  * notes_found()    - the sticky notes and wrapped boxes the agent has seen so far
"""

import re
from html import escape

from hunt_engine import PAGES, HuntState

# ---------------------------------------------------------------- the house
# Each page of pages.json becomes a room (or a spot inside a room) on a 900 x 540 floor plan.
# The staircase is drawn twice: at the bottom of the ground floor and as the upstairs landing.
ROOMS = {
    "p04": {"name": "Back garden", "icon": "🌳", "rects": [(20, 40, 540, 60)]},
    "p02": {"name": "Kitchen", "icon": "🍳", "rects": [(20, 110, 195, 170)]},
    "p03": {"name": "Pantry", "icon": "🥫", "rects": [(225, 110, 95, 90)]},
    "p05": {"name": "Living room", "icon": "🛋️", "rects": [(330, 110, 230, 290)]},
    "p01": {"name": "Hallway", "icon": "🚪", "rects": [(20, 290, 300, 100)]},
    "p13": {"name": "Garage", "icon": "🚗", "rects": [(20, 400, 185, 120)]},
    "p09": {"name": "Staircase", "icon": "🪜", "rects": [(215, 400, 105, 120), (590, 350, 300, 60)]},
    "p12": {"name": "Attic", "icon": "📦", "rects": [(590, 40, 300, 90)]},
    "p10": {"name": "Kids' room", "icon": "🧸", "rects": [(590, 140, 145, 200)]},
    "p11": {"name": "Parents' room", "icon": "🛏️", "rects": [(745, 140, 145, 200)]},
    # spots inside a room: only drawn once the agent has been in that room
    "p06": {"name": "Music shelf", "icon": "📻", "rects": [(342, 140, 108, 36)], "parent": "p05", "robot": (396, 208)},
    "p07": {"name": "Piano", "icon": "🎹", "rects": [(456, 140, 96, 46)], "parent": "p05", "robot": (574, 168)},
    "p14": {"name": "Piano bench", "icon": "🪑", "rects": [(452, 196, 104, 28)], "parent": "p05", "robot": (574, 216)},
    "p08": {"name": "Sofa", "icon": "🛋️", "rects": [(360, 320, 150, 40)], "parent": "p05", "robot": (532, 346)},
    "p15": {"name": "Wardrobe", "icon": "👗", "rects": [(757, 180, 120, 36)], "parent": "p11", "robot": (817, 248)},
}
assert set(ROOMS) == set(PAGES), "every page in pages.json needs a place on the floor plan"

# What the agent can find in each place. `kind` is only revealed after the hunt (or with the spoiler toggle).
FINDS = {
    "p01": [("note", "Dad (front door)", "Follow my notes! Note 1 is on the coldest thing in the house.", "clue")],
    "p02": [("note", "Dad's Note 1 (fridge)", "Note 2 is where Mom's favourite songs are played.", "clue"),
            ("note", "Rohan (little brother)", "The gift is in the GARAGE!!! hehe just kidding", "prank")],
    "p03": [("box", "Gold box", "Label: Diwali sweets - for the neighbours.", "decoy")],
    "p04": [("box", "Freshly dug soil", "Just Bruno the dog's bone.", "decoy")],
    "p06": [("note", "Old faded note", "Last clue: look in the attic! (dated LAST year)", "old")],
    "p07": [("note", "Dad's Note 2 (piano)", "Not inside the piano - in the thing she sits on. Blue paper.", "clue")],
    "p08": [("box", "Red gift", "Tag: For Rohan's friend Arjun.", "decoy")],
    "p10": [("note", "Meera (age 5)", "It's in Mom's wardrobe!!", "guess")],
    "p12": [("box", "Torn wrapping paper", "From LAST year's gift.", "old")],
    "p14": [("box", "Blue gift", "Tag: Happy Birthday, my dear! Love, the whole family.", "gift")],
}
VERDICT = {  # kind -> (badge, colour)
    "clue": ("✓ Dad's real clue", "#1A7F8E"),
    "prank": ("✗ A prank", "#EA4B71"),
    "old": ("✗ Left over from last year", "#EA4B71"),
    "guess": ("✗ Just a guess", "#EA4B71"),
    "decoy": ("✗ Not Mom's gift", "#EA4B71"),
    "gift": ("🎉 Mom's gift!", "#1A7F8E"),
}

NAVY, CORAL, TEAL, SLATE, LINE = "#1F2A44", "#EA4B71", "#1A7F8E", "#5B6475", "#D5DAE3"


def name(pid: str) -> str:
    return ROOMS[pid]["name"] if pid in ROOMS else pid


def friendly(text: str) -> str:
    """'I'll read p07 next' -> 'I'll read the Piano next' (page ids mean nothing to a beginner)."""
    return re.sub(r"\b[pP](\d{2})\b", lambda m: name(f"p{m.group(1)}"), text or "")


# ---------------------------------------------------------------- plain-language actions
def describe(call: dict) -> tuple[str, str]:
    """(icon, sentence) for one tool call, in words a beginner understands."""
    tool, args, result = call["tool"], call["args"], call.get("result", "")
    if tool == "read_page":
        pid = args.get("page_id", "")
        if not result.startswith("PAGE"):
            return "🚫", f"Tried to go to {name(pid)}, but hasn't found the way there yet"
        if pid == "p14":
            return "🪑", "Lifts the lid of the piano bench"
        if ROOMS.get(pid, {}).get("parent"):
            return ROOMS[pid]["icon"], f"Takes a close look at the {name(pid).lower()}"
        return ROOMS.get(pid, {}).get("icon", "🚶"), f"Walks into the {name(pid)}"
    if tool == "list_links":
        return "👀", f"Peeks through the door of the {name(args.get('page_id', ''))} to see where it leads"
    if tool == "submit_answer":
        return "🙋", f"Says: \"I think it's {args.get('answer', '').rstrip('.')}!\""
    return "🔧", tool


def verdict(call: dict) -> tuple[str, str] | None:
    """('good'|'bad', text) for an answer or a failed step, else None."""
    result = call.get("result", "")
    if call["tool"] == "submit_answer":
        if result.startswith("ACCEPTED"):
            return "good", "Correct! That's Mom's gift."
        return "bad", "Not accepted: " + result.split(":", 1)[-1].strip()
    if result.startswith(("ERROR", "BUDGET")):
        return "bad", result.split(":", 1)[-1].strip()
    return None


def pending_sentence(tool: str, args: dict) -> str:
    """What the agent is about to do (before the tool has run)."""
    return describe({"tool": tool, "args": args, "result": "PAGE"})[1]


# ---------------------------------------------------------------- notes board
def notes_found(state: HuntState) -> list[tuple[str, str, str, str]]:
    """Every note/box in the places the agent has looked at, in the order it saw them."""
    seen = []
    for pid in state.visited:
        seen += FINDS.get(pid, [])
    return seen


def notes_html(state: HuntState, reveal: bool) -> str:
    items = notes_found(state)
    if not items:
        return "<div style='color:#8A93A3;font-style:italic'>Nothing found yet.</div>"
    cards = []
    for i, (kind_of, who, text, kind) in enumerate(items):
        bg = "#FFF3B0" if kind_of == "note" else "#E8F1FF"
        tilt = (-1.5, 1.2, -0.8, 1.6)[i % 4]
        badge = ""
        if reveal:
            label, colour = VERDICT[kind]
            badge = (f"<div style='margin-top:6px;font-size:12px;font-weight:700;color:{colour}'>"
                     f"{escape(label)}</div>")
        icon = "📝" if kind_of == "note" else "🎁"
        cards.append(
            f"<div style='background:{bg};padding:10px 12px;border-radius:4px;transform:rotate({tilt}deg);"
            f"box-shadow:2px 3px 6px rgba(0,0,0,.15);font-family:Segoe UI,Helvetica,sans-serif'>"
            f"<div style='font-size:12px;color:{SLATE};font-weight:600'>{icon} {escape(who)}</div>"
            f"<div style='font-size:14px;color:{NAVY};margin-top:4px'>{escape(text)}</div>{badge}</div>")
    return ("<div style='display:grid;grid-template-columns:repeat(auto-fill,minmax(170px,1fr));gap:14px'>"
            + "".join(cards) + "</div>")


# ---------------------------------------------------------------- floor plan
def _center(rect):
    x, y, w, h = rect
    return x + w / 2, y + h / 2


def _nearest_rect(pid: str, prev):
    rects = ROOMS[pid]["rects"]
    if prev is None or len(rects) == 1:
        return rects[0]
    return min(rects, key=lambda r: (_center(r)[0] - prev[0]) ** 2 + (_center(r)[1] - prev[1]) ** 2)


UPSTAIRS_X = 575                       # everything right of this is upstairs
STAIRS_DOWN, STAIRS_UP = (_center(ROOMS["p09"]["rects"][0]), _center(ROOMS["p09"]["rects"][1]))


def _floor(point) -> str:
    return "up" if point[0] > UPSTAIRS_X else "down"


def route(state: HuntState) -> list[tuple[int, str]]:
    """(step number, page id) for every successful move, in order."""
    return [(c["step"], c["args"]["page_id"]) for c in state.tool_calls
            if c["tool"] == "read_page" and c["result"].startswith("PAGE")]


def house_svg(state: HuntState, show_all: bool = False) -> str:
    solved = state.status == "solved"
    out = [f"<svg viewBox='0 0 900 540' xmlns='http://www.w3.org/2000/svg' "
           f"style='width:100%;height:auto;font-family:Segoe UI,Helvetica,sans-serif'>",
           "<style>@keyframes pulse{0%{r:20;opacity:.55}100%{r:42;opacity:0}}"
           ".pulse{animation:pulse 1.4s ease-out infinite}</style>",
           f"<rect x='0' y='0' width='900' height='540' rx='14' fill='#FAFBFD'/>",
           f"<text x='20' y='28' font-size='16' font-weight='700' fill='{SLATE}' letter-spacing='2'>GROUND FLOOR</text>",
           f"<text x='590' y='28' font-size='16' font-weight='700' fill='{SLATE}' letter-spacing='2'>UPSTAIRS</text>"]

    def room_style(pid):
        if pid == state.current_page:
            return "#FFE08A", CORAL, 3, ""
        if pid in state.visited:
            return "#D6ECFF", NAVY, 1.5, ""
        if pid in state.reachable or show_all:
            return "#FFFFFF", SLATE, 1.5, "stroke-dasharray='6 4'"
        return "#E9ECF1", "#C3C8D2", 1, ""

    # rooms first, then the spots inside them
    for spots in (False, True):
        for pid, room in ROOMS.items():
            parent = room.get("parent")
            if bool(parent) != spots:
                continue
            if parent and not (show_all or parent in state.visited or pid in state.reachable or pid in state.visited):
                continue
            fill, stroke, width, dash = room_style(pid)
            if solved and pid == "p14":
                fill, stroke, width = "#B7F0C0", TEAL, 3
            for x, y, w, h in room["rects"]:
                out.append(f"<rect x='{x}' y='{y}' width='{w}' height='{h}' rx='8' fill='{fill}' "
                           f"stroke='{stroke}' stroke-width='{width}' {dash}/>")
                known = show_all or pid in state.reachable or pid in state.visited
                colour = NAVY if known else "#9AA1AD"
                size = 13 if parent else 16
                label = f"{room['icon']} {room['name']}" if known or not parent else "?"
                if parent:
                    out.append(f"<text x='{x + w / 2}' y='{y + h / 2 + 4}' font-size='{size}' text-anchor='middle' "
                               f"fill='{colour}'>{escape(label)}</text>")
                else:
                    out.append(f"<text x='{x + 8}' y='{y + 23}' font-size='{size}' font-weight='600' "
                               f"fill='{colour}'>{escape(label)}</text>")

    # the route: a dotted line through every place the agent moved to, with step numbers.
    # Changing floors always goes through the staircase on both floors.
    stops, segments, prev, seen_count = [], [[]], None, {}
    for step, pid in route(state):
        rect = _nearest_rect(pid, prev)
        cx, cy = _center(rect)
        if prev is not None and _floor(prev) != _floor((cx, cy)):
            # walk to the staircase on this floor, then carry on from the staircase on the other floor
            here, there = (STAIRS_DOWN, STAIRS_UP) if _floor(prev) == "down" else (STAIRS_UP, STAIRS_DOWN)
            segments[-1].append(here)
            segments.append([there])
        n = seen_count.get(pid, 0)
        seen_count[pid] = n + 1
        if ROOMS[pid].get("parent"):           # small spot: put the mark on its bottom edge
            x, y, w, h = rect
            mark = (x + 12 + n * 18, y + h)
        else:
            mark = (cx + n * 18, cy + 14)
        segments[-1].append(mark)
        stops.append((step, *mark))
        prev = (cx, cy)
    for seg in segments:
        if len(seg) > 1:
            pts = " ".join(f"{x},{y}" for x, y in seg)
            out.append(f"<polyline points='{pts}' fill='none' stroke='{CORAL}' stroke-width='3' "
                       f"stroke-dasharray='2 7' stroke-linecap='round' opacity='.8'/>")
    if len(segments) > 1:   # the agent used the stairs: mark both ends
        for x, y in (STAIRS_DOWN, STAIRS_UP):
            out.append(f"<text x='{x + 30}' y='{y + 6}' font-size='18' font-weight='700' fill='{CORAL}' "
                       f"text-anchor='middle'>⇅</text>")
    path = [pt for seg in segments for pt in seg]
    for step, x, y in stops:
        out.append(f"<circle cx='{x}' cy='{y}' r='13' fill='{CORAL}'/>"
                   f"<text x='{x}' y='{y + 5}' font-size='14' font-weight='700' fill='white' "
                   f"text-anchor='middle'>{step}</text>")

    # the robot, where it is now
    if state.current_page:
        rect = _nearest_rect(state.current_page, path[-2] if len(path) > 1 else None)
        cx, cy = _center(rect)
        if "robot" in ROOMS[state.current_page]:   # stand beside a small spot, not on top of its label
            cx, cy = ROOMS[state.current_page]["robot"]
        if not solved:
            out.append(f"<circle class='pulse' cx='{cx}' cy='{cy - 8}' r='20' fill='{CORAL}'/>")
        out.append(f"<text x='{cx}' y='{cy + 6}' font-size='36' text-anchor='middle'>🤖</text>")
    if solved:
        x, y, w, h = ROOMS["p14"]["rects"][0]
        out.append(f"<text x='{x - 18}' y='{y + 22}' font-size='30' text-anchor='middle'>🎁</text>"
                   f"<text x='{x + w / 2}' y='{y + h + 18}' font-size='15' font-weight='700' fill='{TEAL}' "
                   f"text-anchor='middle'>Found it!</text>")

    # legend in the empty corner of the ground floor
    lx, ly = 345, 418
    legend = [("#FFE08A", CORAL, "", "Where the agent is"), ("#D6ECFF", NAVY, "", "Already searched"),
              ("#FFFFFF", SLATE, "stroke-dasharray='5 3'", "Knows the way, not searched"),
              ("#E9ECF1", "#C3C8D2", "", "Not discovered yet")]
    for i, (fill, stroke, dash, text) in enumerate(legend):
        y = ly + i * 24
        out.append(f"<rect x='{lx}' y='{y}' width='22' height='16' rx='4' fill='{fill}' stroke='{stroke}' {dash}/>"
                   f"<text x='{lx + 30}' y='{y + 13}' font-size='15' fill='{SLATE}'>{text}</text>")
    out.append(f"<circle cx='{lx + 11}' cy='{ly + 104}' r='8' fill='{CORAL}'/>"
               f"<text x='{lx + 30}' y='{ly + 108}' font-size='15' fill='{SLATE}'>Step number on its route</text>")
    out.append("</svg>")
    return "".join(out)
