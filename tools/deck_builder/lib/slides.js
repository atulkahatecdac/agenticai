// Slide kinds. Every kind draws on the reference deck's frame: bold navy title at the top
// left, grey subtitle under it, white background, and (here) a DEMO bar at the bottom.

const { C, F, G } = require("./theme");
const { textH } = require("./text");
const { renderColumn, columnH, text, circle, card, pill, eyebrow, B } = require("./blocks");

const MASTER = "DECK_CONTENT";
const BLANK = "DECK_BLANK";
const OPENER = "DECK_OPENER";

function defineMasters(pres) {
  pres.defineSlideMaster({
    title: MASTER,
    background: { color: C.white },
    objects: [
      { placeholder: { options: { name: "title", type: "title", x: G.MX, y: G.titleY, w: G.CW, h: G.titleH, fontFace: F.body, fontSize: 28, bold: true, color: C.navy, margin: 0, valign: "middle", align: "left" }, text: "" } },
    ],
  });
  pres.defineSlideMaster({ title: BLANK, background: { color: C.white }, objects: [] });
  // Session opener: the title sits lower, under a coral eyebrow line.
  pres.defineSlideMaster({
    title: OPENER,
    background: { color: C.white },
    objects: [
      { placeholder: { options: { name: "title", type: "title", x: G.MX, y: 0.5, w: G.CW, h: 0.58, fontFace: F.body, fontSize: 28, bold: true, color: C.navy, margin: 0, valign: "middle", align: "left" }, text: "" } },
    ],
  });
}

// Largest size (28pt down to 20pt) at which the title fits on one line of the content width.
function titleSize(t) {
  let size = 28;
  while (size > 20 && t.length * size * 0.56 > G.CW * 72) size -= 1;
  return size;
}

function header(slide, s) {
  slide.addText(s.title, { placeholder: "title", fontSize: titleSize(s.title) });
  if (s.subtitle) text(slide, s.subtitle, { x: G.MX, y: G.subY, w: G.CW, h: G.subH, fontSize: 13.5, color: C.slate });
}

function demoBar(slide, demo) {
  if (!demo) return;
  const concept = /^concept/i.test(demo);
  card(slide, G.MX, G.demoY, G.CW, G.demoH);
  pill(slide, concept ? "TALK" : "DEMO", G.MX + 0.08, G.demoY + 0.06, 0.56, G.demoH - 0.12, concept ? C.teal : C.coral, 8);
  const size = demo.length > 120 ? 8 : demo.length > 95 ? 8.5 : 9;
  text(slide, concept ? "Concept slide – no code; discuss" : demo, {
    x: G.MX + 0.76, y: G.demoY, w: G.CW - 0.86, h: G.demoH, fontSize: size, valign: "middle",
    fontFace: concept ? F.body : F.code, color: concept ? C.slate : C.navy, italic: concept,
  });
}

// ------------------------------------------------------------------ kinds
const K = {};

// When a column is shorter than the space it has, open up the gaps between its blocks a
// little and centre the result vertically, so slides don't end half-way down the page.
function balance(blocks, w, avail) {
  const h = columnH(blocks, w), slack = avail - h, n = blocks.length;
  if (slack <= 0.05 || s_noBalance(blocks)) return { extra: 0, h };
  const extra = n > 1 ? Math.min(0.3, (slack * 0.5) / (n - 1)) : 0;
  return { extra, h: h + extra * (n - 1) };
}
const s_noBalance = (blocks) => blocks.some((b) => b.type === "image");

K.content = async (ctx, s) => {
  header(ctx.slide, s);
  const top = s.subtitle ? G.top : G.topNoSub;
  const bottom = s.demo ? G.bottom : G.bottomNoDemo;
  const avail = bottom - top;
  const cols = s.left || s.right
    ? (() => {
        const r = s.split || [1, 1], gap = s.gap ?? 0.4, lw = ((G.CW - gap) * r[0]) / (r[0] + r[1]);
        return [{ blocks: s.left || [], x: G.MX, w: lw }, { blocks: s.right || [], x: G.MX + lw + gap, w: G.CW - lw - gap }];
      })()
    : [{ blocks: s.blocks || [], x: G.MX, w: G.CW }];
  for (const c of cols) Object.assign(c, balance(c.blocks, c.w, avail));
  const tallest = Math.max(...cols.map((c) => c.h));
  const offset = s.top ? 0 : Math.max(0, Math.min(0.45, (avail - tallest) / 2));
  for (const c of cols) await renderColumn(ctx, c.blocks, c.x, top + offset, c.w, bottom, c.extra);
  demoBar(ctx.slide, s.demo);
};

// Full-slide figure (an infographic that carries its own title).
K.image = async (ctx, s) => {
  const top = s.title ? (s.subtitle ? G.top : G.topNoSub) : 0.18;
  if (s.title) header(ctx.slide, s);
  const bottom = s.demo ? G.demoY - 0.1 : G.H - 0.18;
  await B.image.render(ctx, { path: s.path, ratio: s.ratio, alt: s.alt || s.title || "" }, 0.3, top, G.W - 0.6, bottom - top);
  demoBar(ctx.slide, s.demo);
};

K.cover = async (ctx, s) => {
  const sl = ctx.slide;
  eyebrow(sl, s.eyebrow, G.MX, 0.62, 4.6);
  text(sl, s.title, { x: G.MX, y: 0.9, w: 4.7, h: 1.0, fontSize: 40, bold: true, valign: "top" });
  text(sl, s.description, { x: G.MX, y: 1.85, w: 4.4, h: 0.8, fontSize: 13.5, color: C.slate });
  eyebrow(sl, "Instructor", G.MX, 2.9, 4.4);
  text(sl, s.author, { x: G.MX, y: 3.12, w: 4.4, h: 0.3, fontSize: 15, bold: true });
  text(sl, s.authorLink, { x: G.MX, y: 3.42, w: 4.4, h: 0.25, fontSize: 11, color: C.slate });
  eyebrow(sl, "Course repository", G.MX, 3.85, 4.4);
  text(sl, s.repo, { x: G.MX, y: 4.07, w: 4.4, h: 0.25, fontSize: 11, color: C.slate });
  text(sl, s.footnote, { x: G.MX, y: 4.95, w: 4.4, h: 0.22, fontSize: 9.5, color: C.muted });
  // right: vertical journey of icons
  const n = s.journey.length, x0 = 5.55, y0 = 0.55, step = (4.6 - 0.62) / (n - 1), d = 0.62;
  for (const [i, j] of s.journey.entries()) {
    const y = y0 + i * step;
    if (i < n - 1) sl.addShape("line", { x: x0 + d / 2, y: y + d + 0.04, w: 0, h: step - d - 0.08, line: { color: C.line, width: 1.25, endArrowType: "triangle" } });
    await circle(sl, x0, y, d, [C.coral, C.navy, C.teal, C.navy, C.coral][i % 5], j.icon);
    text(sl, j.title, { x: x0 + d + 0.2, y: y + 0.05, w: 3.4, h: 0.26, fontSize: 13, bold: true });
    text(sl, j.text, { x: x0 + d + 0.2, y: y + 0.31, w: 3.4, h: 0.24, fontSize: 10.5, color: C.slate });
  }
};

K.map = async (ctx, s) => {
  header(ctx.slide, s);
  const sl = ctx.slide, rowH = 0.4, y0 = G.top + 0.02;
  for (const [i, r] of s.rows.entries()) {
    const y = y0 + i * rowH;
    if (i % 2 === 0) card(sl, G.MX, y, G.CW, rowH - 0.04);
    pill(sl, `S${i + 1}`, G.MX + 0.12, y + 0.07, 0.5, rowH - 0.18, i % 2 ? C.navy : C.coral, 9.5);
    text(sl, r.title, { x: G.MX + 0.78, y, w: 4.4, h: rowH - 0.04, fontSize: 12.5, bold: true, valign: "middle" });
    text(sl, r.focus, { x: G.MX + 5.25, y, w: 3.65, h: rowH - 0.04, fontSize: 10.5, color: C.slate, valign: "middle" });
  }
};

// Session opener: goals on the left, agenda card on the right (reference "Today's Goals & Agenda").
K.opener = async (ctx, s) => {
  const sl = ctx.slide;
  eyebrow(sl, s.eyebrow, G.MX, 0.26, G.CW);
  sl.addText(s.title, { placeholder: "title", fontSize: titleSize(s.title) });
  text(sl, s.subtitle, { x: G.MX, y: 1.12, w: G.CW, h: 0.3, fontSize: 13.5, color: C.slate });
  await renderColumn(ctx, [{ type: "icons", items: s.goals, size: 12, titleSize: 12.5, gap: 0.2 }], G.MX, 1.62, 4.25, 5.2);
  const ax = 5.2, aw = G.CW - (ax - G.MX), ay = 1.55, ah = 5.2 - ay;
  card(sl, ax, ay, aw, ah);
  eyebrow(sl, "Agenda", ax + 0.25, ay + 0.2, aw - 0.5, C.muted);
  const n = s.agenda.length, size = n > 10 ? 10.5 : 11.5, avail = ah - 0.62, step = Math.min(0.32, avail / n);
  for (const [i, a] of s.agenda.entries()) {
    const y = ay + 0.52 + i * step;
    sl.addShape("ellipse", { x: ax + 0.28, y: y + step / 2 - 0.04, w: 0.08, h: 0.08, fill: { color: C.muted }, line: { color: C.muted, width: 0 } });
    text(sl, a, { x: ax + 0.5, y, w: aw - 0.7, h: step, fontSize: size, valign: "middle" });
  }
};

// Session summary: what we built (left), key takeaways + next session (right).
K.summary = async (ctx, s) => {
  header(ctx.slide, s);
  const sl = ctx.slide;
  let y = G.top + 0.05;
  for (const [i, it] of s.built.entries()) {
    pill(sl, it.tag, G.MX, y + 0.03, 0.62, 0.26, i % 2 ? C.navy : C.coral, 8.5);
    text(sl, it.title, { x: G.MX + 0.8, y, w: 3.5, h: 0.26, fontSize: 12.5, bold: true });
    const th = textH(it.text, 10.5, 3.5);
    text(sl, it.text, { x: G.MX + 0.8, y: y + 0.27, w: 3.5, h: th + 0.02, fontSize: 10.5, color: C.slate });
    y += 0.27 + th + 0.13;
  }
  if (y > G.bottomNoDemo + 0.02) ctx.warn(`summary list ends at ${y.toFixed(2)}"`);
  const rx = 5.05, rw = G.CW - (rx - G.MX);
  const nextH = s.next ? 0.8 : 0;
  const kh = 5.2 - G.top - (s.next ? nextH + 0.18 : 0);
  card(sl, rx, G.top, rw, kh);
  eyebrow(sl, "Key takeaways", rx + 0.22, G.top + 0.16, rw - 0.44, C.teal);
  await renderColumn(ctx, [{ type: "bullets", items: s.takeaways, size: 11, gap: 0.08 }], rx + 0.22, G.top + 0.46, rw - 0.44, G.top + kh - 0.1);
  if (s.next) {
    const ny = G.top + kh + 0.18;
    card(sl, rx, ny, rw, nextH, C.navy);
    eyebrow(sl, "Next", rx + 0.22, ny + 0.13, rw - 0.44);
    text(sl, s.next, { x: rx + 0.22, y: ny + 0.36, w: rw - 0.44, h: 0.36, fontSize: 12, bold: true, color: C.white });
  }
};

module.exports = { K, defineMasters, MASTER, BLANK, OPENER };
