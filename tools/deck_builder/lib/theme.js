// Design tokens, taken from the reference deck (no-code-low-code-1.pptx):
// navy text and panels, coral accent, teal secondary, grey subtitles, pale cards.
// All geometry is in inches on the 10" x 5.625" (16:9) canvas.

const C = {
  navy: "1F2A44",
  coral: "EA4B71",
  teal: "1A7F8E",
  slate: "5B6475",   // subtitles, secondary text
  muted: "8A93A3",   // captions
  line: "D5DAE3",    // borders, connectors
  card: "F4F6FA",    // card fill
  white: "FFFFFF",
  codeText: "E8ECF3",
  codeComment: "9FB0CC",
  good: "1A7F8E",
  bad: "EA4B71",
};

// Icon-circle colours cycle through these unless an item names its own.
const ACCENTS = [C.navy, C.coral, C.teal, C.slate];

const F = { body: "Calibri", code: "Courier New" };

const G = {
  W: 10,
  H: 5.625,
  MX: 0.5,                 // left/right margin
  CW: 9.0,                 // content width
  titleY: 0.3, titleH: 0.55,
  subY: 0.86, subH: 0.3,
  top: 1.34,               // content top when there is a subtitle
  topNoSub: 1.05,
  bottom: 5.0,             // content bottom when the DEMO bar is shown
  bottomNoDemo: 5.2,
  demoY: 5.12, demoH: 0.3,
  gap: 0.18,               // vertical gap between blocks
};

module.exports = { C, ACCENTS, F, G };
