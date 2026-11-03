const {test} = require('node:test');
const assert = require('node:assert/strict');
const {readFileSync} = require('node:fs');
const {join} = require('node:path');

const management = readFileSync(join(__dirname, '../app/static/admin/manage.css'), 'utf8');
const overview = readFileSync(join(__dirname, '../app/templates/admin/dashboard.html'), 'utf8');

function contrast(first, second) {
  const luminance = hex => {
    const rgb = hex.match(/\w\w/g).map(value => parseInt(value, 16) / 255);
    const linear = rgb.map(value => value <= 0.04045 ? value / 12.92 : ((value + 0.055) / 1.055) ** 2.4);
    return linear.reduce((total, value, index) => total + value * [0.2126, 0.7152, 0.0722][index], 0);
  };
  const values = [luminance(first), luminance(second)].sort((a, b) => a - b);
  return (values[1] + 0.05) / (values[0] + 0.05);
}

test('management focus outline contrasts with its light surfaces', () => {
  const declaration = management.match(/textarea:focus\{outline:3px solid ([^;]+)/)[1];
  const color = declaration.startsWith('var(')
    ? management.match(new RegExp(declaration.slice(4, -1) + ':\\s*#([\\da-f]{6})', 'i'))[1]
    : declaration.slice(1);
  for (const background of ['ffffff', 'dff2eb', 'f3f6f4']) {
    assert(contrast(color, background) >= 3, `Focus #${color} on #${background} must reach 3:1`);
  }
});

test('sidebar focus uses its readable text color in dark and light layouts', () => {
  for (const styles of [management, overview]) {
    assert.match(styles, /aside a:focus-visible\s*\{\s*outline-color:\s*currentColor;?\s*\}/);
  }
  for (const [text, background] of [
    ['d9ebe5', '0e493f'], ['ffffff', '0e493f'], ['60746f', 'ffffff'], ['0e493f', 'dff2eb'],
  ]) {
    assert(contrast(text, background) >= 3);
  }
});

test('narrow management navigation wraps instead of horizontal scrolling', () => {
  const mobile = management.slice(management.indexOf('@media(max-width:760px)'));
  assert.match(mobile, /nav\{[^}]*flex-wrap:wrap/);
  assert.match(mobile, /nav a\{white-space:normal/);
});
