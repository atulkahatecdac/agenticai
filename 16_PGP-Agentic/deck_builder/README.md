# PGP deck content

The slide content for `../PGP_Agentic_AI.pptx` (the PGP – Agentic AI course deck). The build engine, slide
and block types, and the design are shared with the 14_advanced deck and documented in
[`tools/deck_builder/README.md`](../../tools/deck_builder/README.md).

## Build

```bash
cd tools/deck_builder && npm install     # once
cd 16_PGP-Agentic/deck_builder
npm run build                            # writes ../PGP_Agentic_AI.pptx
npm run build -- --only 03               # just content/03_session_3.js
```

Aim for `0 warning(s)`, then check the slides visually with `tools/deck_builder/tools/render.ps1`.

## This folder

| Path | What it holds |
|---|---|
| `deck.config.js` | Output file, title and author. |
| `content/00_intro.js` … `09_session_9.js` | The slides, one file per session, in order. Edit these to change the deck. |
| `assets/` | The images only this deck uses. Shared ones (RAG, LCEL, guardrails, …) are in `tools/deck_builder/assets/`. |

DEMO paths are relative to `16_PGP-Agentic/code/` (for example `session_3/3_2_tool_calling.py`).
