import fs from "node:fs";
import path from "node:path";
import sharp from "file:///C:/Users/evagh/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/sharp/dist/index.mjs";

const OUT = path.resolve("output/chapter4_final_diagrams");
fs.mkdirSync(OUT, { recursive: true });

const C = {
  ink: "#171717",
  dark: "#303030",
  mid: "#777777",
  line: "#444444",
  pale: "#f2f2f2",
  pale2: "#e7e7e7",
  white: "#ffffff",
};

const escapeXml = (value) => String(value)
  .replaceAll("&", "&amp;")
  .replaceAll("<", "&lt;")
  .replaceAll(">", "&gt;")
  .replaceAll('"', "&quot;");

function wrapWords(text, maxChars = 28) {
  const words = String(text).split(/\s+/);
  const lines = [];
  let line = "";
  for (const word of words) {
    const candidate = line ? `${line} ${word}` : word;
    if (candidate.length > maxChars && line) {
      lines.push(line);
      line = word;
    } else {
      line = candidate;
    }
  }
  if (line) lines.push(line);
  return lines;
}

class Svg {
  constructor(width, height, title, subtitle = "") {
    this.width = width;
    this.height = height;
    this.parts = [];
    this.parts.push(`<rect width="${width}" height="${height}" fill="${C.white}"/>`);
    this.text(width / 2, 48, title.toUpperCase(), { size: 24, weight: 700, anchor: "middle" });
    if (subtitle) this.text(width / 2, 78, subtitle, { size: 14, anchor: "middle", fill: C.mid, letter: 1.2 });
    this.line(50, 98, width - 50, 98, { width: 1.5, color: C.ink });
  }

  rect(x, y, width, height, options = {}) {
    const { fill = C.white, stroke = C.line, rx = 8, sw = 1.7, dash = "" } = options;
    this.parts.push(`<rect x="${x}" y="${y}" width="${width}" height="${height}" rx="${rx}" fill="${fill}" stroke="${stroke}" stroke-width="${sw}"${dash ? ` stroke-dasharray="${dash}"` : ""}/>`);
  }

  circle(cx, cy, r, options = {}) {
    const { fill = C.white, stroke = C.line, sw = 1.7 } = options;
    this.parts.push(`<circle cx="${cx}" cy="${cy}" r="${r}" fill="${fill}" stroke="${stroke}" stroke-width="${sw}"/>`);
  }

  ellipse(cx, cy, rx, ry, options = {}) {
    const { fill = C.white, stroke = C.line, sw = 1.7, dash = "" } = options;
    this.parts.push(`<ellipse cx="${cx}" cy="${cy}" rx="${rx}" ry="${ry}" fill="${fill}" stroke="${stroke}" stroke-width="${sw}"${dash ? ` stroke-dasharray="${dash}"` : ""}/>`);
  }

  line(x1, y1, x2, y2, options = {}) {
    const { color = C.line, width = 1.7, dash = "", arrow = false, startArrow = false } = options;
    this.parts.push(`<line x1="${x1}" y1="${y1}" x2="${x2}" y2="${y2}" stroke="${color}" stroke-width="${width}"${dash ? ` stroke-dasharray="${dash}"` : ""}${arrow ? ' marker-end="url(#arrow)"' : ""}${startArrow ? ' marker-start="url(#arrow-start)"' : ""}/>`);
  }

  polyline(points, options = {}) {
    const { color = C.line, width = 1.7, dash = "", arrow = true, fill = "none" } = options;
    const value = points.map(([x, y]) => `${x},${y}`).join(" ");
    this.parts.push(`<polyline points="${value}" fill="${fill}" stroke="${color}" stroke-width="${width}" stroke-linejoin="round"${dash ? ` stroke-dasharray="${dash}"` : ""}${arrow ? ' marker-end="url(#arrow)"' : ""}/>`);
  }

  path(d, options = {}) {
    const { color = C.line, width = 1.7, dash = "", arrow = true, fill = "none" } = options;
    this.parts.push(`<path d="${d}" fill="${fill}" stroke="${color}" stroke-width="${width}" stroke-linejoin="round"${dash ? ` stroke-dasharray="${dash}"` : ""}${arrow ? ' marker-end="url(#arrow)"' : ""}/>`);
  }

  text(x, y, value, options = {}) {
    const { size = 16, weight = 400, anchor = "start", fill = C.ink, italic = false, letter = 0 } = options;
    this.parts.push(`<text x="${x}" y="${y}" font-family="Arial, Helvetica, sans-serif" font-size="${size}" font-weight="${weight}" text-anchor="${anchor}" fill="${fill}"${italic ? ' font-style="italic"' : ""}${letter ? ` letter-spacing="${letter}"` : ""}>${escapeXml(value)}</text>`);
  }

  lines(x, y, values, options = {}) {
    const { size = 16, weight = 400, anchor = "start", fill = C.ink, lineHeight = size * 1.25, italic = false } = options;
    values.forEach((value, index) => this.text(x, y + index * lineHeight, value, { size, weight, anchor, fill, italic }));
  }

  label(x, y, value, options = {}) {
    const { size = 13, fill = C.white, stroke = "none", padding = 5 } = options;
    const width = Math.max(34, value.length * size * 0.58 + padding * 2);
    this.rect(x - width / 2, y - size + 1, width, size + padding * 1.2, { fill, stroke, rx: 3, sw: stroke === "none" ? 0 : 1 });
    this.text(x, y, value, { size, anchor: "middle", fill: C.ink, weight: 700 });
  }

  node(x, y, width, height, label, options = {}) {
    const { fill = C.white, stroke = C.line, rx = 10, size = 16, weight = 500, maxChars = 30, dash = "" } = options;
    this.rect(x, y, width, height, { fill, stroke, rx, sw: 1.8, dash });
    const lines = Array.isArray(label) ? label : wrapWords(label, maxChars);
    const lineHeight = size * 1.25;
    const firstY = y + height / 2 - ((lines.length - 1) * lineHeight) / 2 + size * 0.35;
    this.lines(x + width / 2, firstY, lines, { size, weight, anchor: "middle", lineHeight });
  }

  diamond(cx, cy, width, height, label, options = {}) {
    const fill = options.fill ?? C.white;
    this.parts.push(`<polygon points="${cx},${cy - height / 2} ${cx + width / 2},${cy} ${cx},${cy + height / 2} ${cx - width / 2},${cy}" fill="${fill}" stroke="${C.line}" stroke-width="1.8"/>`);
    const lines = Array.isArray(label) ? label : wrapWords(label, options.maxChars ?? 20);
    const size = options.size ?? 14;
    const lineHeight = size * 1.15;
    const firstY = cy - ((lines.length - 1) * lineHeight) / 2 + size * 0.35;
    this.lines(cx, firstY, lines, { size, weight: 600, anchor: "middle", lineHeight });
  }

  start(cx, cy) {
    this.circle(cx, cy, 9, { fill: C.ink, stroke: C.ink, sw: 1 });
  }

  end(cx, cy) {
    this.circle(cx, cy, 12, { fill: C.white, stroke: C.ink, sw: 2 });
    this.circle(cx, cy, 6, { fill: C.ink, stroke: C.ink, sw: 1 });
  }

  actor(cx, cy, label) {
    this.circle(cx, cy - 58, 18, { fill: C.white, stroke: C.ink, sw: 2 });
    this.line(cx, cy - 40, cx, cy + 20, { color: C.ink, width: 2 });
    this.line(cx - 28, cy - 15, cx + 28, cy - 15, { color: C.ink, width: 2 });
    this.line(cx, cy + 20, cx - 25, cy + 58, { color: C.ink, width: 2 });
    this.line(cx, cy + 20, cx + 25, cy + 58, { color: C.ink, width: 2 });
    this.text(cx, cy + 84, label, { size: 16, weight: 700, anchor: "middle" });
  }

  finish() {
    const defs = `<defs>
      <marker id="arrow" markerWidth="10" markerHeight="10" refX="9" refY="3" orient="auto" markerUnits="strokeWidth"><path d="M0,0 L0,6 L9,3 z" fill="${C.line}"/></marker>
      <marker id="arrow-start" markerWidth="10" markerHeight="10" refX="1" refY="3" orient="auto-start-reverse" markerUnits="strokeWidth"><path d="M9,0 L9,6 L0,3 z" fill="${C.line}"/></marker>
    </defs>`;
    return `<svg xmlns="http://www.w3.org/2000/svg" width="${this.width}" height="${this.height}" viewBox="0 0 ${this.width} ${this.height}" role="img">${defs}${this.parts.join("")}</svg>`;
  }
}

async function save(name, svg) {
  const svgPath = path.join(OUT, `${name}.svg`);
  const pngPath = path.join(OUT, `${name}.png`);
  fs.writeFileSync(svgPath, svg, "utf8");
  await sharp(Buffer.from(svg), { density: 150 }).flatten({ background: C.white }).png().toFile(pngPath);
  return { name, svgPath, pngPath };
}

function useCaseDiagram() {
  const s = new Svg(1800, 1120, "Spendly Personal Finance Management System", "FINAL USE CASE DIAGRAM");
  s.rect(190, 125, 1420, 930, { rx: 3, sw: 2.2 });
  s.text(900, 154, "Spendly Personal Finance Management System", { size: 17, weight: 700, anchor: "middle" });
  s.actor(92, 535, "App user");
  s.actor(1708, 535, "Administrator");

  const userBasic = [
    [430, 220, "Register account"],
    [430, 310, "Sign in"],
    [430, 400, "Manage profile and consent"],
    [430, 490, "Manage transactions"],
    [430, 580, "Import transaction CSV"],
    [430, 670, "Manage budgets"],
    [430, 760, "View dashboard and analytics"],
    [430, 850, "View analysis history"],
  ];
  const userInsight = [
    [855, 260, "Generate spending insights"],
    [855, 380, "Forecast next-week spending"],
    [855, 500, "Detect unusual spending"],
    [855, 620, "Generate rule-based recommendations"],
    [855, 760, "View forecast"],
    [855, 850, "Review unusual-spending alerts"],
    [855, 940, "View personalised recommendations"],
  ];
  const admin = [
    [1355, 205, "Sign in to admin console"],
    [1355, 295, "Search and inspect accounts"],
    [1355, 385, "Update profile or access; revoke sessions"],
    [1355, 475, "Manage user transactions and budgets"],
    [1355, 565, "View stored insights (read-only)"],
    [1355, 655, "Export account data"],
    [1355, 745, "Delete disabled account"],
    [1355, 835, "View model information and audit log"],
    [1355, 925, "Pause or resume new analysis"],
  ];

  for (const [x, y] of [...userBasic, userInsight[0], ...userInsight.slice(4)]) s.line(120, 520, x - 145, y, { width: 1.1 });
  for (const [x, y] of admin) s.line(1680, 520, x + 150, y, { width: 1.1 });
  for (const [x, y, label] of userBasic) {
    s.ellipse(x, y, 145, 34, { fill: C.white });
    s.lines(x, y - (wrapWords(label, 30).length - 1) * 8 + 5, wrapWords(label, 30), { size: 14, anchor: "middle", lineHeight: 16 });
  }
  for (const [x, y, label] of userInsight) {
    s.ellipse(x, y, 160, 38, { fill: label === "Generate spending insights" ? C.pale2 : C.white });
    s.lines(x, y - (wrapWords(label, 31).length - 1) * 8 + 5, wrapWords(label, 31), { size: 14, weight: label === "Generate spending insights" ? 700 : 400, anchor: "middle", lineHeight: 16 });
  }
  for (const [x, y, label] of admin) {
    s.ellipse(x, y, 150, 34, { fill: C.white });
    s.lines(x, y - (wrapWords(label, 31).length - 1) * 8 + 5, wrapWords(label, 31), { size: 13.5, anchor: "middle", lineHeight: 16 });
  }
  s.line(855, 298, 855, 340, { dash: "7 5", arrow: true, width: 1.5 });
  s.label(760, 326, "<<include>>", { size: 11 });
  s.polyline([[1015, 260], [1075, 260], [1075, 500], [1015, 500]], { dash: "7 5", arrow: true, width: 1.5 });
  s.label(1075, 382, "<<include>>", { size: 11 });
  s.polyline([[695, 260], [635, 260], [635, 620], [695, 620]], { dash: "7 5", arrow: true, width: 1.5 });
  s.label(635, 442, "<<include>>", { size: 11 });
  s.text(270, 1018, "User services", { size: 13, weight: 700, fill: C.mid });
  s.text(1480, 1018, "Browser-only administrator console", { size: 13, weight: 700, fill: C.mid, anchor: "end" });
  return s.finish();
}

function addImportActivity() {
  const s = new Svg(1200, 1640, "Spendly Personal Finance Management System", "ADD OR IMPORT TRANSACTION - ACTIVITY DIAGRAM");
  const cx = 600;
  s.start(cx, 130);
  s.line(cx, 140, cx, 170, { arrow: true });
  s.node(430, 170, 340, 62, "Open Transactions and choose Add or Import");
  s.line(cx, 232, cx, 278, { arrow: true });
  s.diamond(cx, 330, 250, 104, "Entry method?");
  s.polyline([[475, 330], [255, 330], [255, 405]], { arrow: true });
  s.label(350, 318, "Manual entry", { size: 12 });
  s.polyline([[725, 330], [945, 330], [945, 405]], { arrow: true });
  s.label(850, 318, "CSV import", { size: 12 });
  s.node(100, 405, 310, 75, "Enter transaction details", { maxChars: 26 });
  s.node(790, 405, 310, 75, "Select and upload CSV file", { maxChars: 26 });
  s.line(255, 480, 255, 555, { arrow: true });
  s.node(100, 555, 310, 75, "Validate amount, date, type and category", { maxChars: 25 });
  s.line(945, 480, 945, 520, { arrow: true });
  s.node(790, 520, 310, 75, "Parse and normalise CSV rows", { maxChars: 26 });
  s.line(945, 595, 945, 635, { arrow: true });
  s.node(790, 635, 310, 75, "Validate required columns and row values", { maxChars: 27 });
  s.polyline([[255, 630], [255, 750], [600, 750], [600, 790]], { arrow: true });
  s.polyline([[945, 710], [945, 750], [600, 750]], { arrow: false });
  s.node(420, 790, 360, 72, "Check duplicates and confirm category text", { maxChars: 32 });
  s.line(cx, 862, cx, 905, { arrow: true });
  s.diamond(cx, 963, 270, 116, ["Any validation, duplicate", "or category issue?"]);
  s.polyline([[735, 963], [960, 963], [960, 1065]], { arrow: true });
  s.label(845, 950, "Yes", { size: 12 });
  s.node(790, 1065, 340, 80, ["Show the affected row or field", "and request correction"], { size: 15 });
  s.polyline([[960, 1145], [960, 1220], [1125, 1220], [1125, 370], [945, 370], [945, 405]], { arrow: true, dash: "7 5" });
  s.polyline([[960, 1145], [960, 1255], [75, 1255], [75, 370], [255, 370], [255, 405]], { arrow: true, dash: "7 5" });
  s.label(1110, 1188, "CSV: reselect file", { size: 11 });
  s.label(148, 1223, "Manual: correct input", { size: 11 });
  s.line(cx, 1021, cx, 1080, { arrow: true });
  s.label(630, 1055, "No", { size: 12 });
  s.node(420, 1080, 360, 68, "Save transaction record(s)", { fill: C.pale2 });
  s.line(cx, 1148, cx, 1195, { arrow: true });
  s.node(420, 1195, 360, 72, "Refresh spending summary and budget progress");
  s.line(cx, 1267, cx, 1320, { arrow: true });
  s.node(420, 1320, 360, 68, "Display success confirmation");
  s.line(cx, 1388, cx, 1450, { arrow: true });
  s.end(cx, 1466);
  s.rect(55, 1510, 1090, 72, { fill: C.pale, stroke: C.mid, rx: 5, sw: 1.2 });
  s.lines(80, 1538, ["Correction paths return to the relevant source input; detected issues never flow directly to save.", "Categories remain text values in the current schema; the UI may offer suggestions without a categories table."], { size: 13, lineHeight: 20 });
  return s.finish();
}

function insightsActivity() {
  const s = new Svg(1320, 1720, "Spendly Personal Finance Management System", "GENERATE SPENDING INSIGHTS - ACTIVITY DIAGRAM");
  const cx = 660;
  s.start(cx, 130);
  s.line(cx, 140, cx, 170, { arrow: true });
  s.node(465, 170, 390, 62, "Request fresh spending insights");
  s.line(cx, 232, cx, 276, { arrow: true });
  s.node(465, 276, 390, 70, "Validate JWT, active user and analysis setting");
  s.line(cx, 346, cx, 390, { arrow: true });
  s.diamond(cx, 445, 260, 110, "Request accepted?");
  s.polyline([[530, 445], [225, 445], [225, 535]], { arrow: true });
  s.label(375, 432, "No", { size: 12 });
  s.node(75, 535, 300, 78, "Return API error envelope and display message", { maxChars: 26 });
  s.line(225, 613, 225, 660, { arrow: true });
  s.end(225, 677);
  s.line(cx, 500, cx, 550, { arrow: true });
  s.label(690, 530, "Yes", { size: 12 });
  s.node(465, 550, 390, 70, "Retrieve the user's transactions and active budgets");
  s.line(cx, 620, cx, 662, { arrow: true });
  s.diamond(cx, 720, 290, 116, ["Usable spending", "history available?"]);
  s.polyline([[515, 720], [225, 720], [225, 810]], { arrow: true });
  s.label(370, 707, "No", { size: 12 });
  s.node(75, 810, 300, 75, "Ask user to add or import transactions");
  s.line(225, 885, 225, 930, { arrow: true });
  s.end(225, 947);
  s.line(cx, 778, cx, 825, { arrow: true });
  s.label(690, 806, "Yes", { size: 12 });
  s.node(465, 825, 390, 68, "Prepare weekly and transaction features");
  s.line(cx, 893, cx, 930, { arrow: true });
  s.rect(270, 930, 780, 12, { fill: C.ink, stroke: C.ink, rx: 0, sw: 0 });
  s.polyline([[500, 942], [500, 990], [350, 990], [350, 1035]], { arrow: true });
  s.polyline([[820, 942], [820, 990], [970, 990], [970, 1035]], { arrow: true });
  s.diamond(350, 1095, 260, 120, ["Eight or more complete", "weeks of history?"]);
  s.node(820, 1035, 300, 120, ["Score expense transactions", "with Isolation Forest v1"], { fill: C.pale });
  s.polyline([[220, 1095], [90, 1095], [90, 1215], [215, 1215]], { arrow: true });
  s.label(145, 1082, "Fewer than 8 weeks", { size: 11 });
  s.node(215, 1180, 270, 80, ["Use personal weekly-average", "forecast fallback"], { size: 14.5 });
  s.polyline([[480, 1095], [610, 1095], [610, 1215], [485, 1215]], { arrow: true });
  s.label(565, 1082, "8 or more weeks", { size: 11 });
  s.node(485, 1180, 270, 80, ["Generate next-week forecast", "with LSTM v1"], { fill: C.pale2, size: 14.5 });
  s.polyline([[350, 1260], [350, 1315], [500, 1315], [500, 1345]], { arrow: true });
  s.polyline([[620, 1260], [620, 1315], [500, 1315]], { arrow: false });
  s.polyline([[970, 1155], [970, 1315], [820, 1315], [820, 1345]], { arrow: true });
  s.rect(270, 1345, 780, 12, { fill: C.ink, stroke: C.ink, rx: 0, sw: 0 });
  s.line(cx, 1357, cx, 1400, { arrow: true });
  s.node(455, 1400, 410, 75, "Apply rule-based recommendation engine to forecast, budgets and alerts", { fill: C.pale, maxChars: 36 });
  s.line(cx, 1475, cx, 1515, { arrow: true });
  s.node(465, 1515, 390, 66, "Store analysis run and all results");
  s.line(cx, 1581, cx, 1620, { arrow: true });
  s.node(465, 1620, 390, 62, "Return and display forecast, alerts and recommendations");
  s.end(cx, 1700);
  return s.finish();
}

function sequenceDiagram() {
  const s = new Svg(1940, 1400, "Spendly Personal Finance Management System", "GENERATE SPENDING INSIGHTS - SEQUENCE DIAGRAM");
  const actors = [
    [90, "User"], [280, "Flutter mobile app"], [530, "Flask REST API"], [760, "JWT and user scope"],
    [1010, "Feature preparation"], [1260, "Model registry / artifact loader"], [1510, "Rule engine"], [1810, "Database"],
  ];
  s.actor(90, 205, "User");
  for (const [x, label] of actors.slice(1)) s.node(x - 85, 125, 170, 58, wrapWords(label, 20), { size: 13.5, fill: C.pale });
  for (const [x] of actors) s.line(x, x === 90 ? 285 : 183, x, 1345, { dash: "7 6", width: 1.2 });
  s.rect(270, 200, 20, 1150, { fill: C.pale2, stroke: C.mid, rx: 1, sw: 1 });
  s.rect(520, 295, 20, 995, { fill: C.pale2, stroke: C.mid, rx: 1, sw: 1 });
  s.rect(750, 355, 20, 250, { fill: C.pale2, stroke: C.mid, rx: 1, sw: 1 });
  s.rect(1000, 742, 20, 70, { fill: C.pale2, stroke: C.mid, rx: 1, sw: 1 });
  s.rect(1250, 880, 20, 210, { fill: C.pale2, stroke: C.mid, rx: 1, sw: 1 });
  s.rect(1500, 1105, 20, 65, { fill: C.pale2, stroke: C.mid, rx: 1, sw: 1 });
  s.rect(1800, 635, 20, 615, { fill: C.pale2, stroke: C.mid, rx: 1, sw: 1 });

  const msg = (from, to, y, label, options = {}) => {
    s.line(from, y, to, y, { arrow: true, dash: options.dash ?? "", width: 1.4 });
    const center = (from + to) / 2;
    const lines = wrapWords(label, options.maxChars ?? 43);
    s.lines(center, y - 9 - (lines.length - 1) * 14, lines, { size: options.size ?? 12.5, anchor: "middle", lineHeight: 14, fill: C.ink });
  };
  msg(90, 280, 245, "1. Tap Refresh insights", { maxChars: 28 });
  msg(280, 530, 305, "2. POST /api/v1/analysis/run\nAuthorization: Bearer <JWT>", { maxChars: 46 });
  msg(530, 760, 365, "3. Validate JWT, active account and analysis setting", { maxChars: 40 });
  s.rect(490, 405, 340, 155, { fill: "none", stroke: C.mid, rx: 2, sw: 1.3 });
  s.text(560, 425, "alt  request rejected", { size: 12, weight: 700 });
  msg(760, 530, 465, "4a. Rejection details", { dash: "6 5", maxChars: 30 });
  msg(530, 280, 520, "4b. Error envelope (401 / 422 / 503)", { dash: "6 5", maxChars: 37 });
  s.text(560, 552, "else  request accepted", { size: 12, weight: 700 });
  msg(760, 530, 590, "4c. Authenticated user", { dash: "6 5", maxChars: 30 });
  msg(530, 1810, 645, "5. Read user transactions and active budgets", { maxChars: 55 });
  msg(1810, 530, 695, "6. Return user-owned records", { dash: "6 5", maxChars: 38 });
  msg(530, 1010, 750, "7. Prepare weekly and transaction features", { maxChars: 45 });
  msg(1010, 530, 800, "8. Return history count and model inputs", { dash: "6 5", maxChars: 45 });

  s.rect(490, 830, 860, 155, { fill: "none", stroke: C.mid, rx: 2, sw: 1.3 });
  s.text(560, 850, "alt  eight or more complete weeks", { size: 12, weight: 700 });
  msg(530, 1260, 890, "9a. Run LSTM v1 forecast", { maxChars: 35 });
  msg(1260, 530, 925, "9b. Return next-week estimate", { dash: "6 5", maxChars: 35 });
  s.line(490, 945, 1350, 945, { dash: "6 5", width: 1.1 });
  s.text(560, 965, "else  fewer than eight complete weeks", { size: 12, weight: 700 });
  s.text(700, 975, "9c. Use personal weekly-average fallback", { size: 12.5, anchor: "middle" });
  msg(530, 1260, 1025, "10. Score expense features with Isolation Forest v1", { maxChars: 52 });
  msg(1260, 530, 1070, "11. Return alerts, scores and explanations", { dash: "6 5", maxChars: 48 });
  msg(530, 1510, 1115, "12. Evaluate transparent recommendation rules", { maxChars: 47 });
  msg(1510, 530, 1155, "13. Return recommendations and reasons", { dash: "6 5", maxChars: 44 });
  msg(530, 1810, 1190, "14. Store AnalysisRun, Forecast, Alerts and Recommendations", { maxChars: 63 });
  msg(1810, 530, 1240, "15. Confirm database commit", { dash: "6 5", maxChars: 38 });
  msg(530, 280, 1290, "16. HTTP 200 success envelope", { dash: "6 5", maxChars: 38 });
  msg(280, 90, 1340, "17. Display forecast, alerts and recommendations", { dash: "6 5", maxChars: 44 });
  return s.finish();
}

function classBox(s, x, y, width, title, stereotype, attributes, operations = []) {
  const headerH = stereotype ? 58 : 38;
  const attrH = Math.max(34, attributes.length * 19 + 18);
  const opH = operations.length ? operations.length * 19 + 18 : 0;
  const height = headerH + attrH + opH;
  s.rect(x, y, width, height, { fill: C.white, stroke: C.ink, rx: 2, sw: 1.8 });
  s.rect(x, y, width, headerH, { fill: C.pale2, stroke: C.ink, rx: 2, sw: 1.8 });
  if (stereotype) {
    s.text(x + width / 2, y + 19, stereotype, { size: 11.5, italic: true, anchor: "middle", fill: C.mid });
    s.text(x + width / 2, y + 43, title, { size: 16, weight: 700, anchor: "middle" });
  } else {
    s.text(x + width / 2, y + 25, title, { size: 16, weight: 700, anchor: "middle" });
  }
  s.line(x, y + headerH, x + width, y + headerH, { width: 1.3 });
  s.lines(x + 12, y + headerH + 20, attributes, { size: 12.5, lineHeight: 19 });
  if (operations.length) {
    s.line(x, y + headerH + attrH, x + width, y + headerH + attrH, { width: 1.3 });
    s.lines(x + 12, y + headerH + attrH + 20, operations, { size: 12.5, lineHeight: 19 });
  }
  return { x, y, width, height, left: x, right: x + width, top: y, bottom: y + height, cx: x + width / 2, cy: y + height / 2 };
}

function relationship(s, points, leftCardinality, rightCardinality, label = "", options = {}) {
  s.polyline(points, { arrow: options.arrow ?? false, dash: options.dash ?? "", width: options.width ?? 1.4, color: options.color ?? C.line });
  const start = points[0];
  const end = points.at(-1);
  if (leftCardinality) s.label(start[0] + (options.startDx ?? 12), start[1] + (options.startDy ?? -8), leftCardinality, { size: 10.5 });
  if (rightCardinality) s.label(end[0] + (options.endDx ?? -12), end[1] + (options.endDy ?? -8), rightCardinality, { size: 10.5 });
  if (label) {
    const mid = points[Math.floor(points.length / 2)];
    s.label(mid[0] + (options.labelDx ?? 0), mid[1] + (options.labelDy ?? -8), label, { size: 11 });
  }
}

function classDiagram() {
  const s = new Svg(2080, 1540, "Spendly Personal Finance Management System", "IMPLEMENTATION-ALIGNED UML CLASS DIAGRAM");
  s.text(65, 130, "Domain entities", { size: 15, weight: 700 });
  s.line(65, 140, 2015, 140, { color: C.mid, width: 1 });

  const user = classBox(s, 70, 170, 430, "User", "<<entity>>", [
    "- id: UUID", "- email: String", "- passwordHash: String [0..1]", "- googleSubject: String [0..1]",
    "- displayName: String", "- username: String", "- monthlyIncome: Decimal [0..1]", "- requiredConsents: DateTime [0..1]",
    "- modelTrainingOptIn: Boolean", "- onboardingCompletedAt: DateTime [0..1]", "- isActive: Boolean", "- authVersion: Integer",
  ], ["+ authenticate(): Boolean", "+ updateProfile(): void"]);
  const run = classBox(s, 650, 170, 410, "AnalysisRun", "<<entity>>", [
    "- id: UUID", "- userId: UUID", "- status: String", "- forecastModelVersion: String",
    "- anomalyModelVersion: String", "- historyWeeks: Integer", "- generatedAt: DateTime",
  ]);
  const analysis = classBox(s, 1160, 170, 380, "AnalysisService", "<<control>>", [
    "- registry: ModelRegistry", "- featurePreparation: FeaturePreparation", "- recommendations: RecommendationEngine",
  ], ["+ run(user): AnalysisResult", "+ latest(run): AnalysisResult"]);
  const registry = classBox(s, 1610, 170, 400, "ModelRegistry", "<<service>>", [
    "- lstmModel: LSTM v1", "- anomalyModel: Isolation Forest v1", "- loaded: Boolean",
  ], ["+ load(): void", "+ forecast(sequence): Decimal", "+ detectUnusual(features): Alert[]"]);

  const transaction = classBox(s, 70, 690, 430, "Transaction", "<<entity>>", [
    "- id: UUID", "- userId: UUID", "- timestamp: DateTime", "- amount: Decimal", "- currency: String = KES",
    "- category: String", "- transactionType: String", "- merchant: String [0..1]", "- isRecurring: Boolean",
    "- source: String", "- fingerprint: String",
  ], ["+ validate(): Boolean"]);
  const forecast = classBox(s, 570, 690, 380, "Forecast", "<<entity>>", [
    "- id: UUID", "- analysisRunId: UUID", "- userId: UUID", "- periodStart: Date", "- periodEnd: Date",
    "- predictedSpending: Decimal", "- baselinePrediction: Decimal [0..1]", "- modelVersion: String",
  ]);
  const alert = classBox(s, 1010, 690, 420, "AnomalyAlert", "<<entity>>", [
    "- id: UUID", "- analysisRunId: UUID", "- userId: UUID", "- transactionId: UUID [0..1]", "- isUnusualSpending: Boolean",
    "- anomalyScore: Float", "- decisionThreshold: Float", "- explanation: String", "- reviewStatus: String",
    "- reviewedAt: DateTime [0..1]", "- modelVersion: String",
  ], ["+ markReviewed(): void"]);
  const recommendation = classBox(s, 1490, 690, 500, "Recommendation", "<<entity>>", [
    "- id: UUID", "- analysisRunId: UUID", "- userId: UUID", "- recommendationCode: String", "- title: String",
    "- message: String", "- severity: String", "- reason: String", "- supportingValues: JSON",
    "- suggestedAction: String", "- disclaimer: String",
  ]);

  const budget = classBox(s, 70, 1160, 430, "Budget", "<<entity>>", [
    "- id: UUID", "- userId: UUID", "- periodStart: Date", "- periodEnd: Date", "- category: String", "- amount: Decimal", "- currency: String = KES",
  ], ["+ isExceeded(spent): Boolean"]);
  const modelVersion = classBox(s, 570, 1160, 380, "ModelVersion", "<<entity>>", [
    "- id: UUID", "- component: String", "- version: String", "- artifactPath: String", "- metadata: JSON", "- isActive: Boolean",
  ]);
  const audit = classBox(s, 1010, 1170, 420, "AdminAudit", "<<entity>>", [
    "- id: UUID", "- actor: String", "- action: String", "- targetType: String", "- targetId: String", "- reason: String", "- details: JSON", "- createdAt: DateTime",
  ]);
  const setting = classBox(s, 1490, 1170, 500, "SystemSetting", "<<entity>>", [
    "- key: String", "- enabled: Boolean",
  ]);
  const rules = classBox(s, 1160, 500, 380, "RecommendationEngine", "<<service>>", [
    "- rules: Rule[]",
  ], ["+ evaluate(context): Recommendation[]"]);

  relationship(s, [[user.right, 285], [575, 285], [575, 265], [run.left, 265]], "1", "0..*", "owns");
  relationship(s, [[user.cx, user.bottom], [user.cx, 650], [transaction.cx, 650], [transaction.cx, transaction.top]], "1", "0..*", "records");
  relationship(s, [[user.left + 80, user.bottom], [35, user.bottom], [35, 1110], [budget.cx, 1110], [budget.cx, budget.top]], "1", "0..*", "defines", { labelDx: 45 });
  relationship(s, [[run.cx, run.bottom], [run.cx, 650], [forecast.cx, 650], [forecast.cx, forecast.top]], "1", "1", "produces");
  relationship(s, [[run.right - 30, run.bottom], [run.right - 30, 650], [alert.cx, 650], [alert.cx, alert.top]], "1", "0..*", "produces", { labelDx: 45 });
  relationship(s, [[run.right, run.bottom - 5], [1580, run.bottom - 5], [1580, 650], [recommendation.cx, 650], [recommendation.cx, recommendation.top]], "1", "0..*", "produces", { labelDx: 20 });
  relationship(s, [[transaction.right, transaction.bottom - 30], [530, transaction.bottom - 30], [530, 1040], [980, 1040], [980, 950], [alert.left, 950]], "0..1", "0..*", "may explain", { labelDx: 15 });
  relationship(s, [[analysis.left, 285], [run.right, 285]], "", "", "creates", { arrow: true, dash: "7 5" });
  relationship(s, [[analysis.right, 260], [registry.left, 260]], "", "", "uses", { arrow: true, dash: "7 5" });
  relationship(s, [[analysis.cx, analysis.bottom], [analysis.cx, rules.top]], "", "", "uses", { arrow: true, dash: "7 5" });
  relationship(s, [[registry.right, registry.bottom - 25], [2040, registry.bottom - 25], [2040, 1125], [modelVersion.right, 1125], [modelVersion.right, modelVersion.top]], "", "", "loads", { arrow: true, dash: "7 5", labelDx: -40 });
  relationship(s, [[setting.right, setting.cy], [2035, setting.cy], [2035, 410], [analysis.right - 10, 410], [analysis.right - 10, analysis.bottom]], "", "", "controls analysis availability", { arrow: true, dash: "7 5", labelDx: -80 });
  s.rect(1510, 1380, 480, 105, { fill: C.pale, stroke: C.mid, rx: 5, sw: 1.2 });
  s.lines(1530, 1405, ["Administrator identity is server configuration,", "not a User role or database Role class.", "Audit records retain the configured actor name."], { size: 13, lineHeight: 21 });
  s.text(70, 1505, "Constraint: every User must have passwordHash or googleSubject. Category values are stored as text; no Category class/table is used.", { size: 13, fill: C.mid });
  return s.finish();
}

function entityBox(s, x, y, width, height, title, subtitle = "") {
  s.rect(x, y, width, height, { fill: C.white, stroke: C.ink, rx: 4, sw: 1.8 });
  s.rect(x, y, width, 34, { fill: C.pale2, stroke: C.ink, rx: 4, sw: 1.8 });
  s.text(x + width / 2, y + 23, title, { size: 15, weight: 700, anchor: "middle" });
  if (subtitle) s.lines(x + width / 2, y + 56, wrapWords(subtitle, 34), { size: 12, anchor: "middle", fill: C.mid, lineHeight: 16 });
  return { x, y, width, height, left: x, right: x + width, top: y, bottom: y + height, cx: x + width / 2, cy: y + height / 2 };
}

function erdDiagram() {
  const s = new Svg(1840, 1120, "Spendly Personal Finance Management System", "CONCEPTUAL ENTITY-RELATIONSHIP DIAGRAM");
  const user = entityBox(s, 90, 190, 270, 88, "USER", "owns personal and financial data");
  const tx = entityBox(s, 90, 420, 270, 88, "TRANSACTION", "income or expense record");
  const budget = entityBox(s, 90, 680, 270, 88, "BUDGET", "total or category limit");
  const run = entityBox(s, 700, 300, 280, 88, "ANALYSIS RUN", "one stored insight generation event");
  const forecast = entityBox(s, 1280, 170, 280, 88, "FORECAST", "next-week spending estimate");
  const alert = entityBox(s, 1280, 390, 280, 88, "ANOMALY ALERT", "unusual-spending review prompt");
  const rec = entityBox(s, 1280, 610, 280, 88, "RECOMMENDATION", "rule-based planning guidance");
  const model = entityBox(s, 700, 780, 280, 88, "MODEL VERSION", "registered frozen artefact metadata");
  const setting = entityBox(s, 90, 900, 270, 88, "SYSTEM SETTING", "analysis enablement control");
  const audit = entityBox(s, 1280, 865, 280, 88, "ADMIN AUDIT", "append-only accountability event");
  const attempt = entityBox(s, 1620, 865, 180, 88, "LOGIN ATTEMPT", "admin throttle record");
  const admin = entityBox(s, 700, 945, 280, 88, "CONFIGURED ADMINISTRATOR", "identity held outside the database");

  relationship(s, [[user.cx, user.bottom], [user.cx, tx.top]], "1", "0..*", "records", { startDx: -25, endDx: 28, labelDx: 45 });
  relationship(s, [[user.right, 240], [520, 240], [520, 340], [run.left, 340]], "1", "0..*", "requests", { labelDy: -10 });
  relationship(s, [[user.left + 70, user.bottom], [55, user.bottom], [55, budget.cy], [budget.left, budget.cy]], "1", "0..*", "defines", { startDx: 25, endDx: -30, endDy: 22, labelDx: 5, labelDy: -70 });
  relationship(s, [[run.right, 330], [1120, 330], [1120, forecast.cy], [forecast.left, forecast.cy]], "1", "1", "produces");
  relationship(s, [[run.right, 344], [1160, 344], [1160, alert.cy], [alert.left, alert.cy]], "1", "0..*", "produces");
  relationship(s, [[run.right, 358], [1200, 358], [1200, rec.cy], [rec.left, rec.cy]], "1", "0..*", "produces");
  relationship(s, [[tx.right, tx.cy], [1120, tx.cy], [1120, alert.cy], [alert.left, alert.cy]], "1", "0..*", "may be referenced by", { endDx: -15, labelDx: -30, labelDy: 16 });
  relationship(s, [[model.cx, model.top], [model.cx, 700], [850, 700], [850, run.bottom]], "", "", "version metadata", { dash: "7 5", arrow: true, labelDx: 18 });
  relationship(s, [[setting.right, setting.cy], [610, setting.cy], [610, run.bottom]], "1", "0..*", "allows or pauses", { dash: "7 5", arrow: true });
  relationship(s, [[admin.right, admin.cy], [1120, admin.cy], [1120, audit.cy], [audit.left, audit.cy]], "1", "0..*", "creates");
  relationship(s, [[admin.right, admin.cy + 18], [1575, admin.cy + 18], [1575, attempt.cy], [attempt.left, attempt.cy]], "1", "0..*", "is subject to");
  s.rect(430, 1045, 980, 48, { fill: C.pale, stroke: C.mid, rx: 4, sw: 1 });
  s.text(920, 1075, "No ROLES or CATEGORIES entity: mobile users have one user boundary, category is text, and administrator identity is server configuration.", { size: 13, anchor: "middle" });
  return s.finish();
}

function tableBox(s, x, y, width, title, fields, options = {}) {
  const rowH = options.rowH ?? 20;
  const headerH = 36;
  const height = headerH + fields.length * rowH + 14;
  s.rect(x, y, width, height, { fill: C.white, stroke: C.ink, rx: 2, sw: 1.7 });
  s.rect(x, y, width, headerH, { fill: C.pale2, stroke: C.ink, rx: 2, sw: 1.7 });
  s.text(x + width / 2, y + 24, title, { size: 14.5, weight: 700, anchor: "middle" });
  fields.forEach((field, index) => {
    const yText = y + headerH + 18 + index * rowH;
    const match = field.match(/^(PK|FK|UK|CK)\s+(.*)$/);
    if (match) {
      s.text(x + 10, yText, match[1], { size: 10.5, weight: 700, fill: C.mid });
      s.text(x + 44, yText, match[2], { size: 12.1 });
    } else {
      s.text(x + 44, yText, field, { size: 12.1 });
    }
  });
  return { x, y, width, height, left: x, right: x + width, top: y, bottom: y + height, cx: x + width / 2, cy: y + height / 2 };
}

function databaseSchema() {
  const s = new Svg(2320, 1620, "Spendly Personal Finance Management System", "LOGICAL DATABASE SCHEMA");
  s.text(70, 128, "Core user-owned data", { size: 15, weight: 700 });
  s.text(760, 128, "Analysis lifecycle", { size: 15, weight: 700 });
  s.text(1740, 128, "Stored analytical outputs", { size: 15, weight: 700 });

  const users = tableBox(s, 70, 155, 440, "USERS", [
    "PK id", "UK email", "password_hash [nullable]", "UK google_subject [nullable]", "CK password_hash OR google_subject", "display_name", "username", "UK username_normalized",
    "monthly_income [nullable]", "terms_accepted_at [nullable]", "privacy_accepted_at [nullable]", "consent_version [nullable]",
    "model_training_opt_in", "model_training_consented_at [nullable]", "onboarding_completed_at [nullable]", "is_active", "auth_version", "created_at",
  ]);
  const tx = tableBox(s, 70, 600, 440, "TRANSACTIONS", [
    "PK id", "FK user_id -> USERS.id", "transaction_timestamp", "amount", "currency = KES", "category (text)", "transaction_type",
    "merchant [nullable]", "is_recurring", "source", "fingerprint", "created_at", "UK (user_id, fingerprint)",
  ]);
  const budgets = tableBox(s, 70, 1010, 440, "BUDGETS", [
    "PK id", "FK user_id -> USERS.id", "period_start", "period_end", "category (text; 'total' or label)", "amount", "currency = KES",
    "created_at", "updated_at", "UK (user_id, period_start, period_end, category)",
  ]);
  const runs = tableBox(s, 745, 225, 430, "ANALYSIS_RUNS", [
    "PK id", "FK user_id -> USERS.id", "status", "forecast_model_version", "anomaly_model_version", "history_periods", "generated_at",
  ]);
  const versions = tableBox(s, 745, 570, 430, "MODEL_VERSIONS", [
    "PK id", "component", "version", "artifact_path", "metadata_json", "is_active", "created_at", "UK (component, version)",
  ]);
  const forecasts = tableBox(s, 1370, 155, 420, "FORECASTS", [
    "PK id", "FK analysis_run_id -> ANALYSIS_RUNS.id", "FK user_id -> USERS.id", "period_start", "period_end", "predicted_spending",
    "baseline_prediction [nullable]", "currency = KES", "model_version", "created_at", "UK analysis_run_id",
  ]);
  const alerts = tableBox(s, 1370, 555, 420, "ANOMALY_ALERTS", [
    "PK id", "FK analysis_run_id -> ANALYSIS_RUNS.id", "FK user_id -> USERS.id", "FK transaction_id -> TRANSACTIONS.id [nullable]",
    "is_unusual_spending", "anomaly_score", "decision_threshold", "explanation", "review_status", "reviewed_at [nullable]", "model_version", "created_at",
  ]);
  const recommendations = tableBox(s, 1860, 555, 410, "RECOMMENDATIONS", [
    "PK id", "FK analysis_run_id -> ANALYSIS_RUNS.id", "FK user_id -> USERS.id", "recommendation_code", "title", "message", "severity", "reason",
    "supporting_values", "suggested_action", "disclaimer", "created_at",
  ]);
  const audit = tableBox(s, 650, 1030, 430, "ADMIN_AUDIT", [
    "PK id", "actor (configured administrator name)", "action", "target_type", "target_id", "reason", "details", "created_at",
  ]);
  const attempts = tableBox(s, 1130, 1085, 390, "ADMIN_LOGIN_ATTEMPTS", [
    "PK id", "client_key", "created_at",
  ]);
  const settings = tableBox(s, 1570, 1085, 350, "SYSTEM_SETTINGS", [
    "PK key", "enabled",
  ]);

  relationship(s, [[users.right, 320], [620, 320], [620, 285], [runs.left, 285]], "1", "0..*", "owns");
  relationship(s, [[users.cx, users.bottom], [users.cx, tx.top]], "1", "0..*", "owns");
  relationship(s, [[users.left + 80, users.bottom], [40, users.bottom], [40, budgets.cy], [budgets.left, budgets.cy]], "1", "0..*", "owns", { labelDx: 45 });
  relationship(s, [[runs.right, 290], [1260, 290], [1260, forecasts.cy], [forecasts.left, forecasts.cy]], "1", "1", "produces");
  relationship(s, [[runs.right, 310], [1300, 310], [1300, alerts.cy], [alerts.left, alerts.cy]], "1", "0..*", "produces");
  relationship(s, [[runs.right, 350], [1210, 350], [1210, 500], [1820, 500], [1820, recommendations.cy], [recommendations.left, recommendations.cy]], "1", "0..*", "produces");
  relationship(s, [[tx.right, 760], [600, 760], [600, 850], [1290, 850], [1290, alerts.cy], [alerts.left, alerts.cy]], "1", "0..*", "optional transaction", { labelDx: 24, labelDy: 14 });
  relationship(s, [[versions.right, versions.cy], [1240, versions.cy], [1240, 430], [runs.right, 430]], "1..*", "0..*", "version labels", { dash: "7 5", arrow: true });
  relationship(s, [[settings.cx, settings.top], [settings.cx, 970], [runs.cx, 970], [runs.cx, runs.bottom]], "1", "0..*", "analysis_enabled gates new runs", { dash: "7 5", arrow: true, labelDx: -110 });
  s.rect(1970, 1090, 300, 260, { fill: C.pale, stroke: C.mid, rx: 4, sw: 1.2 });
  s.text(2120, 1120, "INTEGRITY NOTES", { size: 13.5, weight: 700, anchor: "middle" });
  s.lines(1990, 1150, [
    "- Authentication requires at least one:", "  password_hash OR google_subject.", "- Administrator credentials are held in", "  server configuration, not USERS/ROLES.",
    "- Category is stored as text; there is", "  no CATEGORIES table.", "- Alert review fields support the", "  Mark as reviewed UI action.",
  ], { size: 12.5, lineHeight: 23 });
  s.rect(650, 1410, 1620, 120, { fill: C.white, stroke: C.mid, rx: 4, sw: 1.1 });
  s.text(670, 1438, "Legend", { size: 13, weight: 700 });
  s.lines(670, 1465, [
    "PK = primary key   FK = foreign key   UK = unique constraint   [nullable] = optional value",
    "Cardinality is shown on relationship lines. Physical DBMS types and indexes are intentionally omitted from this logical schema.",
    "Operational tables are included; ADMIN_AUDIT has no target foreign key so accountability survives account deletion.",
  ], { size: 12.5, lineHeight: 22 });
  return s.finish();
}

function architectureDiagram() {
  const s = new Svg(1940, 1160, "Spendly Personal Finance Management System", "SYSTEM ARCHITECTURE");
  s.rect(45, 125, 1850, 950, { fill: C.white, stroke: C.ink, rx: 5, sw: 2 });
  s.text(70, 155, "Target deployment: Flutter Android client + Render-hosted Flask service + Neon PostgreSQL", { size: 13.5, weight: 700 });

  s.actor(105, 350, "App user");
  s.actor(105, 790, "Administrator");

  s.text(360, 205, "PRESENTATION", { size: 14, weight: 700, anchor: "middle", fill: C.mid });
  s.node(220, 255, 280, 170, ["Flutter Android application", "", "Dashboard and analytics", "Transactions and CSV import", "Budgets and stored insights", "Password or Google sign-in"], { fill: C.pale, size: 13.5 });
  s.node(220, 690, 280, 165, ["Browser admin console", "", "Account and record management", "Audit and model information", "System controls"], { fill: C.pale, size: 13.5 });

  s.text(775, 205, "APPLICATION AND API", { size: 14, weight: 700, anchor: "middle", fill: C.mid });
  s.node(610, 255, 330, 235, ["Flask REST API (/api/v1)", "", "JWT authentication and ownership", "Request schema validation", "Dashboard and history routes", "Analysis orchestration", "SQLAlchemy repositories"], { fill: C.white, size: 13.5 });
  s.node(610, 690, 330, 165, ["Administrator routes", "", "Session + CSRF + reauthentication", "Read/write action controls", "Append-only audit events"], { fill: C.white, size: 13.5 });

  s.text(1270, 205, "ANALYTICAL SERVICES", { size: 14, weight: 700, anchor: "middle", fill: C.mid });
  s.node(1080, 255, 380, 115, ["Feature preparation", "8 complete weekly periods", "Expense-transaction features"], { fill: C.pale, size: 13.5 });
  s.node(1080, 420, 180, 125, ["LSTM v1", "Next-week forecast", "<8 weeks: weekly average"], { fill: C.pale2, size: 13 });
  s.node(1280, 420, 180, 125, ["Isolation Forest v1", "Unusual-spending", "review prompts"], { fill: C.pale2, size: 13 });
  s.node(1080, 600, 380, 125, ["Rule-based recommendation engine", "Transparent rules use forecast, budgets,", "cash flow and unusual-spending results"], { fill: C.pale, size: 13 });
  s.node(1080, 780, 380, 110, ["Model registry / artefact loader", "Loads frozen v1 artefacts once at startup", "Inference only - no request-time training"], { fill: C.white, size: 13 });

  s.text(1690, 205, "DATA", { size: 14, weight: 700, anchor: "middle", fill: C.mid });
  s.node(1560, 315, 270, 300, ["Neon PostgreSQL", "", "Users", "Transactions and budgets", "Analysis runs", "Forecasts and alerts", "Recommendations", "Model versions", "Audit and system settings"], { fill: C.pale, size: 13.5 });
  s.node(1560, 740, 270, 150, ["Server configuration", "", "Administrator identity", "Secrets and deployment settings", "Loaded by admin routes at startup"], { fill: C.white, size: 13.5, dash: "7 5" });

  s.line(135, 335, 220, 335, { arrow: true });
  s.line(220, 370, 135, 370, { arrow: true });
  s.label(177, 323, "uses", { size: 11 });
  s.line(135, 775, 220, 775, { arrow: true });
  s.line(220, 810, 135, 810, { arrow: true });
  s.label(177, 763, "uses", { size: 11 });
  s.line(500, 320, 610, 320, { arrow: true });
  s.line(610, 365, 500, 365, { arrow: true });
  s.label(555, 307, "HTTPS + JWT / JSON / CSV", { size: 10.5 });
  s.label(555, 390, "success or error envelope", { size: 10.5 });
  s.line(500, 755, 610, 755, { arrow: true });
  s.line(610, 800, 500, 800, { arrow: true });
  s.label(555, 742, "HTTPS + session / CSRF", { size: 10.5 });
  s.label(555, 825, "HTML / JSON response", { size: 10.5 });
  s.polyline([[940, 335], [1020, 335], [1020, 312], [1080, 312]], { arrow: true });
  s.polyline([[1080, 350], [1020, 350], [1020, 390], [940, 390]], { arrow: true });
  s.label(1010, 292, "records", { size: 10.5 });
  s.label(1010, 415, "features/results", { size: 10.5 });
  s.line(1270, 370, 1170, 420, { arrow: true });
  s.line(1270, 370, 1370, 420, { arrow: true });
  s.polyline([[1170, 545], [1170, 575], [1270, 575], [1270, 600]], { arrow: true });
  s.polyline([[1370, 545], [1370, 575], [1270, 575]], { arrow: false });
  s.polyline([[1080, 835], [1040, 835], [1040, 570], [1170, 570], [1170, 545]], { arrow: true, dash: "7 5" });
  s.polyline([[1040, 570], [1370, 570], [1370, 545]], { arrow: true, dash: "7 5" });
  s.label(1053, 590, "loads", { size: 10.5 });
  s.line(1460, 460, 1560, 460, { arrow: true });
  s.line(1560, 510, 1460, 510, { arrow: true });
  s.label(1510, 447, "store", { size: 10.5 });
  s.label(1510, 535, "read", { size: 10.5 });
  s.line(940, 790, 1080, 835, { arrow: true, dash: "7 5" });
  s.polyline([[940, 745], [1000, 745], [1000, 920], [1510, 920], [1510, 550], [1560, 550]], { arrow: true });
  s.polyline([[1560, 585], [1535, 585], [1535, 940], [980, 940], [980, 805], [940, 805]], { arrow: true });
  s.label(1470, 908, "write", { size: 10.5 });
  s.label(1490, 952, "read", { size: 10.5 });
  s.rect(220, 955, 1610, 78, { fill: C.pale, stroke: C.mid, rx: 4, sw: 1.1 });
  s.lines(240, 982, ["Arrow direction is explicit: client requests flow to Flask; success/error responses return to clients; services read/write PostgreSQL.", "Isolation Forest alerts are review prompts, not fraud findings. Recommendations are guidance, not automated financial decisions."], { size: 13, lineHeight: 23 });
  return s.finish();
}

function uiText(s, x, y, value, options = {}) {
  s.text(x, y, value, { size: options.size ?? 13, weight: options.weight ?? 400, fill: options.fill ?? C.ink, anchor: options.anchor ?? "start" });
}

function uiCard(s, x, y, width, height, options = {}) {
  s.rect(x, y, width, height, { fill: options.fill ?? C.white, stroke: options.stroke ?? C.mid, rx: options.rx ?? 10, sw: options.sw ?? 1.2, dash: options.dash ?? "" });
}

function uiButton(s, x, y, width, label, options = {}) {
  const height = options.height ?? 42;
  const filled = options.filled ?? false;
  s.rect(x, y, width, height, { fill: filled ? C.dark : C.white, stroke: C.dark, rx: 7, sw: 1.3 });
  uiText(s, x + width / 2, y + height / 2 + 5, label, { size: options.size ?? 13, weight: 700, anchor: "middle", fill: filled ? C.white : C.ink });
}

function uiField(s, x, y, width, label, value, options = {}) {
  uiText(s, x, y, label, { size: 12, weight: 700, fill: C.dark });
  s.rect(x, y + 9, width, options.height ?? 48, { fill: C.white, stroke: options.error ? C.ink : C.mid, rx: 6, sw: options.error ? 2.2 : 1.1, dash: options.error ? "6 4" : "" });
  uiText(s, x + 13, y + 39, value, { size: 13, fill: options.muted ? C.mid : C.ink });
  if (options.trailing) uiText(s, x + width - 18, y + 39, options.trailing, { size: 13, anchor: "middle", fill: C.mid });
}

function phoneShell(s, screenTitle, activeNav) {
  const x = 145;
  const y = 120;
  const width = 610;
  const height = 1480;
  s.rect(x, y, width, height, { fill: C.white, stroke: C.ink, rx: 22, sw: 2.4 });
  s.rect(x + 245, y + 13, 120, 9, { fill: C.ink, stroke: C.ink, rx: 5, sw: 0 });
  s.circle(x + 42, y + 68, 21, { fill: C.dark, stroke: C.dark, sw: 1 });
  uiText(s, x + 42, y + 74, "S", { size: 16, weight: 700, anchor: "middle", fill: C.white });
  uiText(s, x + 76, y + 65, "SPENDLY", { size: 17, weight: 700 });
  uiText(s, x + 76, y + 83, "Personal Finance Management", { size: 10.5, fill: C.mid });
  s.line(x, y + 100, x + width, y + 100, { color: C.pale2, width: 1.3 });
  uiText(s, x + 28, y + 143, screenTitle, { size: 22, weight: 700 });
  s.line(x + 28, y + 160, x + width - 28, y + 160, { color: C.pale2, width: 1.2 });
  const navY = y + height - 82;
  s.rect(x, navY, width, 82, { fill: C.pale, stroke: C.pale2, rx: 0, sw: 1 });
  const nav = ["Dashboard", "Transactions", "Budgets", "Analytics", "More"];
  nav.forEach((label, index) => {
    const nx = x + 61 + index * 122;
    const active = label === activeNav;
    s.circle(nx, navY + 24, 9, { fill: active ? C.dark : C.white, stroke: C.dark, sw: 1.2 });
    uiText(s, nx, navY + 57, label, { size: 10.5, weight: active ? 700 : 400, anchor: "middle", fill: active ? C.ink : C.mid });
  });
  return { x, y, width, height, left: x + 28, right: x + width - 28, contentTop: y + 185, navY };
}

function dashboardWireframe() {
  const s = new Svg(900, 1700, "Spendly Personal Finance Management System", "DASHBOARD WIREFRAME");
  const p = phoneShell(s, "Dashboard", "Dashboard");
  const x = p.left;
  const w = p.right - p.left;
  let y = p.contentTop;
  uiText(s, x, y, "Hello, eva", { size: 19, weight: 700 });
  uiText(s, x, y + 23, "Your spending picture at a glance", { size: 12.5, fill: C.mid });
  y += 55;
  uiField(s, x, y, w, "Dashboard period", "Weekly", { trailing: "v" });
  uiText(s, x, y + 76, "Options: Weekly  |  Monthly  |  Last 3 months  |  Yearly  |  Lifetime", { size: 10.5, fill: C.mid });
  y += 100;
  uiText(s, x, y, "8 Sep - 14 Sep 2026", { size: 11.5, fill: C.mid });
  y += 18;
  const gap = 10;
  const cardW = (w - gap * 2) / 3;
  [["Expenses", "KES 12,450"], ["Income", "KES 30,000"], ["Net cash flow", "KES 17,550"]].forEach(([label, value], index) => {
    const cx = x + index * (cardW + gap);
    uiCard(s, cx, y, cardW, 92, { fill: index === 2 ? C.pale : C.white });
    uiText(s, cx + 12, y + 27, label, { size: 11.5, fill: C.mid });
    uiText(s, cx + 12, y + 61, value, { size: 15, weight: 700 });
  });
  y += 118;
  uiText(s, x, y, "Your latest insights", { size: 17, weight: 700 });
  uiButton(s, p.right - 142, y - 25, 142, "Refresh insights", { height: 34, filled: true, size: 11.5 });
  y += 22;
  const insightCards = [
    ["NEXT 7 DAYS", "KES 8,400", "History available: 8 of 8 weeks", "View forecast >"],
    ["SPENDING CHECK", "2 items to review", "Unusual does not mean fraud", "Review alerts >"],
    ["RECOMMENDATION", "Review transport spending", "Rule-based planning guidance", "View recommendation >"],
  ];
  insightCards.forEach(([eyebrow, value, detail, action], index) => {
    uiCard(s, x, y, w, 132, { fill: index === 0 ? C.pale : C.white });
    uiText(s, x + 16, y + 25, eyebrow, { size: 10.5, weight: 700, fill: C.mid });
    uiText(s, x + 16, y + 56, value, { size: 17, weight: 700 });
    uiText(s, x + 16, y + 82, detail, { size: 12.5, fill: C.mid });
    uiText(s, x + 16, y + 112, action, { size: 12.5, weight: 700 });
    y += 146;
  });
  uiCard(s, x, y, w, 72, { fill: C.pale });
  uiText(s, x + 14, y + 25, "i", { size: 15, weight: 700 });
  s.lines(x + 38, y + 24, ["Insights support planning and review.", "They are not guarantees or fraud findings."], { size: 11.5, lineHeight: 18, fill: C.mid });
  return s.finish();
}

function addTransactionWireframe() {
  const s = new Svg(900, 1700, "Spendly Personal Finance Management System", "ADD TRANSACTION WIREFRAME");
  const p = phoneShell(s, "Add transaction", "Transactions");
  const x = p.left;
  const w = p.right - p.left;
  let y = p.contentTop;
  uiButton(s, p.right - 150, y - 22, 150, "Import CSV", { height: 36 });
  uiText(s, x, y + 13, "Record one entry", { size: 14, fill: C.mid });
  y += 48;
  uiButton(s, x, y, w / 2 - 5, "Expense", { filled: true });
  uiButton(s, x + w / 2 + 5, y, w / 2 - 5, "Income");
  y += 72;
  uiField(s, x, y, w, "Amount (KES)", "0.00", { error: true });
  uiText(s, x, y + 75, "Enter an amount greater than zero.", { size: 11.5, weight: 700 });
  y += 102;
  uiField(s, x, y, w, "Category", "Select or type a category", { trailing: "v", muted: true });
  uiText(s, x, y + 75, "Stored as category text; suggestions help keep names consistent.", { size: 10.8, fill: C.mid });
  y += 103;
  uiField(s, x, y, w, "Merchant or source (optional)", "e.g. Naivas", { muted: true });
  y += 82;
  uiField(s, x, y, w, "Transaction date", "11 Sep 2026", { trailing: ">" });
  y += 86;
  s.rect(x, y, 19, 19, { fill: C.white, stroke: C.dark, rx: 2, sw: 1.2 });
  uiText(s, x + 30, y + 15, "Recurring transaction", { size: 13 });
  y += 54;
  uiCard(s, x, y, w, 88, { fill: C.pale, dash: "6 4" });
  uiText(s, x + 14, y + 27, "VALIDATION ERROR STATE", { size: 10.5, weight: 700 });
  s.lines(x + 14, y + 51, ["Amount is required. Correct the highlighted field", "before saving; no transaction has been created."], { size: 11.8, lineHeight: 18 });
  y += 112;
  uiButton(s, x, y, 140, "Cancel");
  uiButton(s, x + 152, y, w - 152, "Save transaction", { filled: true });
  y += 70;
  uiCard(s, x, y, w, 132, { fill: C.white });
  uiText(s, x + 14, y + 26, "CSV import path", { size: 13.5, weight: 700 });
  s.lines(x + 14, y + 52, ["Transactions > Import CSV > choose file > validate rows", "> review duplicate/category issues > import valid records.", "The import summary reports created, duplicate and invalid rows."], { size: 11.5, lineHeight: 20, fill: C.mid });
  return s.finish();
}

function forecastWireframe() {
  const s = new Svg(900, 1700, "Spendly Personal Finance Management System", "FORECAST RESULTS WIREFRAME");
  const p = phoneShell(s, "Next 7 days", "Dashboard");
  const x = p.left;
  const w = p.right - p.left;
  let y = p.contentTop;
  uiCard(s, x, y, w, 170, { fill: C.dark, stroke: C.dark });
  uiText(s, x + 18, y + 32, "ESTIMATED SPENDING", { size: 10.5, weight: 700, fill: C.white });
  uiText(s, x + 18, y + 86, "KES 8,400", { size: 31, weight: 700, fill: C.white });
  uiText(s, x + 18, y + 126, "14 Sep - 20 Sep 2026", { size: 13, fill: C.white });
  y += 192;
  uiCard(s, x, y, w, 190, { fill: C.white });
  uiText(s, x + 16, y + 30, "History available", { size: 16, weight: 700 });
  uiText(s, p.right - 16, y + 30, "62%", { size: 16, weight: 700, anchor: "end" });
  s.rect(x + 16, y + 52, w - 32, 12, { fill: C.pale2, stroke: C.pale2, rx: 6, sw: 0 });
  s.rect(x + 16, y + 52, (w - 32) * 0.62, 12, { fill: C.dark, stroke: C.dark, rx: 6, sw: 0 });
  uiText(s, x + 16, y + 91, "5 of 8 complete weeks", { size: 13, weight: 700 });
  s.lines(x + 16, y + 119, ["Fewer than eight weeks are available, so this estimate", "uses your personal weekly-average fallback.", "At eight weeks, Spendly uses the frozen LSTM v1 model."], { size: 12, lineHeight: 20, fill: C.mid });
  y += 212;
  uiCard(s, x, y, w, 112, { fill: C.pale });
  uiText(s, x + 16, y + 31, "Accuracy pending", { size: 14.5, weight: 700 });
  s.lines(x + 16, y + 60, ["Accuracy can be measured after the forecast week ends", "and actual expenses have been recorded."], { size: 12, lineHeight: 20, fill: C.mid });
  y += 132;
  uiCard(s, x, y, w, 138, { fill: C.white });
  uiText(s, x + 16, y + 31, "How to use this", { size: 15, weight: 700 });
  s.lines(x + 16, y + 62, ["Use the amount as a planning guide. Compare it with your", "budget and adjust optional spending where practical."], { size: 12.5, lineHeight: 22 });
  y += 158;
  uiCard(s, x, y, w, 118, { fill: C.pale, stroke: C.dark });
  uiText(s, x + 16, y + 29, "EXPERIMENTAL GUIDANCE", { size: 10.5, weight: 700 });
  s.lines(x + 16, y + 58, ["This estimate is not a guaranteed outcome or financial advice.", "No model learns from this screen or retrains during the request."], { size: 11.8, lineHeight: 21 });
  y += 142;
  uiButton(s, x, y, 150, "Back");
  return s.finish();
}

function spendingCheckWireframe() {
  const s = new Svg(900, 1700, "Spendly Personal Finance Management System", "SPENDING CHECK WIREFRAME");
  const p = phoneShell(s, "Spending check", "Dashboard");
  const x = p.left;
  const w = p.right - p.left;
  let y = p.contentTop;
  uiCard(s, x, y, w, 118, { fill: C.pale });
  uiText(s, x + 16, y + 31, "2 items are worth a look", { size: 17, weight: 700 });
  s.lines(x + 16, y + 61, ["These entries differ from your recent pattern.", "An unusual entry does not mean fraud."], { size: 12.5, lineHeight: 21 });
  y += 140;
  const alerts = [
    ["11 Sep 2026", "KES 4,850", "Transport", "This amount is noticeably different from what you usually record."],
    ["9 Sep 2026", "KES 7,200", "Food", "Spending in this category looks different from your usual mix."],
  ];
  alerts.forEach(([date, amount, category, explanation], index) => {
    uiCard(s, x, y, w, 285, { fill: C.white });
    uiText(s, x + 16, y + 28, `CHECK ${index + 1}`, { size: 10.5, weight: 700, fill: C.mid });
    uiText(s, p.right - 16, y + 28, "Needs review", { size: 11.5, weight: 700, anchor: "end" });
    uiText(s, x + 16, y + 64, amount, { size: 21, weight: 700 });
    uiText(s, x + 16, y + 91, `${date}  |  ${category}`, { size: 12.5, fill: C.mid });
    s.line(x + 16, y + 108, p.right - 16, y + 108, { color: C.pale2, width: 1 });
    s.lines(x + 16, y + 137, wrapWords(explanation, 62), { size: 12.5, lineHeight: 20 });
    s.lines(x + 16, y + 187, ["Compare this item with your receipt or transaction history.", "Marking it reviewed does not change or delete the transaction."], { size: 11.5, lineHeight: 19, fill: C.mid });
    uiButton(s, x + 16, y + 226, w - 32, "Mark as reviewed", { filled: index === 0 });
    y += 307;
  });
  uiText(s, x, y + 5, "Reviewed items remain in analysis history for accountability.", { size: 11.5, fill: C.mid });
  return s.finish();
}

function budgetsWireframe() {
  const s = new Svg(900, 1700, "Spendly Personal Finance Management System", "BUDGETS WIREFRAME");
  const p = phoneShell(s, "Budgets", "Budgets");
  const x = p.left;
  const w = p.right - p.left;
  let y = p.contentTop;
  uiButton(s, x, y, 180, "+ Add budget", { filled: true });
  uiButton(s, p.right - 120, y, 120, "Refresh");
  y += 66;
  uiText(s, x, y, "Current weekly plans", { size: 16, weight: 700 });
  uiText(s, x, y + 22, "8 Sep - 14 Sep 2026", { size: 11.5, fill: C.mid });
  y += 42;
  const plans = [
    ["TOTAL BUDGET", "KES 20,000", "KES 12,450", "KES 7,550", 0.62],
    ["TRANSPORT", "KES 5,000", "KES 4,850", "KES 150", 0.97],
    ["FOOD", "KES 8,000", "KES 5,300", "KES 2,700", 0.66],
  ];
  plans.forEach(([label, limit, spent, remaining, ratio], index) => {
    uiCard(s, x, y, w, 215, { fill: index === 0 ? C.pale : C.white });
    uiText(s, x + 16, y + 27, label, { size: 11, weight: 700, fill: C.mid });
    uiText(s, x + 16, y + 61, `Limit  ${limit}`, { size: 18, weight: 700 });
    s.rect(x + 16, y + 82, w - 32, 11, { fill: C.pale2, stroke: C.pale2, rx: 6, sw: 0 });
    s.rect(x + 16, y + 82, (w - 32) * ratio, 11, { fill: C.dark, stroke: C.dark, rx: 6, sw: 0 });
    uiText(s, x + 16, y + 123, `Spent  ${spent}`, { size: 13 });
    uiText(s, p.right - 16, y + 123, `${Math.round(ratio * 100)}% used`, { size: 13, weight: 700, anchor: "end" });
    uiText(s, x + 16, y + 153, `Remaining  ${remaining}`, { size: 13, weight: 700 });
    uiButton(s, x + 16, y + 170, 100, "Edit", { height: 32, size: 11.5 });
    uiButton(s, x + 126, y + 170, 100, "Delete", { height: 32, size: 11.5 });
    y += 233;
  });
  uiCard(s, x, y, w, 82, { fill: C.pale });
  s.lines(x + 14, y + 27, ["Total budgets use category = 'total'. Category budgets use", "the category label; both are stored in the same BUDGETS table."], { size: 11.5, lineHeight: 20, fill: C.mid });
  return s.finish();
}

function adminDashboardWireframe() {
  const s = new Svg(1900, 1180, "Spendly Personal Finance Management System", "ADMINISTRATOR DASHBOARD WIREFRAME");
  const x = 55, y = 125, w = 1790, h = 980;
  s.rect(x, y, w, h, { fill: C.white, stroke: C.ink, rx: 8, sw: 2 });
  s.rect(x, y, w, 82, { fill: C.pale, stroke: C.pale2, rx: 8, sw: 1 });
  s.circle(x + 38, y + 41, 20, { fill: C.dark, stroke: C.dark, sw: 1 });
  uiText(s, x + 38, y + 47, "S", { size: 15, weight: 700, fill: C.white, anchor: "middle" });
  uiText(s, x + 72, y + 35, "SPENDLY", { size: 18, weight: 700 });
  uiText(s, x + 72, y + 55, "Personal Finance Management System", { size: 11.5, fill: C.mid });
  uiText(s, x + w - 150, y + 45, "Administrator", { size: 12.5, weight: 700, anchor: "end" });
  uiButton(s, x + w - 125, y + 22, 95, "Log out", { height: 36, size: 11.5 });

  const sideW = 280;
  s.rect(x, y + 82, sideW, h - 82, { fill: C.pale, stroke: C.pale2, rx: 0, sw: 1 });
  const nav = ["Overview", "Accounts", "Financial records", "Stored insights", "Audit log", "System controls", "Model information"];
  nav.forEach((label, index) => {
    const ny = y + 125 + index * 60;
    if (index === 0) s.rect(x + 16, ny - 28, sideW - 32, 44, { fill: C.dark, stroke: C.dark, rx: 6, sw: 0 });
    uiText(s, x + 34, ny, label, { size: 13, weight: index === 0 ? 700 : 400, fill: index === 0 ? C.white : C.ink });
  });
  uiCard(s, x + 18, y + 690, sideW - 36, 180, { fill: C.white });
  uiText(s, x + 34, y + 720, "Permission boundary", { size: 12.5, weight: 700 });
  s.lines(x + 34, y + 748, ["View-only:", "stored insights, models, audit", "", "Update/delete:", "accounts and financial records", "with reason + reauthentication"], { size: 11.2, lineHeight: 19, fill: C.mid });

  const mainX = x + sideW + 32;
  const mainW = w - sideW - 62;
  uiText(s, mainX, y + 130, "Administrator dashboard", { size: 24, weight: 700 });
  uiText(s, mainX, y + 157, "Operational overview - no model training or threshold editing", { size: 12.5, fill: C.mid });
  const cards = [["Registered users", "1,248"], ["Transactions", "36,902"], ["Analysis runs", "4,816"], ["Unusual alerts", "327"]];
  const gap = 16;
  const cardW = (mainW - gap * 3) / 4;
  cards.forEach(([label, value], index) => {
    const cx = mainX + index * (cardW + gap);
    uiCard(s, cx, y + 185, cardW, 110, { fill: index === 2 ? C.pale : C.white });
    uiText(s, cx + 15, y + 218, label, { size: 12, fill: C.mid });
    uiText(s, cx + 15, y + 263, value, { size: 24, weight: 700 });
  });

  uiCard(s, mainX, y + 320, mainW * 0.64, 310, { fill: C.white });
  uiText(s, mainX + 16, y + 352, "Recent accounts", { size: 16, weight: 700 });
  uiField(s, mainX + 16, y + 368, mainW * 0.64 - 32, "Search", "Name, email or username", { muted: true, height: 42, trailing: "Q" });
  const tableX = mainX + 16, tableY = y + 452, tableW = mainW * 0.64 - 32;
  s.rect(tableX, tableY, tableW, 38, { fill: C.pale2, stroke: C.pale2, rx: 0, sw: 0 });
  const cols = [0, 0.26, 0.54, 0.75];
  ["User", "Email", "Provider", "Status"].forEach((label, index) => uiText(s, tableX + 12 + tableW * cols[index], tableY + 25, label, { size: 11.5, weight: 700 }));
  const rows = [["Amina K.", "amina@example.com", "Google", "Active"], ["Brian O.", "brian@example.com", "Password", "Disabled"], ["Carole W.", "carole@example.com", "Password", "Active"]];
  rows.forEach((row, ri) => {
    const ry = tableY + 67 + ri * 47;
    s.line(tableX, ry + 11, tableX + tableW, ry + 11, { color: C.pale2, width: 1 });
    row.forEach((value, ci) => uiText(s, tableX + 12 + tableW * cols[ci], ry - 4, value, { size: 11.5, weight: ci === 0 ? 700 : 400 }));
  });

  const sideX = mainX + mainW * 0.66;
  const sidePanelW = mainW * 0.34;
  uiCard(s, sideX, y + 320, sidePanelW, 310, { fill: C.pale });
  uiText(s, sideX + 16, y + 352, "Account actions", { size: 16, weight: 700 });
  ["Inspect account", "Edit profile / access", "Manage transactions / budgets", "Export account data", "Delete disabled account"].forEach((label, index) => uiButton(s, sideX + 16, y + 370 + index * 48, sidePanelW - 32, label, { height: 36, size: 11.3, filled: index === 0 }));

  uiCard(s, mainX, y + 656, mainW * 0.55, 260, { fill: C.white });
  uiText(s, mainX + 16, y + 688, "Model information (view-only)", { size: 16, weight: 700 });
  const modelRows = [["Forecast", "LSTM v1", "Loaded"], ["Unusual spending", "Isolation Forest v1", "Loaded"], ["Recommendations", "Rule-based engine", "Active"]];
  modelRows.forEach((row, index) => {
    const ry = y + 730 + index * 54;
    uiText(s, mainX + 16, ry, row[0], { size: 12, fill: C.mid });
    uiText(s, mainX + 170, ry, row[1], { size: 12.5, weight: 700 });
    uiText(s, mainX + mainW * 0.55 - 16, ry, row[2], { size: 11.5, weight: 700, anchor: "end" });
    s.line(mainX + 16, ry + 16, mainX + mainW * 0.55 - 16, ry + 16, { color: C.pale2, width: 1 });
  });
  uiText(s, mainX + 16, y + 886, "No retraining or model/threshold update controls.", { size: 11.2, fill: C.mid });

  const controlX = mainX + mainW * 0.57;
  const controlW = mainW * 0.43;
  uiCard(s, controlX, y + 656, controlW, 260, { fill: C.pale });
  uiText(s, controlX + 16, y + 688, "System controls", { size: 16, weight: 700 });
  uiText(s, controlX + 16, y + 726, "New analysis requests", { size: 12.5, weight: 700 });
  uiText(s, controlX + controlW - 16, y + 726, "Enabled", { size: 12, weight: 700, anchor: "end" });
  s.rect(controlX + controlW - 82, y + 744, 66, 30, { fill: C.dark, stroke: C.dark, rx: 15, sw: 0 });
  s.circle(controlX + controlW - 34, y + 759, 11, { fill: C.white, stroke: C.white, sw: 0 });
  s.lines(controlX + 16, y + 788, ["Pause/resume is the only model-adjacent update.", "It does not change artefacts, thresholds or history."], { size: 11.5, lineHeight: 20, fill: C.mid });
  uiButton(s, controlX + 16, y + 842, controlW - 32, "Pause new insights", { height: 40 });
  return s.finish();
}

async function buildOverview(filename, files, columns, cellWidth, cellHeight) {
  const rows = Math.ceil(files.length / columns);
  const margin = 35;
  const header = 80;
  const canvasWidth = margin * 2 + columns * cellWidth;
  const canvasHeight = header + margin + rows * cellHeight;
  const composites = [];
  const titleSvg = `<svg xmlns="http://www.w3.org/2000/svg" width="${canvasWidth}" height="${header}"><rect width="100%" height="100%" fill="#ffffff"/><text x="${canvasWidth / 2}" y="48" text-anchor="middle" font-family="Arial" font-size="26" font-weight="700" fill="#171717">SPENDLY FINAL CHAPTER 4 FIGURES - OVERVIEW</text></svg>`;
  composites.push({ input: Buffer.from(titleSvg), left: 0, top: 0 });
  for (let index = 0; index < files.length; index++) {
    const file = files[index];
    const labelHeight = 42;
    const image = await sharp(file.pngPath).resize({ width: cellWidth - 30, height: cellHeight - labelHeight - 30, fit: "contain", background: C.white }).png().toBuffer();
    const col = index % columns;
    const row = Math.floor(index / columns);
    const left = margin + col * cellWidth + 15;
    const top = header + row * cellHeight + labelHeight;
    composites.push({ input: image, left, top });
    const label = file.name.replace(/^\d+_/, "").replaceAll("_", " ").toUpperCase();
    const labelSvg = `<svg xmlns="http://www.w3.org/2000/svg" width="${cellWidth}" height="${labelHeight}"><rect width="100%" height="100%" fill="#f2f2f2"/><text x="${cellWidth / 2}" y="27" text-anchor="middle" font-family="Arial" font-size="15" font-weight="700" fill="#171717">${escapeXml(label)}</text></svg>`;
    composites.push({ input: Buffer.from(labelSvg), left: margin + col * cellWidth, top: header + row * cellHeight });
  }
  await sharp({ create: { width: canvasWidth, height: canvasHeight, channels: 3, background: C.white } }).composite(composites).png().toFile(path.join(OUT, filename));
}

const specs = [
  ["01_final_use_case_diagram", useCaseDiagram],
  ["02_add_import_transaction_activity_diagram", addImportActivity],
  ["03_generate_spending_insights_activity_diagram", insightsActivity],
  ["04_generate_spending_insights_sequence_diagram", sequenceDiagram],
  ["05_class_diagram", classDiagram],
  ["06_conceptual_erd", erdDiagram],
  ["07_logical_database_schema", databaseSchema],
  ["08_system_architecture", architectureDiagram],
  ["09_dashboard_wireframe", dashboardWireframe],
  ["10_add_transaction_wireframe", addTransactionWireframe],
  ["11_forecast_results_wireframe", forecastWireframe],
  ["12_spending_check_wireframe", spendingCheckWireframe],
  ["13_budgets_wireframe", budgetsWireframe],
  ["14_administrator_dashboard_wireframe", adminDashboardWireframe],
];

const built = [];
for (const [name, factory] of specs) built.push(await save(name, factory()));
await buildOverview("00_technical_diagrams_overview.png", built.slice(0, 8), 2, 1000, 760);
await buildOverview("00_wireframes_overview.png", built.slice(8), 3, 700, 1100);
process.stdout.write(`Built ${built.length} editable SVG files and ${built.length + 2} PNG files in ${OUT}\n`);
