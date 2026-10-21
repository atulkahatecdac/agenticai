// Renders react-icons glyphs to PNG data URIs (white glyph by default) for use inside
// coloured circles, the same way the reference deck's icons are built.
// Icon names carry their pack prefix: Fa* -> fa6, Md* -> md, Lu* -> lu, Si* -> si, Tb* -> tb.

const React = require("react");
const ReactDOMServer = require("react-dom/server");
const sharp = require("sharp");

const PACKS = { Fa: "fa6", Md: "md", Lu: "lu", Si: "si", Tb: "tb", Bs: "bs", Pi: "pi" };
const cache = new Map();
const missing = new Set();

function component(name) {
  const pack = PACKS[name.slice(0, 2)];
  if (!pack) return null;
  return require(`react-icons/${pack}`)[name] || null;
}

async function iconData(name, color = "FFFFFF") {
  const key = `${name}:${color}`;
  if (cache.has(key)) return cache.get(key);
  const Icon = component(name);
  if (!Icon) {
    missing.add(name);
    return null;
  }
  const svg = ReactDOMServer.renderToStaticMarkup(React.createElement(Icon, { size: 256, color: `#${color}` }));
  const png = await sharp(Buffer.from(svg)).resize(256, 256).png().toBuffer();
  const data = "image/png;base64," + png.toString("base64");
  cache.set(key, data);
  return data;
}

module.exports = { iconData, missing };
