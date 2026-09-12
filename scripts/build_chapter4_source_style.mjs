import fs from "node:fs";
import path from "node:path";
import sharp from "file:///C:/Users/evagh/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/sharp/dist/index.mjs";

const OUT = path.resolve("output/chapter4_source_style_final");
fs.mkdirSync(OUT, { recursive: true });

const INK = "#111111";
const WHITE = "#ffffff";
const BLUE = "#185498";

const esc = (value) => String(value)
  .replaceAll("&", "&amp;")
  .replaceAll("<", "&lt;")
  .replaceAll(">", "&gt;")
  .replaceAll('"', "&quot;");

class Svg {
  constructor(width, height, label) {
    this.width = width;
    this.height = height;
    this.parts = [
      `<svg xmlns="http://www.w3.org/2000/svg" width="${width}" height="${height}" viewBox="0 0 ${width} ${height}" role="img" aria-label="${esc(label)}">`,
      `<defs><marker id="arrow" viewBox="0 0 10 10" markerWidth="10" markerHeight="10" refX="9" refY="5" orient="auto" markerUnits="userSpaceOnUse"><path d="M 0 0 L 10 5 L 0 10 Z" fill="${INK}"/></marker></defs>`,
      `<rect width="100%" height="100%" fill="${WHITE}"/>`,
    ];
  }

  rect(x, y, width, height, options = {}) {
    this.parts.push(`<rect x="${x}" y="${y}" width="${width}" height="${height}" rx="${options.rx ?? 10}" ry="${options.rx ?? 10}" fill="${options.fill ?? WHITE}" stroke="${options.stroke ?? INK}" stroke-width="${options.sw ?? 2.2}"${options.dash ? ` stroke-dasharray="${options.dash}"` : ""}/>`);
  }

  line(points, options = {}) {
    this.parts.push(`<polyline points="${points.map((p) => p.join(",")).join(" ")}" fill="none" stroke="${options.stroke ?? INK}" stroke-width="${options.sw ?? 2}" stroke-linecap="round" stroke-linejoin="round"${options.dash ? ` stroke-dasharray="${options.dash}"` : ""}${options.arrow ? ' marker-end="url(#arrow)"' : ""}/>`);
  }

  text(x, y, value, options = {}) {
    this.parts.push(`<text x="${x}" y="${y}" font-family="Arial, Helvetica, sans-serif" font-size="${options.size ?? 20}" font-weight="${options.weight ?? 400}" text-anchor="${options.anchor ?? "middle"}" fill="${options.fill ?? INK}"${options.letterSpacing ? ` letter-spacing="${options.letterSpacing}"` : ""}>${esc(value)}</text>`);
  }

  lines(x, y, values, options = {}) {
    const gap = options.gap ?? (options.size ?? 20) * 1.25;
    values.forEach((value, index) => this.text(x, y + index * gap, value, options));
  }

  ellipse(cx, cy, rx, ry, options = {}) {
    this.parts.push(`<ellipse cx="${cx}" cy="${cy}" rx="${rx}" ry="${ry}" fill="${options.fill ?? WHITE}" stroke="${options.stroke ?? INK}" stroke-width="${options.sw ?? 2.2}"/>`);
  }

  polygon(points, options = {}) {
    this.parts.push(`<polygon points="${points.map((p) => p.join(",")).join(" ")}" fill="${options.fill ?? WHITE}" stroke="${options.stroke ?? INK}" stroke-width="${options.sw ?? 2.2}"/>`);
  }

  actor(x, y, label) {
    this.parts.push(`<circle cx="${x}" cy="${y - 78}" r="20" fill="${WHITE}" stroke="${INK}" stroke-width="2.2"/>`);
    this.line([[x, y - 58], [x, y + 10]]);
    this.line([[x - 34, y - 30], [x + 34, y - 30]]);
    this.line([[x, y + 10], [x - 34, y + 60]]);
    this.line([[x, y + 10], [x + 34, y + 60]]);
    this.text(x, y + 96, label, { size: 22, weight: 600 });
  }

  finish() {
    return `${this.parts.join("\n")}\n</svg>\n`;
  }
}

function activityTitle(s, subtitle) {
  s.text(s.width / 2, 52, "SPENDLY PERSONAL FINANCE MANAGEMENT SYSTEM", { size: 30, weight: 700 });
  s.text(s.width / 2, 88, `${subtitle} — ACTIVITY DIAGRAM`, { size: 20, letterSpacing: 1.2 });
}

function action(s, x, y, width, height, lines, options = {}) {
  s.rect(x, y, width, height, { rx: 11, sw: 2.3, fill: WHITE });
  const size = options.size ?? 21;
  const gap = options.gap ?? size * 1.22;
  const start = y + height / 2 - ((lines.length - 1) * gap) / 2 + size * 0.34;
  s.lines(x + width / 2, start, lines, { size, gap });
}

function decision(s, cx, cy, halfWidth, halfHeight, lines, options = {}) {
  s.polygon([[cx, cy - halfHeight], [cx + halfWidth, cy], [cx, cy + halfHeight], [cx - halfWidth, cy]], { sw: 2.3 });
  const size = options.size ?? 19;
  const gap = options.gap ?? size * 1.2;
  const start = cy - ((lines.length - 1) * gap) / 2 + size * 0.33;
  s.lines(cx, start, lines, { size, gap });
}

function startNode(s, x, y) {
  s.parts.push(`<circle cx="${x}" cy="${y}" r="13" fill="${INK}"/>`);
}

function endNode(s, x, y) {
  s.parts.push(`<circle cx="${x}" cy="${y}" r="20" fill="${WHITE}" stroke="${INK}" stroke-width="2.6"/><circle cx="${x}" cy="${y}" r="11" fill="${INK}"/>`);
}

function buildUseCase() {
  const s = new Svg(2400, 1950, "Spendly Personal Finance Management System - Final Use Case Diagram");
  s.text(1200, 70, "SPENDLY PERSONAL FINANCE MANAGEMENT SYSTEM", { size: 32, weight: 700 });
  s.text(1200, 108, "FINAL USE CASE DIAGRAM", { size: 21, letterSpacing: 1.6 });
  s.rect(210, 145, 1980, 1690, { rx: 2, sw: 2.4 });
  s.text(1200, 180, "Spendly Personal Finance Management System", { size: 19, weight: 600 });

  s.actor(85, 950, "App user");
  s.actor(2315, 950, "Administrator");

  const left = [
    [275, ["Register account"]],
    [440, ["Sign in"]],
    [605, ["Manage profile", "and consent"]],
    [770, ["Manage transactions"]],
    [935, ["Import transaction CSV"]],
    [1100, ["Manage budgets"]],
    [1265, ["View dashboard", "and analytics"]],
    [1430, ["Generate spending insights"]],
    [1595, ["View forecast, alerts", "and recommendations"]],
  ];
  const right = [
    [275, ["Sign in to admin console"]],
    [440, ["Search and inspect accounts"]],
    [605, ["Update account profile or status", "and revoke sessions"]],
    [770, ["Manage user transactions", "and budgets"]],
    [935, ["View stored insights", "(read-only)"]],
    [1100, ["Export account data"]],
    [1265, ["Delete disabled account"]],
    [1430, ["View audit records", "and model information"]],
    [1595, ["Pause or resume", "new analysis"]],
  ];

  const drawCase = (cx, cy, lines, width = 620, size = 23) => {
    s.ellipse(cx, cy, width / 2, 58, { sw: 2.2 });
    const gap = 26;
    const start = cy - ((lines.length - 1) * gap) / 2 + 8;
    s.lines(cx, start, lines, { size, gap });
  };

  left.forEach(([y, lines]) => {
    s.line([[150, 950], [330, y]], { sw: 1.9 });
    drawCase(640, y, lines);
  });
  right.forEach(([y, lines]) => {
    s.line([[2250, 950], [2085, y]], { sw: 1.9 });
    drawCase(1800, y, lines, 570, 22);
  });

  const analyticCases = [
    [1110, ["Forecast next-week spending", "with LSTM or weekly average"]],
    [1335, ["Detect unusual spending", "with Isolation Forest"]],
    [1560, ["Generate rule-based", "recommendations"]],
  ];
  analyticCases.forEach(([y, lines]) => drawCase(1225, y, lines, 440, 20));
  s.line([[950, 1430], [975, 1430], [975, 1110], [1005, 1110]], { dash: "10 8", arrow: true, sw: 1.8 });
  s.text(998, 1093, "<<include>>", { size: 14.5, anchor: "end" });
  s.line([[950, 1430], [980, 1430], [980, 1335], [1005, 1335]], { dash: "10 8", arrow: true, sw: 1.8 });
  s.text(998, 1318, "<<include>>", { size: 14.5, anchor: "end" });
  s.line([[950, 1430], [980, 1430], [980, 1560], [1005, 1560]], { dash: "10 8", arrow: true, sw: 1.8 });
  s.text(998, 1543, "<<include>>", { size: 14.5, anchor: "end" });

  s.text(640, 1775, "Mobile application", { size: 17, fill: "#555555" });
  s.text(1225, 1775, "Analytical functions", { size: 17, fill: "#555555" });
  s.text(1800, 1775, "Browser administrator console", { size: 17, fill: "#555555" });
  return s.finish();
}

function buildAddImportActivity() {
  const s = new Svg(1500, 1770, "Spendly - Add or Import Transaction Activity Diagram");
  activityTitle(s, "ADD OR IMPORT TRANSACTION");
  startNode(s, 750, 125);
  s.line([[750, 138], [750, 160]], { arrow: true, sw: 2.2 });
  action(s, 390, 160, 720, 80, ["Select Add Transaction or Import CSV"], { size: 23 });
  s.line([[750, 240], [750, 275]], { arrow: true });
  decision(s, 750, 335, 125, 60, ["Entry method?"], { size: 21 });

  s.line([[625, 335], [350, 335], [350, 450]], { arrow: true });
  s.text(480, 315, "[Manual entry]", { size: 18 });
  action(s, 100, 450, 500, 90, ["Enter transaction details"], { size: 22 });
  s.line([[875, 335], [1150, 335], [1150, 450]], { arrow: true });
  s.text(1020, 315, "[CSV import]", { size: 18 });
  action(s, 900, 450, 500, 90, ["Select and upload CSV file"], { size: 22 });

  s.line([[350, 540], [350, 590], [730, 590]], { arrow: true });
  s.line([[1150, 540], [1150, 590], [770, 590]], { arrow: true });
  decision(s, 750, 590, 20, 20, [""], { size: 1 });
  s.line([[750, 610], [750, 640]], { arrow: true });
  action(s, 400, 640, 700, 75, ["Parse and normalise transaction data"], { size: 22 });
  s.line([[750, 715], [750, 750]], { arrow: true });
  action(s, 400, 750, 700, 75, ["Validate required fields and data types"], { size: 22 });
  s.line([[750, 825], [750, 855]], { arrow: true });
  decision(s, 750, 915, 120, 60, ["Validation", "outcome?"], { size: 20 });

  s.line([[630, 915], [600, 915]], { arrow: true });
  s.text(470, 852, "[Manual issue]", { size: 17 });
  action(s, 100, 870, 500, 90, ["Show errors and correct", "manual-entry fields"], { size: 19 });
  s.line([[100, 915], [55, 915], [55, 495], [100, 495]], { arrow: true });

  s.line([[870, 915], [900, 915]], { arrow: true });
  s.text(1030, 852, "[CSV issue]", { size: 17 });
  action(s, 900, 870, 500, 90, ["Show errors and correct", "CSV rows or file"], { size: 19 });
  s.line([[1400, 915], [1445, 915], [1445, 495], [1400, 495]], { arrow: true });

  s.line([[750, 975], [750, 1020]], { arrow: true });
  s.text(795, 1005, "[Valid]", { size: 17, anchor: "start" });
  action(s, 390, 1020, 720, 78, ["Check duplicates and confirm category"], { size: 22 });
  s.line([[750, 1098], [750, 1130]], { arrow: true });
  decision(s, 750, 1190, 125, 60, ["Issue", "detected?"], { size: 20 });

  s.line([[625, 1190], [600, 1190]], { arrow: true });
  s.text(470, 1128, "[Manual correction]", { size: 16.5 });
  action(s, 100, 1145, 500, 90, ["Resolve duplicate or category", "issue in manual entry"], { size: 18.5 });
  s.line([[100, 1190], [25, 1190], [25, 510], [100, 510]], { arrow: true });

  s.line([[875, 1190], [900, 1190]], { arrow: true });
  s.text(1030, 1128, "[CSV correction]", { size: 16.5 });
  action(s, 900, 1145, 500, 90, ["Resolve duplicate or category", "issue in CSV data"], { size: 18.5 });
  s.line([[1400, 1190], [1475, 1190], [1475, 510], [1400, 510]], { arrow: true });

  s.line([[750, 1250], [750, 1290]], { arrow: true });
  s.text(795, 1275, "[No issue]", { size: 17, anchor: "start" });
  action(s, 420, 1290, 660, 75, ["Save transaction record(s)"], { size: 22 });
  s.line([[750, 1365], [750, 1400]], { arrow: true });
  action(s, 380, 1400, 740, 78, ["Update spending summary and budget progress"], { size: 21 });
  s.line([[750, 1478], [750, 1515]], { arrow: true });
  action(s, 420, 1515, 660, 75, ["Display confirmation"], { size: 22 });
  s.line([[750, 1590], [750, 1640]], { arrow: true });
  endNode(s, 750, 1665);
  return s.finish();
}

function message(s, from, to, y, lines, options = {}) {
  s.line([[from, y], [to, y]], { arrow: true, dash: options.dash ?? "", sw: 1.8 });
  const center = (from + to) / 2;
  const values = Array.isArray(lines) ? lines : [lines];
  const size = options.size ?? 17.5;
  const gap = size * 1.18;
  const start = y - 11 - (values.length - 1) * gap;
  s.lines(center, start, values, { size, gap });
}

function buildSequence() {
  const s = new Svg(2200, 1600, "Spendly - Generate Spending Insights Sequence Diagram");
  s.text(1100, 58, "SPENDLY PERSONAL FINANCE MANAGEMENT SYSTEM", { size: 30, weight: 700 });
  s.text(1100, 96, "GENERATE SPENDING INSIGHTS — SEQUENCE DIAGRAM", { size: 20, letterSpacing: 1.2 });

  const participants = [
    [90, "User"], [340, "Flutter mobile app"], [610, "Flask REST API"], [860, "JWT and user scope"],
    [1120, "Feature preparation"], [1400, "Model service / artefact loader"], [1690, "Rule-based recommendation engine"], [2050, "Database"],
  ];
  s.actor(90, 205, "User");
  participants.slice(1).forEach(([x, label]) => {
    const width = label.length > 25 ? 250 : 210;
    s.rect(x - width / 2, 135, width, 58, { rx: 6, sw: 1.9, fill: WHITE });
    const words = label.length > 25 ? [label.slice(0, label.lastIndexOf(" ", 24)), label.slice(label.lastIndexOf(" ", 24) + 1)] : [label];
    s.lines(x, words.length === 1 ? 171 : 157, words, { size: 17.5, gap: 20 });
  });
  participants.forEach(([x]) => s.line([[x, x === 90 ? 285 : 193], [x, 1545]], { dash: "8 7", sw: 1.3 }));

  s.rect(330, 215, 20, 1320, { rx: 1, sw: 1.1, fill: "#f2f2f2" });
  s.rect(600, 280, 20, 1205, { rx: 1, sw: 1.1, fill: "#f2f2f2" });
  s.rect(850, 340, 20, 245, { rx: 1, sw: 1.1, fill: "#f2f2f2" });
  s.rect(1110, 735, 20, 90, { rx: 1, sw: 1.1, fill: "#f2f2f2" });
  s.rect(1390, 900, 20, 330, { rx: 1, sw: 1.1, fill: "#f2f2f2" });
  s.rect(1680, 1240, 20, 100, { rx: 1, sw: 1.1, fill: "#f2f2f2" });
  s.rect(2040, 625, 20, 820, { rx: 1, sw: 1.1, fill: "#f2f2f2" });

  s.rect(565, 390, 345, 205, { rx: 2, sw: 1.4, fill: "none" });
  s.line([[565, 520], [910, 520]], { dash: "8 6", sw: 1.2 });
  s.rect(565, 855, 900, 245, { rx: 2, sw: 1.4, fill: "none" });
  s.line([[565, 980], [1465, 980]], { dash: "8 6", sw: 1.2 });

  message(s, 90, 340, 235, "1. Request fresh insights");
  message(s, 340, 610, 300, ["2. POST /api/v1/analysis/run", "Authorization: Bearer <JWT>"], { size: 15.5 });
  message(s, 610, 860, 360, ["3. Validate JWT, active account", "and analysis setting"], { size: 15.5 });
  s.text(590, 415, "alt  request rejected", { size: 16, weight: 700, anchor: "start" });
  message(s, 860, 610, 455, "4a. Rejection details", { dash: "8 6", size: 15.5 });
  message(s, 610, 340, 500, "4b. Error envelope (401 / 422 / 503)", { dash: "8 6", size: 15 });
  s.text(590, 548, "else  request accepted", { size: 16, weight: 700, anchor: "start" });
  message(s, 860, 610, 580, "4c. Authenticated user", { dash: "8 6", size: 15.5 });

  message(s, 610, 2050, 640, "5. Read user transactions and active budgets", { size: 16 });
  message(s, 2050, 610, 700, "6. Return user-owned records", { dash: "8 6" });
  message(s, 610, 1120, 760, "7. Prepare weekly and transaction features");
  message(s, 1120, 610, 820, "8. Return history count and model inputs", { dash: "8 6", size: 16 });

  s.text(590, 880, "alt  eight or more complete weeks", { size: 16, weight: 700, anchor: "start" });
  message(s, 610, 1400, 920, "9a. Run LSTM forecast");
  message(s, 1400, 610, 965, "9b. Return next-week estimate", { dash: "8 6" });
  s.text(590, 1010, "else  fewer than eight complete weeks", { size: 16, weight: 700, anchor: "start" });
  s.line([[620, 1065], [740, 1065], [740, 1085], [620, 1085]], { arrow: true, sw: 1.7 });
  s.text(875, 1055, "9c. Use personal weekly-average fallback", { size: 16 });

  message(s, 610, 1400, 1150, "10. Score expense features with Isolation Forest", { size: 16.5 });
  message(s, 1400, 610, 1200, "11. Return alerts, scores and explanations", { dash: "8 6", size: 16.5 });
  message(s, 610, 1690, 1260, "12. Evaluate transparent recommendation rules", { size: 16.5 });
  message(s, 1690, 610, 1310, "13. Return recommendations and reasons", { dash: "8 6", size: 16.5 });
  message(s, 610, 2050, 1370, "14. Store AnalysisRun, Forecast, Alerts and Recommendations", { size: 16 });
  message(s, 2050, 610, 1420, "15. Confirm database commit", { dash: "8 6" });
  message(s, 610, 340, 1470, "16. HTTP 200 success envelope", { dash: "8 6" });
  message(s, 340, 90, 1520, "17. Display forecast, alerts and recommendations", { dash: "8 6", size: 15.5 });
  return s.finish();
}

function tableBox(s, x, y, width, title, rows, options = {}) {
  const header = options.header ?? 48;
  const rowH = options.rowH ?? 32;
  const footerH = options.footer ? 38 : 0;
  const height = header + rows.length * rowH + footerH + 14;
  const keyW = options.keyW ?? 90;
  const fieldW = options.fieldW ?? Math.round(width * 0.56);
  s.rect(x, y, width, height, { rx: 8, sw: 2.2, fill: WHITE });
  s.line([[x, y + header], [x + width, y + header]], { sw: 1.8 });
  s.line([[x + keyW, y + header], [x + keyW, y + height - footerH]], { sw: 1.4 });
  s.line([[x + fieldW, y + header], [x + fieldW, y + height - footerH]], { sw: 1.4 });
  s.text(x + width / 2, y + 33, title, { size: options.titleSize ?? 25, weight: 500 });
  rows.forEach(([key, field, type], index) => {
    const ty = y + header + 26 + index * rowH;
    s.text(x + 14, ty, key, { size: options.size ?? 21, anchor: "start" });
    s.text(x + keyW + 14, ty, field, { size: options.size ?? 21, weight: key === "PK" ? 700 : 400, anchor: "start" });
    s.text(x + fieldW + 14, ty, type, { size: options.size ?? 21, anchor: "start" });
  });
  if (options.footer) {
    s.line([[x, y + height - footerH], [x + width, y + height - footerH]], { sw: 1.3 });
    s.text(x + 14, y + height - 12, options.footer, { size: options.footerSize ?? 17, anchor: "start" });
  }
  return { x, y, width, height, left: x, right: x + width, top: y, bottom: y + height, cx: x + width / 2, cy: y + height / 2 };
}

function dbRelationship(s, points, code, startCardinality, endCardinality, options = {}) {
  s.line(points, { sw: 1.8 });
  const start = points[0];
  const end = points.at(-1);
  s.text(start[0] + (options.startDx ?? 20), start[1] + (options.startDy ?? -12), startCardinality, { size: 17, anchor: "start" });
  s.text(end[0] + (options.endDx ?? -20), end[1] + (options.endDy ?? -12), endCardinality, { size: 17, anchor: "end" });
  const segment = Math.floor((points.length - 1) / 2);
  const a = points[segment];
  const b = points[segment + 1];
  const mid = [(a[0] + b[0]) / 2, (a[1] + b[1]) / 2];
  s.text(mid[0] + (options.codeDx ?? 0), mid[1] + (options.codeDy ?? -12), code, { size: 17, weight: 600 });
}

function buildDatabaseSchema() {
  const s = new Svg(4000, 2400, "Spendly Personal Finance Management System - Database Schema");
  s.text(2000, 72, "SPENDLY PERSONAL FINANCE MANAGEMENT SYSTEM — DATABASE SCHEMA", { size: 34, weight: 500 });

  const users = tableBox(s, 80, 170, 850, "USERS", [
    ["PK", "id", "VARCHAR(36)"], ["UQ", "email", "VARCHAR(255)"], ["", "password_hash ?", "VARCHAR(255)"], ["UQ", "google_subject ?", "VARCHAR(255)"],
    ["", "display_name", "VARCHAR(100)"], ["", "username", "VARCHAR(30)"], ["UQ", "username_normalized", "VARCHAR(30)"], ["", "monthly_income ?", "NUMERIC(14,2)"],
    ["", "terms_accepted_at ?", "TIMESTAMP"], ["", "privacy_accepted_at ?", "TIMESTAMP"], ["", "consent_version ?", "VARCHAR(30)"], ["", "model_training_opt_in", "BOOLEAN"],
    ["", "model_training_consented_at ?", "TIMESTAMP"], ["", "onboarding_completed_at ?", "TIMESTAMP"], ["", "is_active", "BOOLEAN"], ["", "auth_version", "INT"], ["", "created_at", "TIMESTAMP"],
  ], { rowH: 34, keyW: 90, fieldW: 600, size: 22, footer: "UQ: email, google_subject, username_normalized | CK: password_hash OR google_subject", footerSize: 16 });

  const transactions = tableBox(s, 80, 1000, 850, "TRANSACTIONS", [
    ["PK", "id", "VARCHAR(36)"], ["FK", "user_id", "VARCHAR(36)"], ["", "transaction_timestamp", "TIMESTAMP"], ["", "amount", "NUMERIC(14,2)"],
    ["", "currency", "VARCHAR(3)"], ["", "category", "VARCHAR(80)"], ["", "transaction_type", "VARCHAR(10)"], ["", "merchant ?", "VARCHAR(120)"],
    ["", "is_recurring", "BOOLEAN"], ["", "source", "VARCHAR(20)"], ["", "fingerprint", "VARCHAR(64)"], ["", "created_at", "TIMESTAMP"],
  ], { rowH: 34, keyW: 90, fieldW: 600, size: 22, footer: "UQ: (user_id, fingerprint)", footerSize: 17 });

  const budgets = tableBox(s, 80, 1710, 850, "BUDGETS", [
    ["PK", "id", "VARCHAR(36)"], ["FK", "user_id", "VARCHAR(36)"], ["", "period_start", "DATE"], ["", "period_end", "DATE"],
    ["", "category", "VARCHAR(80)"], ["", "amount", "NUMERIC(14,2)"], ["", "currency", "VARCHAR(3)"], ["", "created_at", "TIMESTAMP"], ["", "updated_at", "TIMESTAMP"],
  ], { rowH: 32, keyW: 90, fieldW: 600, size: 21, footer: "UQ: (user_id, period_start, period_end, category)", footerSize: 16 });

  const runs = tableBox(s, 1450, 170, 800, "ANALYSIS_RUNS", [
    ["PK", "id", "VARCHAR(36)"], ["FK", "user_id", "VARCHAR(36)"], ["", "status", "VARCHAR(20)"], ["", "forecast_model_version", "VARCHAR(30)"],
    ["", "anomaly_model_version", "VARCHAR(30)"], ["", "history_periods", "INT"], ["", "generated_at", "TIMESTAMP"],
  ], { rowH: 34, keyW: 90, fieldW: 540, size: 22 });

  const forecasts = tableBox(s, 2950, 170, 900, "FORECASTS", [
    ["PK", "id", "VARCHAR(36)"], ["FK/UQ", "analysis_run_id", "VARCHAR(36)"], ["FK", "user_id", "VARCHAR(36)"], ["", "period_start", "DATE"],
    ["", "period_end", "DATE"], ["", "predicted_spending", "NUMERIC(14,2)"], ["", "baseline_prediction ?", "NUMERIC(14,2)"], ["", "currency", "VARCHAR(3)"],
    ["", "model_version", "VARCHAR(30)"], ["", "created_at", "TIMESTAMP"],
  ], { rowH: 34, keyW: 110, fieldW: 650, size: 22 });

  const alerts = tableBox(s, 1450, 820, 800, "ANOMALY_ALERTS", [
    ["PK", "id", "VARCHAR(36)"], ["FK", "analysis_run_id", "VARCHAR(36)"], ["FK", "user_id", "VARCHAR(36)"], ["FK", "transaction_id ?", "VARCHAR(36)"],
    ["", "is_unusual_spending", "BOOLEAN"], ["", "anomaly_score", "FLOAT"], ["", "decision_threshold", "FLOAT"], ["", "explanation", "TEXT"],
    ["", "review_status", "VARCHAR(20)"], ["", "reviewed_at ?", "TIMESTAMP"], ["", "model_version", "VARCHAR(30)"], ["", "created_at", "TIMESTAMP"],
  ], { rowH: 34, keyW: 90, fieldW: 535, size: 21 });

  const recommendations = tableBox(s, 2950, 820, 900, "RECOMMENDATIONS", [
    ["PK", "id", "VARCHAR(36)"], ["FK", "analysis_run_id", "VARCHAR(36)"], ["FK", "user_id", "VARCHAR(36)"], ["", "recommendation_code", "VARCHAR(100)"],
    ["", "title", "VARCHAR(160)"], ["", "message", "TEXT"], ["", "severity", "VARCHAR(20)"], ["", "reason", "TEXT"],
    ["", "supporting_values", "JSON"], ["", "suggested_action", "TEXT"], ["", "disclaimer", "TEXT"], ["", "created_at", "TIMESTAMP"],
  ], { rowH: 34, keyW: 90, fieldW: 650, size: 21 });

  const versions = tableBox(s, 1080, 1580, 680, "MODEL_VERSIONS", [
    ["PK", "id", "VARCHAR(36)"], ["", "component", "VARCHAR(36)"], ["", "version", "VARCHAR(30)"], ["", "artifact_path", "VARCHAR(500)"],
    ["", "metadata_json", "JSON"], ["", "is_active", "BOOLEAN"], ["", "created_at", "TIMESTAMP"],
  ], { rowH: 30, keyW: 80, fieldW: 465, size: 19, footer: "UQ: (component, version)", footerSize: 16 });

  const audit = tableBox(s, 1840, 1540, 720, "ADMIN_AUDIT", [
    ["PK", "id", "VARCHAR(36)"], ["", "actor", "VARCHAR(255)"], ["", "action", "VARCHAR(80)"], ["", "target_type", "VARCHAR(40)"],
    ["", "target_id", "VARCHAR(64)"], ["", "reason", "VARCHAR(300)"], ["", "details", "JSON"], ["", "created_at", "TIMESTAMP"],
  ], { rowH: 30, keyW: 80, fieldW: 490, size: 19 });

  tableBox(s, 2670, 1580, 540, "ADMIN_LOGIN_ATTEMPTS", [
    ["PK", "id", "VARCHAR(36)"], ["", "client_key", "VARCHAR(64)"], ["", "created_at", "TIMESTAMP"],
  ], { rowH: 30, keyW: 70, fieldW: 360, size: 18 });
  tableBox(s, 3300, 1580, 500, "SYSTEM_SETTINGS", [
    ["PK", "key", "VARCHAR(64)"], ["", "enabled", "BOOLEAN"],
  ], { rowH: 30, keyW: 70, fieldW: 335, size: 18 });

  dbRelationship(s, [[users.cx, users.bottom], [users.cx, transactions.top]], "R1", "1", "0..*", { codeDx: 55, codeDy: -18 });
  dbRelationship(s, [[users.left + 120, users.bottom], [45, users.bottom], [45, budgets.cy], [budgets.left, budgets.cy]], "R2", "1", "0..*", { startDx: 25, endDx: -10, endDy: 28, codeDx: 24 });
  dbRelationship(s, [[users.right, 300], [runs.left, 300]], "R3", "1", "0..*", { codeDy: -18 });
  dbRelationship(s, [[users.right, 230], [1120, 230], [1120, 125], [2850, 125], [2850, 280], [forecasts.left, 280]], "R4", "1", "0..*", { codeDy: -18 });
  dbRelationship(s, [[users.right, 590], [1250, 590], [1250, 950], [alerts.left, 950]], "R5", "1", "0..*", { codeDx: 28 });
  dbRelationship(s, [[users.right, 650], [1120, 650], [1120, 1470], [2800, 1470], [2800, 1050], [recommendations.left, 1050]], "R6", "1", "0..*", { codeDx: 30 });
  dbRelationship(s, [[runs.right, 360], [2720, 360], [2720, 380], [forecasts.left, 380]], "R7", "1", "1", { codeDy: -18 });
  dbRelationship(s, [[runs.cx, runs.bottom], [runs.cx, alerts.top]], "R8", "1", "0..*", { codeDx: 55 });
  dbRelationship(s, [[runs.right, 480], [2660, 480], [2660, 980], [recommendations.left, 980]], "R9", "1", "0..*", { codeDx: 34 });
  dbRelationship(s, [[transactions.right, 1200], [1300, 1200], [1300, 1120], [alerts.left, 1120]], "R10", "1", "0..*", { codeDx: 36 });

  s.rect(1080, 2040, 2720, 255, { rx: 6, sw: 1.6, fill: WHITE });
  s.text(1120, 2080, "RELATIONSHIP AND INTEGRITY NOTES", { size: 22, weight: 700, anchor: "start" });
  s.lines(1120, 2120, [
    "R1 users.id → transactions.user_id    R2 users.id → budgets.user_id    R3 users.id → analysis_runs.user_id",
    "R4 users.id → forecasts.user_id       R5 users.id → anomaly_alerts.user_id       R6 users.id → recommendations.user_id",
    "R7 analysis_runs.id → forecasts.analysis_run_id    R8 → anomaly_alerts.analysis_run_id    R9 → recommendations.analysis_run_id",
    "R10 transactions.id → anomaly_alerts.transaction_id (optional). Category is stored as text; there is no CATEGORIES table.",
    "Authentication requires password_hash OR google_subject. Administrator identity is server configuration; there is no ROLES table.",
  ], { size: 19, anchor: "start", gap: 34 });
  s.text(80, 2335, "PK = primary key   FK = foreign key   UQ = unique   ? = nullable   |   Alert review fields and the authentication check are required final-schema corrections.", { size: 20, anchor: "start" });
  return s.finish();
}

function patchInsightsActivity() {
  const input = String.raw`C:\Users\evagh\Downloads\chapter 4 diagrams\Activity Diagram\final\Spendly_Activity_Generate_Spending_Insights.svg`;
  let svg = fs.readFileSync(input, "utf8");
  svg = svg
    .replace(/>SPENDLY[^<]*GENERATE SPENDING INSIGHTS<\/text>/, ">SPENDLY PERSONAL FINANCE MANAGEMENT SYSTEM</text>")
    .replace(">ACTIVITY DIAGRAM</text>", ">GENERATE SPENDING INSIGHTS — ACTIVITY DIAGRAM</text>")
    .replace('<text x="270" y="660.0" font-family="Arial, Helvetica, sans-serif" font-size="17" font-weight="400" text-anchor="middle" fill="#111111">[No]</text>', '<text x="225" y="744" font-family="Arial, Helvetica, sans-serif" font-size="15" font-weight="400" text-anchor="middle" fill="#111111">[Fewer than eight complete weeks]</text>')
    .replace('<text x="590" y="660.0" font-family="Arial, Helvetica, sans-serif" font-size="17" font-weight="400" text-anchor="middle" fill="#111111">[Yes]</text>', '<text x="645" y="744" font-family="Arial, Helvetica, sans-serif" font-size="15" font-weight="400" text-anchor="middle" fill="#111111">[Eight or more complete weeks]</text>')
    .replace("forecast with LSTM v1</text>", "forecast with LSTM</text>")
    .replace("using Isolation Forest v1</text>", "using Isolation Forest</text>")
    .replace("using the rule-based engine</text>", "using the rule-based recommendation engine</text>");
  return svg;
}

function patchArchitecture() {
  const input = String.raw`C:\Users\evagh\Downloads\chapter 4 diagrams\System Architecture\07_System_Architecture.svg`;
  let svg = fs.readFileSync(input, "utf8");
  svg = svg
    .replace(">scikit-learn</text>", ">LSTM • ISOLATION FOREST • RULES</text>")
    .replace("• Forecast: multiple linear regression v1", "• Forecast: LSTM")
    .replace("• Early history: weekly-average baseline", "• Fewer than 8 weeks: weekly-average fallback")
    .replace("• Anomalies: Isolation Forest v1", "• Anomalies: Isolation Forest")
    .replace("• Recommendations: transparent rules", "• Recommendations: rule-based engine")
    .replace("Android mobile client | Render-hosted Flask service | Neon PostgreSQL | Lightweight v1 runtime", "Android mobile client | Render-hosted Flask service | Neon PostgreSQL | LSTM + Isolation Forest + rule-based engine");
  return svg;
}

const figures = [
  ["01_Database_Schema_Final.svg", buildDatabaseSchema()],
  ["02_Final_Use_Case_Diagram.svg", buildUseCase()],
  ["03_Activity_Add_Import_Transaction_Final.svg", buildAddImportActivity()],
  ["04_Activity_Generate_Spending_Insights_Final.svg", patchInsightsActivity()],
  ["05_Sequence_Generate_Spending_Insights_Final.svg", buildSequence()],
  ["06_System_Architecture_Final.svg", patchArchitecture()],
];

for (const [name, svg] of figures) {
  const svgPath = path.join(OUT, name);
  fs.writeFileSync(svgPath, svg, "utf8");
  await sharp(Buffer.from(svg), { density: 180 }).flatten({ background: WHITE }).png().toFile(svgPath.replace(/\.svg$/i, ".png"));
}

const pngs = figures.map(([name]) => path.join(OUT, name.replace(/\.svg$/i, ".png")));
const thumbs = [];
for (let i = 0; i < pngs.length; i += 1) {
  const thumb = await sharp(pngs[i]).resize({ width: 900, height: 620, fit: "contain", background: WHITE }).png().toBuffer();
  thumbs.push({ input: thumb, left: (i % 2) * 940 + 40, top: Math.floor(i / 2) * 690 + 90 });
}
await sharp({ create: { width: 1880, height: 2180, channels: 3, background: WHITE } })
  .composite(thumbs)
  .png()
  .toFile(path.join(OUT, "00_Revised_Figures_Overview.png"));

console.log(`Built ${figures.length} source-style final figures in ${OUT}`);
