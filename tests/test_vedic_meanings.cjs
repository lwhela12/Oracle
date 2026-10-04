// Content coverage and public lookup contract; no model or browser required.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const source = path.resolve(__dirname, '../static/astrology/vedic-meanings.js');
const context = vm.createContext({window: {}});
vm.runInContext(fs.readFileSync(source, 'utf8'), context, {filename: source});
const meanings = context.window.VedicMeanings;

assert.ok(Object.isFrozen(meanings));
const planets = ['Sun', 'Moon', 'Mercury', 'Venus', 'Mars', 'Jupiter', 'Saturn', 'Rahu', 'Ketu'];
const signs = ['Aries', 'Taurus', 'Gemini', 'Cancer', 'Leo', 'Virgo', 'Libra', 'Scorpio', 'Sagittarius', 'Capricorn', 'Aquarius', 'Pisces'];

assert.deepEqual(Object.keys(meanings.tables.planets), planets);
assert.equal(Object.keys(meanings.tables.houses).length, 12);
for (let house = 1; house <= 12; house++) {
  assert.match(meanings.tables.houses[house], /bhava/i);
  assert.ok(meanings.tables.houses[house].split(/\s+/).length >= 20);
}

const rashiTexts = [];
for (const graha of planets) {
  assert.ok(meanings.planet(graha).split(/\s+/).length >= 15, `planet description: ${graha}`);
  for (const sign of signs) {
    const sections = meanings.placement(graha, {sign}, 'natal');
    assert.equal(sections.length, 1);
    assert.equal(sections[0].title, `${graha} in ${sign}`);
    assert.ok(sections[0].text.split(/\s+/).length >= 18, `${graha} in ${sign}`);
    assert.ok(!/not included|undefined/i.test(sections[0].text));
    assert.ok(!sections[0].text.includes('?'));
    rashiTexts.push(sections[0].text);
  }
}
assert.equal(rashiTexts.length, 108);
assert.equal(new Set(rashiTexts).size, 108, 'All 108 graha-in-rashi passages must be distinct');

const nakshatras = meanings.tables.nakshatras;
assert.equal(nakshatras.length, 27);
assert.equal(new Set(nakshatras.map(item => item.text)).size, 27);
assert.deepEqual(Array.from(nakshatras, item => item.index), Array.from({length: 27}, (_, index) => index + 1));
for (const star of nakshatras) {
  for (let pada = 1; pada <= 4; pada++) {
    const sections = meanings.placement('Moon', {
      sign: 'Aries',
      nakshatra: {name: star.name, index: star.index, pada, lord: star.lord}
    }, 'natal');
    const detail = sections[1];
    assert.equal(detail.title, `${star.name}, pada ${pada}`);
    assert.match(detail.text, new RegExp(`Pada ${pada} is the`));
    assert.match(detail.text, /quarter/i);
    assert.doesNotMatch(detail.text, /Navamsa/i);
  }
}

for (let house = 1; house <= 12; house++) {
  const natal = meanings.placement('Jupiter', {sign: 'Sagittarius', whole_sign_house: house}, 'natal');
  assert.equal(natal.length, 2);
  assert.match(natal[1].title, /bhava/);
}
const horoscope = meanings.placement('Moon', {
  sign: 'Taurus', whole_sign_house: 4,
  nakshatra: {name: 'Rohini', index: 4, pada: 2, lord: 'Moon'}
}, 'horoscope');
assert.equal(horoscope.length, 2, 'Horoscope must omit the supplied natal-style house');
assert.match(horoscope[0].text, /current sidereal sky/i);
assert.doesNotMatch(horoscope.map(section => section.text).join(' '), /bhava|natal chart|temperament|your house/i);

assert.match(meanings.planet('Rahu'), /mean ascending lunar node.*not a physical planet/i);
assert.match(meanings.planet('Ketu'), /mean descending lunar node.*not a physical planet/i);
assert.match(meanings.retrograde('Rahu', 'current'), /mean lunar node.*continuous convention.*not interpreted as a planet turning retrograde or stationing/i);
assert.match(meanings.retrograde('Ketu', 'natal'), /mean lunar node.*not a physical planet/i);

const marsFourth = meanings.aspect('Mars', 'Moon', 'full', 'natal', 4);
const marsEighth = meanings.aspect('Mars', 'Moon', 'full', 'natal', 8);
const jupiterFifth = meanings.aspect('Jupiter', 'Moon', 'full', 'natal', 5);
const reverse = meanings.aspect('Moon', 'Mars', 'full', 'natal', 7);
assert.notEqual(marsFourth, marsEighth, 'Distance must change the directional explanation');
assert.notEqual(marsFourth, jupiterFifth, 'Source graha must change the directional explanation');
assert.notEqual(marsFourth, reverse, 'Direction must not be collapsed into an unordered pair');
for (const text of [marsFourth, marsEighth, jupiterFifth, reverse]) {
  assert.match(text, /directional drishti/i);
  assert.doesNotMatch(text, /\b(square|sextile|trine|opposition|orb)\b/i);
}
assert.match(meanings.aspect('Saturn', 'Sun', 'drishti', 'current', 10), /10th-place special glance of Saturn/);
assert.match(meanings.aspect('Sun', 'Saturn', 'full', 'current', 7), /seventh-place glance/);
assert.match(meanings.aspect('Sun', 'Moon', 'full', 'current', 4), /not included/);
assert.match(meanings.aspect('Rahu', 'Moon', 'full', 'current', 7), /not included/);
assert.match(meanings.aspect('Ketu', 'Sun', 'full', 'natal', 7), /not included/);

assert.match(meanings.planet('Unknown'), /not included/);
assert.match(meanings.retrograde('Unknown', 'natal'), /not included/);
assert.match(meanings.aspect('Unknown', 'Moon', 'full', 'natal', 7), /not included/);
assert.match(meanings.placement('Moon', {sign: 'Unknown'}, 'natal')[0].text, /not included/);
assert.match(meanings.placement('Unknown', {sign: 'Aries'}, 'natal')[0].text, /not included/);

console.log('PASS: 108 distinct rashi placements, 27 nakshatras with four padas, 12 bhavas, nine grahas, node conventions, horoscope boundaries, directional drishti, and fallbacks.');
