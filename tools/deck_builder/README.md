# Deck builder (shared engine)

Builds the course decks from slide content written as JavaScript data. Two decks use it:

| Deck folder | Writes | Content |
|---|---|---|
| `16_PGP-Agentic/deck_builder/` | `16_PGP-Agentic/PGP_Agentic_AI.pptx` | one file per session |
| `14_advanced/deck_builder/` | `14_advanced/Agentic AI - Advanced Engineering.pptx` | one file per module |

Both decks share one design: navy text, coral accent, teal secondary, Calibri, pale cards, icons in coloured
circles, and a DEMO bar on every content slide naming the script to run. They have no speaker notes and no
footers. The `.pptx` files are generated, so edit the content files: manual edits in PowerPoint are lost on the
next build.

## Setup and build

```bash
cd tools/deck_builder
npm install                 # once: pptxgenjs, react-icons, sharp (pinned in package.json)

cd ../../14_advanced/deck_builder      # or 16_PGP-Agentic/deck_builder
npm run build                          # writes the deck named in deck.config.js
npm run build -- --only 07             # just one content file (07_….js), for quick checks
npm run build -- --out test.pptx       # write somewhere else
```

Close the deck in PowerPoint before rebuilding. The build prints a `WARN` line for anything that would not fit:
a column of content that runs past the DEMO bar, a summary list that is too long, or a DEMO line over 100
characters. A clean build reports `0 warning(s)`.

To check the result visually, render every slide to PNG through PowerPoint:

```powershell
powershell -ExecutionPolicy Bypass -File tools\deck_builder\tools\render.ps1 -Deck "14_advanced\Agentic AI - Advanced Engineering.pptx" -OutDir out_png
```

## Layout

| Path | What it holds |
|---|---|
| `build.js` | `node build.js <deckDir>`: reads `<deckDir>/deck.config.js` and `<deckDir>/content/*.js`, writes the deck. |
| `lib/theme.js` | Colours, fonts and slide geometry. |
| `lib/blocks.js` | Content blocks: `text`, `bullets`, `icons`, `steps`, `cards`, `tiles`, `flow`, `tree`, `chain`, `code`, `table`, `compare`, `callout`, `image`, `cols`. |
| `lib/slides.js` | Slide kinds: `cover`, `map`, `opener`, `content` (default), `image`, `summary`. |
| `lib/icons.js`, `lib/text.js` | Icon rendering and text measurement. |
| `assets/` | Infographics used by more than one deck. |
| `tools/render.ps1` | PNG export of every slide for visual QA. |

A deck folder holds `deck.config.js` (`out`, `title`, `author`), `content/NN_*.js` (one section each, built in
file-name order), `assets/` (its own images) and a `package.json` whose `build` script calls this engine.
An image's `src` is looked up in the deck's `assets/` first, then in the shared `assets/` here.

## Writing slides

Each content file exports `{ section, slides }`. A content slide is a title, an optional subtitle, a DEMO line,
and either one column of blocks or two columns (`left` / `right`, widths set with `split`):

```js
{
  title: "Writing a Tool",
  subtitle: "A normal Python function plus a decorator",
  demo: "06_langchain_agents/tool_calling.py",   // or "Concept" for a discussion slide
  split: [1.2, 1],
  left:  [{ type: "code", caption: "tool.py", code: "@tool\ndef ..." }],
  right: [{ type: "icons", items: [{ icon: "FaTag", title: "@tool", text: "..." }] }],
}
```

- In text, `**bold**` is bold and `` `code` `` is shown in the code font.
- Icon names come from [react-icons](https://react-icons.github.io/react-icons/) (`Fa…` = Font Awesome 6,
  `Md…` = Material, `Lu…` = Lucide). An unknown name stops the build and lists it.
- An infographic that carries its own title is a full-slide image: `{ kind: "image", src: "file.png", demo: "..." }`.
  Keep images as palette PNGs (sharp `png({ palette: true })`) so the decks stay small.
- `tree` connects every box in a row to every box in the next row. That suits fan-out (1 → n) and join
  (n → 1); for anything else (n → n) use a `table` or several `chain`s instead.
- Code shown on a slide should match the demo script it names.
- Each deck's README says what its DEMO paths are relative to.
