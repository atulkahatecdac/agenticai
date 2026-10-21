// Inline markup and text-size estimation.
//   **bold**    -> bold run
//   `code`      -> Courier New run in the accent colour
// Estimation is deliberately a little pessimistic so the overflow check errs on the safe side.

const { C, F } = require("./theme");

function runs(str, base = {}) {
  const out = [];
  for (const part of String(str).split(/(\*\*[^*]+\*\*|`[^`]+`)/)) {
    if (!part) continue;
    if (part.startsWith("**")) out.push({ text: part.slice(2, -2), options: { ...base, bold: true } });
    else if (part.startsWith("`")) out.push({ text: part.slice(1, -1), options: { ...base, fontFace: F.code, color: C.coral } });
    else out.push({ text: part, options: { ...base } });
  }
  return out;
}

const plain = (s) => String(s).replace(/\*\*|`/g, "");

// Average glyph width as a fraction of the font size.
const WIDTH = { [F.body]: 0.47, [F.code]: 0.6 };

function lineCount(str, sizePt, widthIn, font = F.body) {
  const perLine = Math.max(1, (widthIn * 72) / (sizePt * (WIDTH[font] || 0.5)));
  let n = 0;
  for (const para of plain(str).split("\n")) n += Math.max(1, Math.ceil((para.length * 1.04) / perLine));
  return n;
}

// Height (inches) of a block of text.
function textH(str, sizePt, widthIn, font = F.body, leading = 1.2) {
  return (lineCount(str, sizePt, widthIn, font) * sizePt * leading) / 72;
}

module.exports = { runs, plain, lineCount, textH };
