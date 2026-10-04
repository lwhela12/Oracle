// Content coverage and public lookup contract; no model or browser required.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const root = path.resolve(__dirname, '../static/astrology');
const sources = ['aspects-sun-moon.js', 'aspects-mercury-venus.js', 'aspects-outer.js', 'aspects-self.js'];
const context = vm.createContext({window: {}});
const html = fs.readFileSync(path.join(root, 'index.html'), 'utf8');
const seenPairs = new Set();
for (const source of sources) {
  const before = new Map(Object.entries(context.window.AstrologyAspectLibrary || {}));
  vm.runInContext(fs.readFileSync(path.join(root, source), 'utf8'), context, {filename: source});
  for (const [key, entry] of before) assert.equal(context.window.AstrologyAspectLibrary[key], entry, `${source} overwrote ${key}`);
  for (const key of Object.keys(context.window.AstrologyAspectLibrary)) seenPairs.add(key);
  assert.ok(html.indexOf(`/static/astrology/${source}?`) < html.indexOf('/static/astrology/meanings.js?'), `${source} must load before lookup`);
}
vm.runInContext(fs.readFileSync(path.join(root, 'meanings.js'), 'utf8'), context);
const lookup = context.window.AstrologyMeanings.aspect;
const bodies = ['Sun', 'Moon', 'Mercury', 'Venus', 'Mars', 'Jupiter', 'Saturn', 'Uranus', 'Neptune', 'Pluto'];
const aspects = ['conjunction', 'sextile', 'square', 'trine', 'opposition'];
const expectedPairs = [];
const paragraphs = [];
for (let i = 0; i < bodies.length; i++) {
  for (let j = i; j < bodies.length; j++) {
    const first = bodies[i], second = bodies[j], key = `${first}|${second}`;
    expectedPairs.push(key);
    const entry = context.window.AstrologyAspectLibrary[key];
    assert.ok(entry, `Missing pair ${key}`);
    assert.deepEqual(Object.keys(entry).sort(), [...aspects].sort(), `Aspect coverage for ${key}`);
    for (const aspect of aspects) {
      const paragraph = entry[aspect];
      assert.equal(typeof paragraph, 'string');
      assert.ok(paragraph.trim().split(/\s+/).length >= 25, `Incomplete paragraph: ${key} ${aspect}`);
      assert.ok(!paragraph.includes('?'), `Stock reflection question: ${key} ${aspect}`);
      assert.equal(lookup(first, second, aspect, 'transit'), paragraph);
      if (i !== j) {
        assert.equal(lookup(second, first, aspect, 'natal'), paragraph, `Reversed natal lookup: ${key}`);
        assert.equal(lookup(first, second, aspect, 'current'), paragraph);
        assert.equal(lookup(first, second, aspect, 'horoscope'), paragraph);
      } else {
        assert.notEqual(lookup(first, second, aspect, 'natal'), paragraph, 'Self aspects must remain transit-only');
      }
      paragraphs.push(paragraph);
    }
  }
}
assert.deepEqual([...seenPairs].sort(), expectedPairs.sort(), 'Unexpected or missing planet pairs');
assert.equal(paragraphs.length, 275);
assert.equal(new Set(paragraphs).size, 275, 'Duplicate authored passages');
assert.equal(lookup(' venus ', 'SATURN', ' Opposition ', 'natal'), lookup('Venus', 'Saturn', 'opposition', 'natal'));
assert.match(lookup('Not a planet', 'Moon', 'trine', 'natal'), /not included/);
assert.match(lookup('Sun', 'Moon', 'invalid', 'natal'), /not included/);
// An unavailable asset must not take down placement/retrograde descriptions.
const missing = vm.createContext({window: {}});
vm.runInContext(fs.readFileSync(path.join(root, 'meanings.js'), 'utf8'), missing);
assert.match(missing.window.AstrologyMeanings.aspect('Sun', 'Moon', 'trine', 'natal'), /not available/);
assert.ok(missing.window.AstrologyMeanings.placement('Sun', 'Aries', 1, 'natal').length);
console.log('PASS: 225 pair/aspect essays + 50 self-transit essays; all lookups, coverage, uniqueness, script order, and fallback checks.');
