// Content blocks. Each block type has:
//   measure(b, w)               -> height in inches for width w
//   render(ctx, b, x, y, w, h)  -> draws it (async: icons are rasterised on demand)
// Columns of blocks are stacked by renderColumn(); slides.js decides the columns.

const { C, ACCENTS, F, G } = require("./theme");
const { runs, plain, textH, lineCount } = require("./text");
const { iconData } = require("./icons");

const pt = (p) => p / 72;
const accent = (i, c) => (c ? C[c] || c : ACCENTS[i % ACCENTS.length]);

// ------------------------------------------------------------------ primitives
function paraRuns(text, base = {}) {
  const ps = String(text).split("\n");
  const out = [];
  ps.forEach((p, i) => {
    const r = runs(p, base);
    if (!r.length) r.push({ text: " ", options: { ...base } });
    if (i < ps.length - 1) r[r.length - 1].options.breakLine = true;
    out.push(...r);
  });
  return out;
}

function text(slide, str, o) {
  slide.addText(paraRuns(str, {}), {
    fontFace: F.body, color: C.navy, margin: 0, valign: "top", isTextBox: true, fit: "none",
    paraSpaceAfter: 0, ...o,
  });
}

async function circle(slide, x, y, d, color, icon, label) {
  slide.addShape("ellipse", { x, y, w: d, h: d, fill: { color }, line: { color, width: 0 } });
  if (icon) {
    const data = await iconData(icon);
    if (data) {
      const s = d * 0.5;
      slide.addImage({ data, x: x + (d - s) / 2, y: y + (d - s) / 2, w: s, h: s, altText: icon });
    }
  } else if (label != null) {
    text(slide, String(label), { x, y, w: d, h: d, fontSize: Math.max(9, d * 30), bold: true, color: C.white, align: "center", valign: "middle" });
  }
}

function card(slide, x, y, w, h, fill = C.card) {
  slide.addShape("roundRect", { x, y, w, h, fill: { color: fill }, line: { color: fill, width: 0 }, rectRadius: 0.06 });
}

function pill(slide, label, x, y, w, h, fill = C.coral, size = 8.5) {
  slide.addShape("roundRect", { x, y, w, h, fill: { color: fill }, line: { color: fill, width: 0 }, rectRadius: h / 2 });
  text(slide, label, { x, y, w, h, fontSize: size, bold: true, color: C.white, align: "center", valign: "middle" });
}

function arrow(slide, x1, y1, x2, y2, color = C.line, dash) {
  slide.addShape("line", {
    x: Math.min(x1, x2), y: Math.min(y1, y2), w: Math.max(Math.abs(x2 - x1), 0.001), h: Math.max(Math.abs(y2 - y1), 0.001),
    flipH: x2 < x1, flipV: y2 < y1,
    line: { color, width: 1.25, endArrowType: "triangle", ...(dash ? { dashType: "dash" } : {}) },
  });
}

function eyebrow(slide, label, x, y, w, color = C.coral) {
  text(slide, label.toUpperCase(), { x, y, w, h: 0.2, fontSize: 9, bold: true, color, charSpacing: 2 });
}

// ------------------------------------------------------------------ block types
const B = {};

// Plain paragraph(s).
B.text = {
  measure: (b, w) => textH(b.text, b.size || 12, w) + 0.02,
  render: (ctx, b, x, y, w, h) =>
    text(ctx.slide, b.text, { x, y, w, h, fontSize: b.size || 12, color: b.color ? C[b.color] || b.color : C.navy, bold: !!b.bold, italic: !!b.italic, align: b.align || "left" }),
};

// Dot bullets, optional one level of sub-items: items: ["a", {text:"b", sub:["c"]}]
function bulletRows(b, w) {
  const size = b.size || 12, rows = [];
  for (const it of b.items) {
    const t = typeof it === "string" ? it : it.text;
    rows.push({ t, size, ind: 0, h: textH(t, size, w - 0.22) });
    for (const s of (typeof it === "string" ? [] : it.sub || [])) rows.push({ t: s, size: size - 1, ind: 0.24, h: textH(s, size - 1, w - 0.46) });
  }
  return rows;
}
// Bullets are real paragraphs in one text box, so PowerPoint does the spacing.
const PARA_GAP = 4; // pt after each paragraph
B.bullets = {
  measure: (b, w) => bulletRows(b, w).reduce((a, r) => a + r.h + pt(b.gapPt ?? PARA_GAP), 0),
  render: (ctx, b, x, y, w, h) => {
    const rs = bulletRows(b, w), out = [];
    rs.forEach((r, i) => {
      const para = runs(r.t, { fontSize: r.size, color: r.ind ? C.slate : C.navy });
      // paragraph options go on the first run only: pptxgenjs starts a new paragraph at every run with `bullet`
      Object.assign(para[0].options, {
        bullet: { characterCode: r.ind ? "2013" : "2022", indent: 13 }, indentLevel: r.ind ? 1 : 0,
        paraSpaceAfter: b.gapPt ?? PARA_GAP,
      });
      if (i < rs.length - 1) para[para.length - 1].options.breakLine = true;
      out.push(...para);
    });
    ctx.slide.addText(out, { x, y, w, h: Math.max(h, 0.2), fontFace: F.body, margin: 0, valign: "top", isTextBox: true, fit: "none" });
  },
};

// Title (bold) and description (grey) as two paragraphs of one text box.
function titleText(it, titleSize, size, extra = {}) {
  const r = [];
  if (it.title) r.push(...runs(it.title, { fontSize: titleSize, bold: true, color: C.navy }));
  if (it.title && it.text) r[r.length - 1].options.breakLine = true;
  if (it.text) r.push(...runs(it.text, { fontSize: size, color: extra.textColor || C.slate }));
  if (r[0]) r[0].options.paraSpaceAfter = 2;
  return r;
}

// Icon rows: icon in a coloured circle, bold title, grey description.
function iconRow(it, b, w) {
  const d = b.d || 0.42, tw = w - d - 0.16;
  const th = it.title ? textH(it.title, b.titleSize || 13, tw) : 0;
  const bh = it.text ? textH(it.text, b.size || 11.5, tw) : 0;
  return { d, tw, h: Math.max(d, th + bh + (it.title && it.text ? 0.03 : 0)) };
}
B.icons = {
  measure: (b, w) => b.items.reduce((a, it) => a + iconRow(it, b, w).h, 0) + (b.items.length - 1) * (b.gap ?? 0.16),
  render: async (ctx, b, x, y, w) => {
    let cy = y;
    for (const [i, it] of b.items.entries()) {
      const r = iconRow(it, b, w);
      await circle(ctx.slide, x, cy + (r.h - r.d) / 2, r.d, accent(i, it.color), it.icon, it.n);
      ctx.slide.addText(titleText(it, b.titleSize || 13, b.size || 11.5), {
        x: x + r.d + 0.16, y: cy, w: r.tw, h: r.h, fontFace: F.body, margin: 0, valign: "middle", isTextBox: true, fit: "none",
      });
      cy += r.h + (b.gap ?? 0.16);
    }
  },
};

// Numbered steps with coral number circles.
B.steps = {
  measure: (b, w) => B.icons.measure({ ...b, d: b.d || 0.32, titleSize: b.titleSize || 12.5, size: b.size || 11, items: norm(b.items) }, w),
  render: (ctx, b, x, y, w) =>
    B.icons.render(ctx, { ...b, d: b.d || 0.32, titleSize: b.titleSize || 12.5, size: b.size || 11, gap: b.gap ?? 0.13,
      items: norm(b.items).map((it, i) => ({ ...it, n: it.n ?? i + 1, color: it.color || (b.color || "coral") })) }, x, y, w),
};
function norm(items) { return items.map((it) => (typeof it === "string" ? { title: it } : it)); }

// Cards side by side: icon circle + title on one line, body lines below.
function cardDims(b, w) {
  const n = b.items.length, gap = b.gapX ?? 0.18, cw = (w - gap * (n - 1)) / n, pad = 0.18;
  const d = b.d || 0.42, iw = cw - pad * 2;
  const heads = b.items.map((it) => (it.icon || it.n != null ? Math.max(d, textH(it.title || "", b.titleSize || 14, iw - d - 0.12)) : textH(it.title || "", b.titleSize || 14, iw)));
  const bodies = b.items.map((it) => {
    const lines = it.lines || (it.text ? [it.text] : []);
    return lines.reduce((a, l) => a + textH(l, b.size || 11, iw) + 0.06, 0) + (it.code ? codeH(it.code, iw, b.codeSize || 9) + 0.08 : 0);
  });
  const h = Math.max(b.minH || 0, pad * 2 + Math.max(...heads) + 0.12 + Math.max(...bodies) + (b.items.some((it) => it.tag) ? 0.24 : 0));
  return { n, gap, cw, pad, d, iw, h };
}
B.cards = {
  measure: (b, w) => cardDims(b, w).h,
  render: async (ctx, b, x, y, w) => {
    const k = cardDims(b, w);
    for (const [i, it] of b.items.entries()) {
      const cx = x + i * (k.cw + k.gap);
      card(ctx.slide, cx, y, k.cw, k.h, it.fill ? C[it.fill] || it.fill : C.card);
      let cy = y + k.pad;
      if (it.tag) { eyebrow(ctx.slide, it.tag, cx + k.pad, cy, k.iw, it.tagColor ? C[it.tagColor] : C.coral); cy += 0.24; }
      let tx = cx + k.pad, tw = k.iw, hh = textH(it.title || "", b.titleSize || 14, k.iw);
      if (it.icon || it.n != null) {
        await circle(ctx.slide, cx + k.pad, cy, k.d, accent(i, it.color), it.icon, it.n);
        tx += k.d + 0.12; tw -= k.d + 0.12; hh = Math.max(k.d, textH(it.title || "", b.titleSize || 14, tw));
      }
      if (it.title) text(ctx.slide, it.title, { x: tx, y: cy, w: tw, h: hh, fontSize: b.titleSize || 14, bold: true, valign: it.icon || it.n != null ? "middle" : "top" });
      cy += hh + 0.12;
      const lines = it.lines || (it.text ? [it.text] : []);
      if (lines.length) {
        const r = [];
        lines.forEach((l, li) => {
          const p = runs(l, { fontSize: b.size || 11, color: C.navy, paraSpaceAfter: 4 });
          if (li < lines.length - 1) p[p.length - 1].options.breakLine = true;
          r.push(...p);
        });
        const bh = lines.reduce((a, l) => a + textH(l, b.size || 11, k.iw) + 0.06, 0);
        ctx.slide.addText(r, { x: cx + k.pad, y: cy, w: k.iw, h: bh, fontFace: F.body, margin: 0, valign: "top", isTextBox: true, fit: "none" });
        cy += bh;
      }
      if (it.code) { drawCode(ctx.slide, it.code, cx + k.pad, cy + 0.02, k.iw, b.codeSize || 9); }
    }
  },
};

// Grid of small tiles.
function tileDims(b, w) {
  const cols = b.cols || 3, gap = 0.14, tw = (w - gap * (cols - 1)) / cols, d = b.d || 0.34, pad = 0.13;
  const inner = tw - pad * 2 - d - 0.12;
  const hs = b.items.map((it) => Math.max(d, textH(it.title, b.titleSize || 12, inner) + (it.text ? textH(it.text, b.size || 10.5, inner) + 0.03 : 0)) + pad * 2);
  const rows = Math.ceil(b.items.length / cols);
  const rowH = [];
  for (let r = 0; r < rows; r++) rowH.push(Math.max(...hs.slice(r * cols, r * cols + cols)));
  return { cols, gap, tw, d, pad, inner, rowH, h: rowH.reduce((a, v) => a + v, 0) + gap * (rows - 1) };
}
B.tiles = {
  measure: (b, w) => tileDims(b, w).h,
  render: async (ctx, b, x, y, w) => {
    const k = tileDims(b, w);
    let ry = y;
    for (let r = 0; r < k.rowH.length; r++) {
      for (let c = 0; c < k.cols; c++) {
        const i = r * k.cols + c, it = b.items[i];
        if (!it) continue;
        const tx = x + c * (k.tw + k.gap);
        card(ctx.slide, tx, ry, k.tw, k.rowH[r]);
        await circle(ctx.slide, tx + k.pad, ry + k.pad, k.d, accent(i, it.color), it.icon, it.n);
        ctx.slide.addText(titleText(it, b.titleSize || 12, b.size || 10.5), {
          x: tx + k.pad + k.d + 0.12, y: ry + k.pad - 0.02, w: k.inner, h: k.rowH[r] - k.pad * 2 + 0.04, fontFace: F.body, margin: 0, valign: "top", isTextBox: true, fit: "none",
        });
      }
      ry += k.rowH[r] + k.gap;
    }
  },
};

// Horizontal flow: circles (with icon) or boxes (no icon), joined by arrows.
function flowDims(b, w) {
  const n = b.items.length, slot = w / n, boxes = !b.items.some((it) => it.icon || it.n != null);
  const d = b.d || 0.6, bw = slot - 0.22;
  const boxH = boxes ? Math.max(0.5, ...b.items.map((it) => textH(it.label, b.labelSize || 11, bw - 0.12) + 0.2)) : d;
  const lab = boxes ? 0 : Math.max(...b.items.map((it) => textH(it.label || "", b.labelSize || 12, slot - 0.08)));
  const cap = Math.max(0, ...b.items.map((it) => (it.caption ? textH(it.caption, b.size || 10, slot - 0.08) : 0)));
  const h = boxH + (boxes ? 0 : 0.08 + lab) + (cap ? 0.06 + cap : 0) + (b.loop ? 0.48 : 0);
  return { n, slot, boxes, d, bw, boxH, lab, cap, h };
}
B.flow = {
  measure: (b, w) => flowDims(b, w).h,
  render: async (ctx, b, x, y, w) => {
    const k = flowDims(b, w), s = ctx.slide;
    for (const [i, it] of b.items.entries()) {
      const cx = x + k.slot * i + k.slot / 2;
      if (k.boxes) {
        card(s, cx - k.bw / 2, y, k.bw, k.boxH, it.fill ? C[it.fill] || it.fill : C.card);
        text(s, it.label, { x: cx - k.bw / 2 + 0.06, y, w: k.bw - 0.12, h: k.boxH, fontSize: b.labelSize || 11, bold: true, align: "center", valign: "middle", color: it.fill && it.fill !== "card" ? C.white : C.navy });
      } else {
        await circle(s, cx - k.d / 2, y, k.d, accent(i, it.color), it.icon, it.n);
        text(s, it.label || "", { x: cx - k.slot / 2 + 0.04, y: y + k.d + 0.08, w: k.slot - 0.08, h: k.lab + 0.02, fontSize: b.labelSize || 12, bold: true, align: "center" });
      }
      if (it.caption) {
        const cy = y + k.boxH + (k.boxes ? 0.06 : 0.08 + k.lab + 0.06);
        text(s, it.caption, { x: cx - k.slot / 2 + 0.04, y: cy, w: k.slot - 0.08, h: k.cap + 0.02, fontSize: b.size || 10, color: C.slate, align: "center" });
      }
      if (i < k.n - 1) {
        const half = k.boxes ? k.bw / 2 : k.d / 2;
        arrow(s, cx + half + 0.05, y + k.boxH / 2, cx + k.slot - half - 0.05, y + k.boxH / 2);
      }
    }
    if (b.loop) {
      const ly = y + k.h - 0.08, x1 = x + k.slot / 2, x2 = x + k.slot * (k.n - 0.5);
      arrow(s, x2, ly, x1, ly, C.coral, true);
      text(s, b.loop, { x: x1, y: ly - 0.24, w: x2 - x1, h: 0.2, fontSize: 9.5, color: C.coral, bold: true, align: "center" });
    }
  },
};

// Code panel (navy), optional caption above. Lines starting with # or // are dimmed.
function codeSize(code, w, size) {
  const lines = code.split("\n");
  let s = size;
  // shrink long-line code a little (down to 8.5pt) rather than wrap it; past that, lines wrap
  while (s > 8.5 && Math.max(...lines.map((l) => l.length)) * s * 0.6 > (w - 0.3) * 72) s -= 0.5;
  return s;
}
function codeH(code, w, size = 9.5) {
  const s = codeSize(code, w, size);
  return code.split("\n").reduce((a, l) => a + lineCount(l || " ", s, w - 0.3, F.code), 0) * pt(s) * 1.18 + 0.26;
}
function drawCode(slide, code, x, y, w, size = 9.5) {
  const s = codeSize(code, w, size), h = codeH(code, w, size);
  slide.addShape("roundRect", { x, y, w, h, fill: { color: C.navy }, line: { color: C.navy, width: 0 }, rectRadius: 0.05 });
  const lines = code.split("\n");
  const r = lines.map((l, i) => ({
    text: l || " ",
    options: { color: /^\s*(#|\/\/)/.test(l) ? C.codeComment : C.codeText, breakLine: i < lines.length - 1 },
  }));
  slide.addText(r, { x: x + 0.15, y: y + 0.12, w: w - 0.3, h: h - 0.2, fontFace: F.code, fontSize: s, margin: 0, valign: "top", isTextBox: true, lineSpacingMultiple: 0.98, fit: "none" });
  return h;
}
B.code = {
  measure: (b, w) => (b.caption ? 0.26 : 0) + codeH(b.code, w, b.size || 9.5),
  render: (ctx, b, x, y, w) => {
    let cy = y;
    if (b.caption) { text(ctx.slide, b.caption, { x, y: cy, w, h: 0.22, fontSize: 11, bold: true }); cy += 0.26; }
    drawCode(ctx.slide, b.code, x, cy, w, b.size || 9.5);
  },
};

// Table: navy header, alternating pale rows.
function tableDims(b, w) {
  const size = b.size || 10, cols = b.head.length;
  const fr = b.widths || Array(cols).fill(1);
  const tot = fr.reduce((a, v) => a + v, 0);
  const colW = fr.map((f) => (f / tot) * w);
  const rowH = (cells, s) => Math.max(...cells.map((c, i) => textH(c, s, colW[i] - 0.14))) + 0.1;
  const heads = rowH(b.head, size);
  const rows = b.rows.map((r) => rowH(r, size));
  return { size, colW, heads, rows, h: heads + rows.reduce((a, v) => a + v, 0) };
}
B.table = {
  measure: (b, w) => tableDims(b, w).h,
  render: (ctx, b, x, y, w) => {
    const k = tableDims(b, w);
    const border = { type: "solid", pt: 0.5, color: C.line };
    const head = b.head.map((h) => ({ text: runs(h), options: { bold: true, color: C.white, fill: { color: b.headColor ? C[b.headColor] : C.navy }, valign: "middle" } }));
    const body = b.rows.map((r, ri) => r.map((c, ci) => ({
      text: runs(c),
      options: { color: C.navy, bold: ci === 0 && b.firstBold !== false, fill: { color: ri % 2 ? C.card : C.white }, valign: "middle" },
    })));
    ctx.slide.addTable([head, ...body], {
      x, y, w, colW: k.colW, rowH: [k.heads, ...k.rows], fontFace: F.body, fontSize: k.size, border, margin: [0.04, 0.07, 0.04, 0.07], autoPage: false,
    });
  },
};

// Two or three columns of bullets, each under a coloured header pill.
function compareDims(b, w) {
  const n = b.cols.length, gap = 0.2, cw = (w - gap * (n - 1)) / n;
  const bodies = b.cols.map((c) => (c.items ? B.bullets.measure({ items: c.items, size: b.size || 11.5 }, cw - 0.3) : 0) + (c.code ? codeH(c.code, cw - 0.3, b.codeSize || 9) + 0.08 : 0));
  return { n, gap, cw, h: 0.42 + 0.14 + Math.max(...bodies) + 0.16 };
}
B.compare = {
  measure: (b, w) => compareDims(b, w).h,
  render: async (ctx, b, x, y, w) => {
    const k = compareDims(b, w);
    for (const [i, c] of b.cols.entries()) {
      const cx = x + i * (k.cw + k.gap), col = accent(i, c.color);
      card(ctx.slide, cx, y, k.cw, k.h);
      ctx.slide.addShape("roundRect", { x: cx, y, w: k.cw, h: 0.42, fill: { color: col }, line: { color: col, width: 0 }, rectRadius: 0.06 });
      text(ctx.slide, c.title, { x: cx + 0.15, y, w: k.cw - 0.3, h: 0.42, fontSize: 13, bold: true, color: C.white, valign: "middle" });
      let cy = y + 0.56;
      if (c.items) { B.bullets.render(ctx, { items: c.items, size: b.size || 11.5 }, cx + 0.15, cy, k.cw - 0.3); cy += B.bullets.measure({ items: c.items, size: b.size || 11.5 }, k.cw - 0.3) + 0.04; }
      if (c.code) drawCode(ctx.slide, c.code, cx + 0.15, cy, k.cw - 0.3, b.codeSize || 9);
    }
  },
};

// Highlight box: dark (navy, like the reference "NEXT" box), light (pale card) or plain.
B.callout = {
  measure: (b, w) => 0.2 + (b.eyebrow ? 0.24 : 0) + textH(b.text, b.size || 12, w - 0.36) + 0.06,
  render: (ctx, b, x, y, w, h) => {
    const dark = b.style === "dark";
    card(ctx.slide, x, y, w, h, dark ? C.navy : C.card);
    let cy = y + 0.12;
    if (b.eyebrow) { eyebrow(ctx.slide, b.eyebrow, x + 0.18, cy, w - 0.36, dark ? C.coral : C.teal); cy += 0.24; }
    text(ctx.slide, b.text, { x: x + 0.18, y: cy, w: w - 0.36, h: h - (cy - y) - 0.08, fontSize: b.size || 12, bold: dark, color: dark ? C.white : C.navy });
  },
};

// A chain of small boxes joined by arrows, wrapping onto more rows if needed.
function chainLayout(b, w) {
  const size = b.size || 10.5, h = 0.34, gapA = 0.26;
  const widths = b.items.map((t) => Math.min(w, plain(t).length * pt(size) * 0.52 + 0.26));
  const rows = [[]];
  let cx = 0;
  widths.forEach((bw, i) => {
    if (cx + bw > w + 0.001 && rows[rows.length - 1].length) { rows.push([]); cx = 0; }
    rows[rows.length - 1].push({ i, x: cx, w: bw });
    cx += bw + gapA;
  });
  return { size, h, rows, total: rows.length * h + (rows.length - 1) * 0.12 };
}
B.chain = {
  measure: (b, w) => chainLayout(b, w).total,
  render: (ctx, b, x, y, w) => {
    const k = chainLayout(b, w);
    k.rows.forEach((row, ri) => {
      const ry = y + ri * (k.h + 0.12);
      row.forEach((c, j) => {
        const hi = (b.highlight || []).includes(c.i);
        card(ctx.slide, x + c.x, ry, c.w, k.h, hi ? C.navy : C.card);
        text(ctx.slide, b.items[c.i], { x: x + c.x, y: ry, w: c.w, h: k.h, fontSize: k.size, bold: true, color: hi ? C.white : C.navy, align: "center", valign: "middle" });
        if (j < row.length - 1) arrow(ctx.slide, x + c.x + c.w + 0.03, ry + k.h / 2, x + row[j + 1].x - 0.03, ry + k.h / 2);
      });
    });
  },
};

// Top-down diagram: rows of boxes; every box in a row connects to every box in the next row
// (so 1 → 2 fans out and 2 → 1 joins). rows: [[{label, fill}], ...]; labels[i] annotates gap i.
function treeDims(b, w) {
  const boxH = b.boxH || 0.4, gapY = b.gapY || (b.labels ? 0.42 : 0.3), size = b.size || 11;
  const rows = b.rows.map((row) => {
    const n = row.length, gx = 0.3, bw = Math.min(b.boxW || 2.6, (w - gx * (n - 1)) / n);
    const total = bw * n + gx * (n - 1), x0 = (w - total) / 2;
    return row.map((it, i) => ({ ...(typeof it === "string" ? { label: it } : it), x: x0 + i * (bw + gx), w: bw }));
  });
  return { boxH, gapY, size, rows, h: rows.length * boxH + (rows.length - 1) * gapY };
}
B.tree = {
  measure: (b, w) => treeDims(b, w).h,
  render: async (ctx, b, x, y, w) => {
    const k = treeDims(b, w), s = ctx.slide;
    k.rows.forEach((row, ri) => {
      const ry = y + ri * (k.boxH + k.gapY);
      if (ri < k.rows.length - 1) {
        const ny = ry + k.boxH + k.gapY;
        for (const a of row) for (const c of k.rows[ri + 1]) arrow(s, x + a.x + a.w / 2, ry + k.boxH + 0.03, x + c.x + c.w / 2, ny - 0.03);
        const lab = (b.labels || [])[ri];
        if (lab) text(s, lab, { x: x + w / 2 + 0.12, y: ry + k.boxH + 0.06, w: w / 2 - 0.12, h: k.gapY - 0.1, fontSize: 9.5, color: C.slate, italic: true, valign: "middle" });
      }
      for (const it of row) {
        const fill = it.fill ? C[it.fill] || it.fill : C.card, dark = fill !== C.card;
        card(s, x + it.x, ry, it.w, k.boxH, fill);
        text(s, it.label, { x: x + it.x + 0.06, y: ry, w: it.w - 0.12, h: k.boxH, fontSize: k.size, bold: true, align: "center", valign: "middle", color: dark ? C.white : C.navy });
      }
    });
  },
};

// Image fitted into the available box, keeping its aspect ratio.
B.image = {
  measure: (b, w) => (b.h ? b.h : (w / b.ratio)),
  render: (ctx, b, x, y, w, h) => {
    let iw = w, ih = w / b.ratio;
    if (ih > h) { ih = h; iw = h * b.ratio; }
    ctx.slide.addImage({ path: b.path, x: x + (w - iw) / 2, y, w: iw, h: ih, altText: b.alt || "" });
  },
};

// Side-by-side columns of blocks inside a column.
B.cols = {
  measure: (b, w) => {
    const ws = colWidths(b, w);
    return Math.max(...b.cols.map((blocks, i) => columnH(blocks, ws[i])));
  },
  render: async (ctx, b, x, y, w, h) => {
    const ws = colWidths(b, w);
    let cx = x;
    for (const [i, blocks] of b.cols.entries()) { await renderColumn(ctx, blocks, cx, y, ws[i], y + h); cx += ws[i] + (b.gap ?? 0.35); }
  },
};
function colWidths(b, w) {
  const r = b.ratio || b.cols.map(() => 1), gap = b.gap ?? 0.35, tot = r.reduce((a, v) => a + v, 0);
  return r.map((v) => ((w - gap * (b.cols.length - 1)) * v) / tot);
}

// ------------------------------------------------------------------ columns
function blockH(b, w) {
  const t = B[b.type];
  if (!t) throw new Error(`unknown block type "${b.type}"`);
  return b.h || t.measure(b, w);
}
function columnH(blocks, w) {
  return blocks.reduce((a, b, i) => a + blockH(b, w) + (i ? b.gapBefore ?? G.gap : 0), 0);
}
async function renderColumn(ctx, blocks, x, y, w, maxY, extraGap = 0) {
  let cy = y;
  for (const [i, b] of blocks.entries()) {
    if (i) cy += (b.gapBefore ?? G.gap) + extraGap;
    let h = blockH(b, w);
    if (b.type === "image" && cy + h > maxY) h = maxY - cy;
    await B[b.type].render(ctx, b, x, cy, w, h);
    cy += h;
  }
  if (cy > maxY + 0.02) ctx.warn(`content ends at ${cy.toFixed(2)}" (limit ${maxY.toFixed(2)}")`);
  return cy - y;
}

module.exports = { B, renderColumn, columnH, text, circle, card, pill, arrow, eyebrow, drawCode, paraRuns };
