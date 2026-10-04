// Canvas-operation regression for the reusable share-card compositor.
// These hashes were captured after operation-for-operation comparison with the
// original renderer extracted from oracle.js; the test itself is Git-independent.
const assert = require('node:assert/strict');
const crypto = require('node:crypto');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const source = fs.readFileSync(path.resolve(__dirname, '../static/share-card.js'), 'utf8');
const title = 'THREE-CARD TAROT';
const quote = 'The present opens a path toward courage, clarity, and renewal.';
const expectedHashes = {
  'story-wide-manual': '5949645c931ab799ebb86ab904b0ba60163874edc0490cf8b7dfa2546f99e3b5',
  'story-tall-manual': 'a486003c6461c64ef08fbfb65d6247626c62dd4610bc4b36c7805eb63bed835f',
  'post-wide-manual': '59c02e536ac8191cd4b928c02c3a249ae635ed08320e17af6d954cdf7ed17771',
  'post-tall-manual': 'b3d4319580755f31199823d7c2abf8182cde77d0022a31aac990e14bbc453270',
  'story-wide-native': 'd8936b8bbcfda152061b0ca8d61d0916b6126056f1960ec98b6dcf811ccccec7',
  'story-tall-native': '30f72869c1228818f8cc7cccd5a3556c5b7baf470ba766c4eb83234bc1fbeb64',
  'post-wide-native': '5299661b589de7d4801910c54de4946edc765cee2ae15c178999457072a6d313',
  'post-tall-native': 'e2b2cfb00643d6be22eb016df7befc644227cb48fe76c0610a2896ea93746532'
};

function normalize(value) {
  return value && typeof value === 'object' && value._traceId ? value._traceId : value;
}

function createHarness(hasLetterSpacing) {
  const trace = [];
  const fontLoads = [];
  let canvasId = 0;
  let gradientId = 0;

  function createGradient() {
    const id = `gradient-${++gradientId}`;
    return {
      _traceId: id,
      addColorStop(...args) { trace.push([`${id}.addColorStop`, ...args]); }
    };
  }

  function createContext(id) {
    const state = hasLetterSpacing ? {letterSpacing: '0px'} : {};
    const methods = new Set([
      'save', 'restore', 'fillRect', 'drawImage', 'beginPath', 'moveTo', 'lineTo',
      'arcTo', 'closePath', 'fill', 'clip', 'stroke', 'translate', 'scale', 'fillText'
    ]);
    return new Proxy(state, {
      has(target, property) { return Reflect.has(target, property); },
      get(target, property) {
        if (property === 'measureText') {
          return text => {
            const size = Number.parseFloat(String(target.font || '16px').match(/\d+(?:\.\d+)?(?=px)/)?.[0] || '16');
            return {width: [...String(text)].length * size * 0.53};
          };
        }
        if (property === 'createRadialGradient' || property === 'createLinearGradient') {
          return (...args) => {
            const gradient = createGradient();
            trace.push([`${id}.${String(property)}`, ...args, gradient._traceId]);
            return gradient;
          };
        }
        if (methods.has(property)) {
          return (...args) => trace.push([`${id}.${String(property)}`, ...args.map(normalize)]);
        }
        return target[property];
      },
      set(target, property, value) {
        target[property] = value;
        trace.push([`${id}.set`, String(property), normalize(value)]);
        return true;
      }
    });
  }

  function createCanvas(label) {
    const id = label || `canvas-${++canvasId}`;
    const context = createContext(`${id}.ctx`);
    return {
      _traceId: id,
      getContext(type) {
        assert.equal(type, '2d');
        trace.push([`${id}.getContext`, type]);
        return context;
      },
      set width(value) { this._width = value; trace.push([`${id}.set`, 'width', value]); },
      get width() { return this._width; },
      set height(value) { this._height = value; trace.push([`${id}.set`, 'height', value]); },
      get height() { return this._height; }
    };
  }

  const document = {
    fonts: {load(value) { fontLoads.push(value); return Promise.resolve(value); }},
    createElement(tag) {
      assert.equal(tag, 'canvas');
      return createCanvas();
    }
  };
  const context = vm.createContext({document, window: {}, Math, Promise});
  vm.runInContext(source, context, {filename: 'share-card.js'});
  return {api: context.window.OracleShareCard, createCanvas, fontLoads, trace};
}

async function main() {
  const fontHarness = createHarness(false);
  assert.deepEqual(Object.keys(fontHarness.api).sort(), ['compose', 'ensureFonts', 'formats']);
  assert.deepEqual(JSON.parse(JSON.stringify(fontHarness.api.formats)), {
    story: {w: 1080, h: 1920, label: '1080 × 1920 · PNG'},
    post: {w: 1080, h: 1080, label: '1080 × 1080 · PNG'}
  });
  await Promise.all([fontHarness.api.ensureFonts(), fontHarness.api.ensureFonts()]);
  assert.deepEqual(fontHarness.fontLoads, ['700 48px "Cormorant Garamond"', '600 24px Cinzel']);

  for (const hasLetterSpacing of [false, true]) {
    for (const format of ['story', 'post']) {
      for (const [shape, content] of Object.entries({
        wide: {x: 11, y: 17, w: 900, h: 420},
        tall: {x: 5, y: 7, w: 320, h: 760}
      })) {
        const harness = createHarness(hasLetterSpacing);
        const snapshotCanvas = harness.createCanvas('snapshot');
        harness.trace.length = 0;
        const canvas = harness.api.compose({
          format,
          title,
          quote,
          snapshot: {canvas: snapshotCanvas, content}
        });

        assert.equal(canvas.width, 1080);
        assert.equal(canvas.height, format === 'story' ? 1920 : 1080);
        const drawnText = harness.trace.filter(entry => entry[0].endsWith('.fillText')).map(entry => entry[1]);
        const combinedText = drawnText.join('');
        assert.ok(hasLetterSpacing ? drawnText.includes(title) : combinedText.includes(title));
        assert.ok(hasLetterSpacing ? drawnText.includes('— THE QUANTUM ORACLE') : combinedText.includes('— THE QUANTUM ORACLE'));
        assert.ok(hasLetterSpacing ? drawnText.includes('qoracle.app') : combinedText.includes('qoracle.app'));
        assert.ok(combinedText.replace(/\s+/g, '').includes(quote.replace(/\s+/g, '')));

        const mode = hasLetterSpacing ? 'native' : 'manual';
        const key = `${format}-${shape}-${mode}`;
        const hash = crypto.createHash('sha256').update(JSON.stringify(harness.trace)).digest('hex');
        assert.equal(hash, expectedHashes[key], `canvas operation trace changed for ${key}`);
      }
    }
  }
  console.log('PASS: shared share-card API and 8 canvas layout/font traces match the extracted renderer baseline.');
}

main().catch(error => {
  console.error(error);
  process.exitCode = 1;
});
