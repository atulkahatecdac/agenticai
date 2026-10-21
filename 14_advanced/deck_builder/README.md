# Advanced Engineering deck content

The slide content for `../Agentic AI - Advanced Engineering.pptx` (the "Advanced Certification in Agentic AI
Engineering" course deck, modules 01–19). The build engine, slide and block types, and the design are shared
with the PGP deck and documented in [`tools/deck_builder/README.md`](../../tools/deck_builder/README.md).

## Build

```bash
cd tools/deck_builder && npm install     # once
cd 14_advanced/deck_builder
npm run build                            # writes "../Agentic AI - Advanced Engineering.pptx"
npm run build -- --only 07               # just content/07_langgraph.js
```

Aim for `0 warning(s)`, then check the slides visually with `tools/deck_builder/tools/render.ps1`.

## This folder

| Path | What it holds |
|---|---|
| `deck.config.js` | Output file, title and author. |
| `content/00_intro.js` | Cover and course map. |
| `content/01_python_setup.js` … `19_capstone.js` | One file per module, named by module number. Each starts with an opener (goals and agenda) and ends with a summary. |
| `assets/` | The infographics only this deck uses (palette PNGs). Shared ones are in `tools/deck_builder/assets/`. |

DEMO paths are relative to `14_advanced/`, e.g. `07_langgraph/greeter_graph.py`. Modules 10 and 11 (MCP) have no
folder here: their demos live in `6_mcp/`, written as `../6_mcp/…`. The PDFs next to the deck (brochure and
course outline) are not generated.
