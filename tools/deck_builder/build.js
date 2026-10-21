// Builds a course deck from a deck folder (deck.config.js + content/*.js + assets/).
//   node tools/deck_builder/build.js <deckDir>                    -> whole deck
//   node tools/deck_builder/build.js <deckDir> --only 03          -> just one content file (quick visual checks)
//   node tools/deck_builder/build.js <deckDir> --out other.pptx   -> different output path
// Each deck folder also has `npm run build`, which calls this script with "." as <deckDir>.
// Close the deck in PowerPoint before rebuilding.

const fs = require("fs");
const path = require("path");
const pptxgen = require("pptxgenjs");
const sharp = require("sharp");
const { K, defineMasters, MASTER, BLANK, OPENER } = require("./lib/slides");
const { missing } = require("./lib/icons");

const arg = (name) => { const i = process.argv.indexOf(name); return i > 0 ? process.argv[i + 1] : null; };
const DECK = process.argv[2] && !process.argv[2].startsWith("--") ? path.resolve(process.argv[2]) : null;
if (!DECK || !fs.existsSync(path.join(DECK, "deck.config.js"))) {
  console.error("usage: node build.js <deckDir> [--only <prefix>] [--out <file.pptx>]   (<deckDir> must hold deck.config.js)");
  process.exit(1);
}
const CONFIG = require(path.join(DECK, "deck.config.js"));
const ONLY = arg("--only");
const OUT = arg("--out") ? path.resolve(arg("--out")) : path.resolve(DECK, CONFIG.out);
// The deck's own images first, then the ones shared by every deck.
const ASSET_DIRS = [path.join(DECK, "assets"), path.join(__dirname, "assets")];

// Resolve every image (slide kind "image" and block type "image") to a path + aspect ratio.
async function resolveImages(node) {
  if (Array.isArray(node)) { for (const n of node) await resolveImages(n); return; }
  if (!node || typeof node !== "object") return;
  if ((node.kind === "image" || node.type === "image") && node.src) {
    node.path = ASSET_DIRS.map((d) => path.join(d, node.src)).find((p) => fs.existsSync(p));
    if (!node.path) throw new Error(`missing asset ${node.src}`);
    const m = await sharp(node.path).metadata();
    node.ratio = m.width / m.height;
  }
  for (const v of Object.values(node)) if (v && typeof v === "object") await resolveImages(v);
}

(async () => {
  const files = fs.readdirSync(path.join(DECK, "content")).filter((f) => f.endsWith(".js")).sort()
    .filter((f) => !ONLY || f.startsWith(ONLY));
  const pres = new pptxgen();
  pres.layout = "LAYOUT_16x9";
  pres.author = CONFIG.author;
  pres.title = CONFIG.title;
  pres.theme = { headFontFace: "Calibri", bodyFontFace: "Calibri" };
  defineMasters(pres);

  let n = 0, warnings = 0;
  for (const f of files) {
    const { section, slides } = require(path.join(DECK, "content", f));
    await resolveImages(slides);
    pres.addSection({ title: section });
    for (const s of slides) {
      n++;
      const kind = s.kind || "content";
      if (!K[kind]) throw new Error(`${f}: unknown slide kind "${kind}"`);
      const slide = pres.addSlide({ masterName: ["image", "cover"].includes(kind) ? BLANK : kind === "opener" ? OPENER : MASTER, sectionTitle: section });
      const label = `${f} #${n} "${(s.title || s.src || kind).slice(0, 50)}"`;
      const ctx = { slide, warn: (m) => { warnings++; console.warn(`WARN ${label}: ${m}`); } };
      if (s.demo && s.demo.length > 100) ctx.warn(`DEMO text is ${s.demo.length} chars – shorten to ≤ 100 so it fits on one line`);
      await K[kind](ctx, s);
    }
  }
  if (missing.size) throw new Error(`unknown icon names: ${[...missing].join(", ")}`);
  await pres.writeFile({ fileName: OUT });
  console.log(`Wrote ${OUT}: ${n} slides from ${files.length} file(s), ${warnings} warning(s)`);
})().catch((e) => { console.error(e); process.exit(1); });
