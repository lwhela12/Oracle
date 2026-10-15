// The Sanctum: a prototype 3D entry. Every object and texture is generated here
// (no downloads beyond the card faces); the look follows the owner's mood board:
// candlelit darkness, warm natural materials, and a cosmic blue-magenta numbers altar.
// Choosing an altar hands off to the existing reading flow at /#read/<tradition>.
import * as THREE from 'three';
import { EffectComposer } from 'three/addons/postprocessing/EffectComposer.js';
import { RenderPass } from 'three/addons/postprocessing/RenderPass.js';
import { UnrealBloomPass } from 'three/addons/postprocessing/UnrealBloomPass.js';
import { OutputPass } from 'three/addons/postprocessing/OutputPass.js';

const PARAMS = new URLSearchParams(location.search);
const REDUCED = matchMedia('(prefers-reduced-motion: reduce)').matches;
const TAU = Math.PI * 2;
const RING = 4.4; // distance of each altar from the singularity
const HOLD_MS = 1100;
const ALTARS = {
    tarot: { name: 'Tarot', tagline: 'Find perspective in the cards', angle: 0, verb: 'Hold to draw', labelY: 2.0, lookY: .6 },
    iching: { name: 'I Ching', tagline: 'Navigate the nature of change', angle: Math.PI / 2, verb: 'Hold to cast', labelY: 2.7, lookY: .7 },
    number: { name: 'Numbers', tagline: 'Discover meaning in a number', angle: Math.PI, verb: 'Hold to draw', labelY: 3.65, lookY: 1.5 },
    runes: { name: 'Runes', tagline: 'Listen to the wisdom of symbols', angle: -Math.PI / 2, verb: 'Hold to cast', labelY: 2.85, lookY: .7 },
};

// Elder Futhark drawn as straight strokes in a unit box (x, y downward), so no font is needed.
const RUNES = {
    fehu: [[.3, 0, .3, 1], [.3, .35, .75, .05], [.3, .6, .75, .3]],
    uruz: [[.3, 1, .3, 0], [.3, 0, .72, .35], [.72, .35, .72, 1]],
    thurisaz: [[.3, 0, .3, 1], [.3, .28, .68, .5], [.68, .5, .3, .72]],
    ansuz: [[.3, 0, .3, 1], [.3, .05, .72, .35], [.3, .35, .72, .65]],
    raidho: [[.3, 0, .3, 1], [.3, 0, .7, .25], [.7, .25, .3, .5], [.3, .5, .72, 1]],
    kenaz: [[.68, .1, .3, .5], [.3, .5, .68, .9]],
    gebo: [[.2, 0, .8, 1], [.8, 0, .2, 1]],
    wunjo: [[.3, 0, .3, 1], [.3, 0, .7, .25], [.7, .25, .3, .5]],
    hagalaz: [[.25, 0, .25, 1], [.75, 0, .75, 1], [.25, .35, .75, .65]],
    nauthiz: [[.5, 0, .5, 1], [.25, .35, .75, .65]],
    isa: [[.5, 0, .5, 1]],
    jera: [[.45, .1, .2, .35], [.2, .35, .45, .6], [.55, .4, .8, .65], [.8, .65, .55, .9]],
    eihwaz: [[.5, 0, .5, 1], [.5, 0, .76, .2], [.5, 1, .24, .8]],
    perthro: [[.3, 0, .3, 1], [.3, 0, .7, .25], [.3, 1, .7, .75]],
    algiz: [[.5, 0, .5, 1], [.5, .45, .2, 0], [.5, .45, .8, 0]],
    sowilo: [[.7, 0, .3, .35], [.3, .35, .7, .65], [.7, .65, .3, 1]],
    tiwaz: [[.5, 0, .5, 1], [.5, 0, .2, .3], [.5, 0, .8, .3]],
    berkano: [[.3, 0, .3, 1], [.3, 0, .7, .25], [.7, .25, .3, .5], [.3, .5, .7, .75], [.7, .75, .3, 1]],
    ehwaz: [[.25, 0, .25, 1], [.75, 0, .75, 1], [.25, 0, .5, .35], [.5, .35, .75, 0]],
    mannaz: [[.25, 0, .25, 1], [.75, 0, .75, 1], [.25, 0, .75, .4], [.75, 0, .25, .4]],
    laguz: [[.3, 0, .3, 1], [.3, 0, .7, .3]],
    ingwaz: [[.5, .1, .78, .5], [.78, .5, .5, .9], [.5, .9, .22, .5], [.22, .5, .5, .1]],
    dagaz: [[.2, 0, .2, 1], [.8, 0, .8, 1], [.2, 0, .8, 1], [.8, 0, .2, 1]],
    othala: [[.5, 0, .8, .35], [.8, .35, .5, .7], [.5, .7, .2, .35], [.2, .35, .5, 0], [.5, .7, .18, 1], [.5, .7, .82, 1]],
};
const RUNE_NAMES = Object.keys(RUNES);

function webglAvailable() {
    try {
        const probe = document.createElement('canvas');
        return Boolean(probe.getContext('webgl2') || probe.getContext('webgl'));
    } catch {
        return false;
    }
}

function seeded(seed) {
    return () => {
        seed |= 0; seed = seed + 0x6D2B79F5 | 0;
        let t = Math.imul(seed ^ seed >>> 15, 1 | seed);
        t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t;
        return ((t ^ t >>> 14) >>> 0) / 4294967296;
    };
}

// Shared corners move together so rough stone stays closed.
function roughen(geometry, amount, seed) {
    const rand = seeded(seed);
    const position = geometry.attributes.position;
    const offsets = new Map();
    for (let i = 0; i < position.count; i++) {
        const key = `${position.getX(i).toFixed(3)},${position.getY(i).toFixed(3)},${position.getZ(i).toFixed(3)}`;
        if (!offsets.has(key)) offsets.set(key, [(rand() - .5) * amount, (rand() - .5) * amount, (rand() - .5) * amount]);
        const [dx, dy, dz] = offsets.get(key);
        position.setXYZ(i, position.getX(i) + dx, position.getY(i) + dy, position.getZ(i) + dz);
    }
    geometry.computeVertexNormals();
    return geometry;
}

function canvasTexture(width, height, draw, { repeat = false, color = true } = {}) {
    const canvas = document.createElement('canvas');
    canvas.width = width;
    canvas.height = height;
    draw(canvas.getContext('2d'), width, height);
    const texture = new THREE.CanvasTexture(canvas);
    if (color) texture.colorSpace = THREE.SRGBColorSpace;
    if (repeat) texture.wrapS = texture.wrapT = THREE.RepeatWrapping;
    return texture;
}

function glowTexture(inner, outer) {
    return canvasTexture(128, 128, (ctx, s) => {
        const g = ctx.createRadialGradient(s / 2, s / 2, 0, s / 2, s / 2, s / 2);
        g.addColorStop(0, inner);
        g.addColorStop(1, outer);
        ctx.fillStyle = g;
        ctx.fillRect(0, 0, s, s);
    });
}

function drawRune(ctx, strokes, x, y, size, width) {
    ctx.lineWidth = width;
    ctx.lineCap = 'round';
    ctx.beginPath();
    for (const [x1, y1, x2, y2] of strokes) {
        ctx.moveTo(x + x1 * size * .7 + size * .15, y + y1 * size);
        ctx.lineTo(x + x2 * size * .7 + size * .15, y + y2 * size);
    }
    ctx.stroke();
}

function woodTexture(base, grain, highlight, seed) {
    return canvasTexture(512, 512, (ctx, s) => {
        const rand = seeded(seed);
        ctx.fillStyle = base;
        ctx.fillRect(0, 0, s, s);
        for (let i = 0; i < 170; i++) {
            const y0 = rand() * s, amp = 1 + rand() * 5, freq = .004 + rand() * .018, phase = rand() * TAU;
            ctx.strokeStyle = rand() < .6 ? grain : highlight;
            ctx.globalAlpha = .06 + rand() * .22;
            ctx.lineWidth = .5 + rand() * 2.4;
            ctx.beginPath();
            for (let x = 0; x <= s; x += 8) {
                const y = y0 + Math.sin(x * freq + phase) * amp + Math.sin(x * .05 + i) * .6;
                if (x === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y);
            }
            ctx.stroke();
        }
        for (let k = 0; k < 2; k++) {
            const kx = rand() * s, ky = rand() * s;
            for (let r = 3; r < 26; r += 3) {
                ctx.globalAlpha = .12;
                ctx.strokeStyle = grain;
                ctx.beginPath(); ctx.ellipse(kx, ky, r * 2.4, r * .7, 0, 0, TAU); ctx.stroke();
            }
        }
        ctx.globalAlpha = 1;
    }, { repeat: true });
}

function linenTexture(base, thread) {
    return canvasTexture(256, 256, (ctx, s) => {
        const rand = seeded(5);
        ctx.fillStyle = base;
        ctx.fillRect(0, 0, s, s);
        for (let i = 0; i < s; i += 3) {
            ctx.globalAlpha = .18 + rand() * .25;
            ctx.fillStyle = thread;
            ctx.fillRect(0, i, s, 1);
            ctx.globalAlpha = .12 + rand() * .2;
            ctx.fillRect(i, 0, 1, s);
        }
        ctx.globalAlpha = 1;
    }, { repeat: true });
}

// A black runner printed in cream: rune borders, a stave circle, three linked triangles and a tree.
function runnerTexture() {
    return canvasTexture(512, 1024, (ctx, w, h) => {
        const rand = seeded(17);
        const cream = '#e9dcc0';
        ctx.fillStyle = '#121014';
        ctx.fillRect(0, 0, w, h);
        ctx.strokeStyle = cream;
        ctx.lineWidth = 3; ctx.strokeRect(14, 14, w - 28, h - 28);
        ctx.lineWidth = 1.5; ctx.strokeRect(24, 24, w - 48, h - 48);
        for (let y = 44, i = 0; y < h - 60; y += 34, i++) {
            drawRune(ctx, RUNES[RUNE_NAMES[i % 24]], 30, y, 26, 2.4);
            drawRune(ctx, RUNES[RUNE_NAMES[(i + 9) % 24]], w - 58, y, 26, 2.4);
        }
        const cx = w / 2;
        // Stave circle.
        ctx.lineWidth = 2.5;
        ctx.beginPath(); ctx.arc(cx, 200, 120, 0, TAU); ctx.stroke();
        ctx.lineWidth = 1.2;
        ctx.beginPath(); ctx.arc(cx, 200, 108, 0, TAU); ctx.stroke();
        for (let i = 0; i < 8; i++) {
            const a = i / 8 * TAU, ex = cx + Math.cos(a) * 92, ey = 200 + Math.sin(a) * 92;
            ctx.lineWidth = 3;
            ctx.beginPath(); ctx.moveTo(cx, 200); ctx.lineTo(ex, ey); ctx.stroke();
            ctx.lineWidth = 2;
            const px = -Math.sin(a) * 12, py = Math.cos(a) * 12;
            ctx.beginPath(); ctx.moveTo(ex - px, ey - py); ctx.lineTo(ex + px, ey + py); ctx.stroke();
            const mx = cx + Math.cos(a) * 55, my = 200 + Math.sin(a) * 55;
            ctx.beginPath(); ctx.arc(mx, my, 5, 0, TAU); ctx.stroke();
        }
        // Three linked triangles.
        ctx.lineWidth = 3;
        for (let i = 0; i < 3; i++) {
            const ox = cx + (i - 1) * 26, oy = 470 + (i === 1 ? -22 : 0);
            ctx.beginPath(); ctx.moveTo(ox, oy - 50); ctx.lineTo(ox + 46, oy + 30); ctx.lineTo(ox - 46, oy + 30); ctx.closePath(); ctx.stroke();
        }
        // Tree: branches up, roots down.
        const branch = (x, y, angle, length, depth) => {
            if (depth === 0) return;
            const x2 = x + Math.cos(angle) * length, y2 = y + Math.sin(angle) * length;
            ctx.lineWidth = depth * 1.2;
            ctx.beginPath(); ctx.moveTo(x, y); ctx.lineTo(x2, y2); ctx.stroke();
            branch(x2, y2, angle - .45 - rand() * .2, length * .72, depth - 1);
            branch(x2, y2, angle + .45 + rand() * .2, length * .72, depth - 1);
        };
        ctx.beginPath(); ctx.arc(cx, 760, 150, 0, TAU); ctx.lineWidth = 2; ctx.stroke();
        ctx.lineWidth = 7; ctx.beginPath(); ctx.moveTo(cx, 830); ctx.lineTo(cx, 740); ctx.stroke();
        branch(cx, 740, -Math.PI / 2, 52, 6);
        branch(cx, 830, Math.PI / 2 - .5, 28, 4);
        branch(cx, 830, Math.PI / 2 + .5, 28, 4);
        // Worn print: speckle the ink.
        ctx.globalCompositeOperation = 'destination-out';
        for (let i = 0; i < 2600; i++) { ctx.globalAlpha = rand() * .5; ctx.fillRect(rand() * w, rand() * h, 2, 2); }
        ctx.globalCompositeOperation = 'source-over';
        ctx.globalAlpha = 1;
        ctx.fillStyle = 'rgba(18,16,20,1)';
        ctx.globalCompositeOperation = 'destination-over';
        ctx.fillRect(0, 0, w, h);
        ctx.globalCompositeOperation = 'source-over';
    });
}

function sliceTexture() {
    return canvasTexture(512, 512, (ctx, s) => {
        const rand = seeded(23), c = s / 2;
        ctx.fillStyle = '#4a3220';
        ctx.fillRect(0, 0, s, s);
        const g = ctx.createRadialGradient(c, c, 0, c, c, c * .92);
        g.addColorStop(0, '#d9b98d'); g.addColorStop(.85, '#c49a6a'); g.addColorStop(1, '#8a6040');
        ctx.fillStyle = g;
        ctx.beginPath(); ctx.arc(c, c, c * .92, 0, TAU); ctx.fill();
        ctx.strokeStyle = '#8c6440';
        for (let r = 6; r < c * .9; r += 5 + rand() * 6) {
            ctx.globalAlpha = .25 + rand() * .3; ctx.lineWidth = .6 + rand();
            ctx.beginPath();
            for (let a = 0; a <= TAU + .01; a += .05) {
                const rr = r + Math.sin(a * 3 + r) * 1.4 + Math.sin(a * 7) * .6;
                const x = c + Math.cos(a) * rr, y = c + Math.sin(a) * rr;
                if (a === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y);
            }
            ctx.stroke();
        }
        ctx.globalAlpha = .35; ctx.lineWidth = 1;
        for (let i = 0; i < 9; i++) { const a = rand() * TAU; ctx.beginPath(); ctx.moveTo(c, c); ctx.lineTo(c + Math.cos(a) * c * .8, c + Math.sin(a) * c * .8); ctx.stroke(); }
        ctx.globalAlpha = 1;
    });
}

function pageTexture(hexagrams) {
    return canvasTexture(384, 512, (ctx, w, h) => {
        const rand = seeded(hexagrams.length * 31);
        const g = ctx.createRadialGradient(w / 2, h / 2, 40, w / 2, h / 2, w * .8);
        g.addColorStop(0, '#efe3c6'); g.addColorStop(1, '#cdb88f');
        ctx.fillStyle = g;
        ctx.fillRect(0, 0, w, h);
        for (let i = 0; i < 900; i++) { ctx.fillStyle = `rgba(120,90,50,${rand() * .08})`; ctx.fillRect(rand() * w, rand() * h, 2, 2); }
        ctx.fillStyle = '#2a221c';
        hexagrams.forEach((lines, k) => {
            const ox = hexagrams.length === 1 ? w / 2 : w / 2 + (k - .5) * 160, top = 120;
            lines.forEach((solid, i) => {
                const y = top + i * 46, half = hexagrams.length === 1 ? 110 : 66;
                if (solid) ctx.fillRect(ox - half, y, half * 2, 18);
                else { ctx.fillRect(ox - half, y, half * .8, 18); ctx.fillRect(ox + half * .2, y, half * .8, 18); }
            });
        });
    });
}

function coinTexture() {
    return canvasTexture(256, 256, (ctx, s) => {
        const rand = seeded(41), c = s / 2;
        const g = ctx.createRadialGradient(c * .8, c * .8, 10, c, c, c);
        g.addColorStop(0, '#a98552'); g.addColorStop(1, '#6b5230');
        ctx.fillStyle = g;
        ctx.fillRect(0, 0, s, s);
        for (let i = 0; i < 500; i++) { ctx.fillStyle = `rgba(70,110,85,${rand() * .35})`; ctx.beginPath(); ctx.arc(rand() * s, rand() * s, rand() * 4, 0, TAU); ctx.fill(); }
        ctx.strokeStyle = '#4a3820'; ctx.lineWidth = 8;
        ctx.beginPath(); ctx.arc(c, c, c - 8, 0, TAU); ctx.stroke();
        ctx.lineWidth = 3; ctx.beginPath(); ctx.arc(c, c, c * .55, 0, TAU); ctx.stroke();
        ctx.strokeStyle = '#c9a36a'; ctx.lineWidth = 6;
        for (const [dx, dy] of [[0, -1], [1, 0], [0, 1], [-1, 0]]) {
            ctx.beginPath(); ctx.moveTo(c + dx * 44 - dy * 10, c + dy * 44 - dx * 10); ctx.lineTo(c + dx * 70 + dy * 10, c + dy * 70 + dx * 10); ctx.stroke();
        }
        ctx.fillStyle = '#100a06';
        ctx.fillRect(c - 22, c - 22, 44, 44);
        ctx.strokeStyle = '#5a4428'; ctx.lineWidth = 5; ctx.strokeRect(c - 26, c - 26, 52, 52);
    });
}

function zodiacTexture() {
    const signs = ['Aries', 'Taurus', 'Gemini', 'Cancer', 'Leo', 'Virgo', 'Libra', 'Scorpio', 'Sagittarius', 'Capricorn', 'Aquarius', 'Pisces'];
    return canvasTexture(1024, 1024, (ctx, s) => {
        const rand = seeded(77), c = s / 2;
        ctx.strokeStyle = 'rgba(225,215,255,.75)';
        for (const [r, width] of [[500, 3], [488, 1], [420, 2], [300, 2], [290, 1], [150, 2]]) {
            ctx.lineWidth = width; ctx.beginPath(); ctx.arc(c, c, r, 0, TAU); ctx.stroke();
        }
        ctx.lineWidth = 1.2;
        for (let i = 0; i < 12; i++) {
            const a = i / 12 * TAU;
            ctx.beginPath(); ctx.moveTo(c + Math.cos(a) * 150, c + Math.sin(a) * 150); ctx.lineTo(c + Math.cos(a) * 488, c + Math.sin(a) * 488); ctx.stroke();
        }
        for (let i = 0; i < 120; i++) {
            const a = i / 120 * TAU, inner = i % 10 === 0 ? 470 : 480;
            ctx.beginPath(); ctx.moveTo(c + Math.cos(a) * inner, c + Math.sin(a) * inner); ctx.lineTo(c + Math.cos(a) * 488, c + Math.sin(a) * 488); ctx.stroke();
        }
        ctx.fillStyle = 'rgba(235,228,255,.9)';
        ctx.font = 'italic 30px "Cormorant Garamond", Georgia, serif';
        ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
        signs.forEach((sign, i) => {
            const a = (i + .5) / 12 * TAU;
            ctx.save(); ctx.translate(c + Math.cos(a) * 455, c + Math.sin(a) * 455); ctx.rotate(a + Math.PI / 2);
            ctx.fillText(sign, 0, 0); ctx.restore();
        });
        // A stick-figure constellation in each house.
        for (let i = 0; i < 12; i++) {
            const a0 = i / 12 * TAU, points = [];
            for (let k = 0; k < 4 + Math.floor(rand() * 3); k++) {
                const a = a0 + (.12 + rand() * .3) * (TAU / 12) / .55, r = 315 + rand() * 90;
                points.push([c + Math.cos(a) * r, c + Math.sin(a) * r]);
            }
            ctx.strokeStyle = 'rgba(225,215,255,.55)'; ctx.lineWidth = 1.5;
            ctx.beginPath(); points.forEach(([x, y], k) => (k ? ctx.lineTo(x, y) : ctx.moveTo(x, y))); ctx.stroke();
            ctx.fillStyle = '#ffffff';
            for (const [x, y] of points) { ctx.beginPath(); ctx.arc(x, y, 3 + rand() * 3, 0, TAU); ctx.fill(); }
        }
        // Rosette at the centre.
        ctx.strokeStyle = 'rgba(225,215,255,.6)'; ctx.lineWidth = 1.2;
        for (let i = 0; i < 12; i++) { const a = i / 12 * TAU; ctx.beginPath(); ctx.arc(c + Math.cos(a) * 70, c + Math.sin(a) * 70, 70, 0, TAU); ctx.stroke(); }
    }, { color: true });
}

function flareTexture() {
    return canvasTexture(128, 128, (ctx, s) => {
        const c = s / 2;
        const g = ctx.createRadialGradient(c, c, 0, c, c, c * .5);
        g.addColorStop(0, 'rgba(255,255,255,1)'); g.addColorStop(.25, 'rgba(220,200,255,.55)'); g.addColorStop(1, 'rgba(160,120,255,0)');
        ctx.fillStyle = g; ctx.fillRect(0, 0, s, s);
        for (const [w, hgt] of [[s, 3], [3, s]]) {
            const lg = ctx.createLinearGradient(c - w / 2, c - hgt / 2, c + w / 2, c + hgt / 2);
            lg.addColorStop(0, 'rgba(255,255,255,0)'); lg.addColorStop(.5, 'rgba(255,255,255,1)'); lg.addColorStop(1, 'rgba(255,255,255,0)');
            ctx.fillStyle = lg; ctx.fillRect(c - w / 2, c - hgt / 2, w, hgt);
        }
    });
}

function runeDecalTexture(name) {
    return canvasTexture(128, 128, (ctx, s) => {
        ctx.strokeStyle = '#f3cf7a';
        ctx.shadowColor = 'rgba(255,200,110,.9)'; ctx.shadowBlur = 6;
        drawRune(ctx, RUNES[name], 22, 18, 92, 9);
    });
}

const FLAME_VERTEX = 'varying vec2 vUv; void main(){ vUv = uv; gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0); }';
const FLAME_FRAGMENT = `uniform float uTime; uniform float uSeed; varying vec2 vUv;
    void main(){
        float t = uTime + uSeed;
        float sway = (sin(t * 7.0) * 0.5 + sin(t * 13.0 + 1.3) * 0.3) * 0.08 * vUv.y * vUv.y;
        float x = (vUv.x - 0.5 - sway) * 2.0;
        float y = vUv.y;
        float width = sin(clamp(y, 0.0, 1.0) * 3.14159) * (1.0 - 0.55 * y) + 0.001;
        width *= 0.92 + 0.08 * sin(t * 17.0);
        float d = abs(x) / width;
        float body = smoothstep(1.0, 0.3, d) * smoothstep(0.0, 0.1, y) * smoothstep(1.0, 0.55, y);
        float core = smoothstep(0.65, 0.0, d) * smoothstep(0.8, 0.15, y);
        vec3 color = mix(vec3(1.0, 0.38, 0.06), vec3(1.0, 0.9, 0.62), core);
        color += vec3(0.25, 0.3, 0.9) * smoothstep(0.18, 0.0, y) * smoothstep(1.0, 0.3, d) * 0.5;
        gl_FragColor = vec4(color * body * 3.4, body);
    }`;

function start() {
    const canvas = document.getElementById('scene');
    const renderer = new THREE.WebGLRenderer({ canvas, antialias: true, powerPreference: 'high-performance' });
    let pixelRatio = Math.min(window.devicePixelRatio || 1, 1.75);
    renderer.setPixelRatio(pixelRatio);
    renderer.toneMapping = THREE.ACESFilmicToneMapping;
    renderer.toneMappingExposure = 1.1;

    const scene = new THREE.Scene();
    scene.fog = new THREE.FogExp2(0x0a0812, 0.028);
    const camera = new THREE.PerspectiveCamera(55, 1, 0.1, 200);
    const maxAnisotropy = renderer.capabilities.getMaxAnisotropy();
    const loader = new THREE.TextureLoader();
    const load = url => {
        const texture = loader.load(url);
        texture.colorSpace = THREE.SRGBColorSpace;
        texture.anisotropy = maxAnisotropy;
        return texture;
    };
    const animated = []; // per-frame callbacks (time, dt)

    // Bloom makes flames and glyphs glow; it is dropped automatically on slow devices.
    const composer = new EffectComposer(renderer);
    composer.addPass(new RenderPass(scene, camera));
    const bloom = new UnrealBloomPass(new THREE.Vector2(256, 256), .6, .5, .9);
    composer.addPass(bloom);
    composer.addPass(new OutputPass());
    let bloomOn = PARAMS.get('quality') !== 'low';
    // Hand-written shaders pick colours by eye in display space; the bloom path is linear, so convert there.
    const linearOutput = { value: 1 };

    // Sky dome: violet at the horizon, near-black overhead.
    const skyMaterial = new THREE.ShaderMaterial({
        side: THREE.BackSide, depthWrite: false, uniforms: { uLinear: linearOutput },
        vertexShader: 'varying vec3 vDir; void main(){ vDir = normalize(position); gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0); }',
        fragmentShader: `uniform float uLinear; varying vec3 vDir;
            void main(){
                float h = vDir.y;
                vec3 top = vec3(0.012, 0.01, 0.028);
                vec3 horizon = vec3(0.1, 0.06, 0.17);
                vec3 low = vec3(0.02, 0.016, 0.035);
                vec3 color = h > 0.0 ? mix(horizon, top, pow(h, 0.5)) : mix(horizon, low, pow(-h, 0.35));
                gl_FragColor = vec4(uLinear > 0.5 ? pow(color, vec3(2.2)) * 1.6 : color, 1.0);
            }`,
    });
    scene.add(new THREE.Mesh(new THREE.SphereGeometry(90, 32, 16), skyMaterial));

    // A soft environment so metal reads as metal without an HDR download.
    const envScene = new THREE.Scene();
    envScene.add(new THREE.Mesh(new THREE.SphereGeometry(10, 16, 8), skyMaterial));
    for (const [x, y, z, color] of [[6, 4, 2, 0xffc98a], [-5, 3, -4, 0x9f7bff], [0, 6, -6, 0xffe2b8]]) {
        const panel = new THREE.Mesh(new THREE.PlaneGeometry(4, 2), new THREE.MeshBasicMaterial({ color, side: THREE.DoubleSide }));
        panel.position.set(x, y, z);
        panel.lookAt(0, 0, 0);
        envScene.add(panel);
    }
    const pmrem = new THREE.PMREMGenerator(renderer);
    scene.environment = pmrem.fromScene(envScene, 0.04).texture;
    pmrem.dispose();

    // Stars, constellations and a few cross-shaped flares in the dome.
    const starDome = new THREE.Group();
    scene.add(starDome);
    const starSprite = glowTexture('rgba(255,255,255,1)', 'rgba(255,255,255,0)');
    const flare = flareTexture();
    const starRand = seeded(7);
    const starCount = 2400;
    const starPositions = new Float32Array(starCount * 3);
    const starColors = new Float32Array(starCount * 3);
    const palette = [new THREE.Color(0xf2eee6), new THREE.Color(0xf1d492), new THREE.Color(0xc7b8db)];
    for (let i = 0; i < starCount; i++) {
        const theta = starRand() * TAU;
        const y = 1 - starRand() * 1.12;
        const r = Math.sqrt(1 - y * y);
        starPositions.set([Math.cos(theta) * r * 80, y * 80, Math.sin(theta) * r * 80], i * 3);
        const color = palette[starRand() < .8 ? 0 : starRand() < .5 ? 1 : 2].clone().multiplyScalar(.35 + starRand() ** 2 * .9);
        starColors.set([color.r, color.g, color.b], i * 3);
    }
    const starGeometry = new THREE.BufferGeometry();
    starGeometry.setAttribute('position', new THREE.BufferAttribute(starPositions, 3));
    starGeometry.setAttribute('color', new THREE.BufferAttribute(starColors, 3));
    starDome.add(new THREE.Points(starGeometry, new THREE.PointsMaterial({
        size: 0.55, map: starSprite, vertexColors: true, transparent: true, depthWrite: false,
        blending: THREE.AdditiveBlending, fog: false,
    })));
    const toSky = (azimuth, elevation, distance = 78) => {
        const a = THREE.MathUtils.degToRad(azimuth), e = THREE.MathUtils.degToRad(elevation);
        return new THREE.Vector3(Math.sin(a) * Math.cos(e) * distance, Math.sin(e) * distance, -Math.cos(a) * Math.cos(e) * distance);
    };
    const constellations = [
        [[-18, 34], [-10, 40], [-2, 37], [6, 44], [13, 41]],
        [[38, 22], [44, 30], [52, 27], [49, 19], [38, 22]],
        [[-58, 26], [-50, 33], [-44, 29], [-40, 37]],
        [[150, 30], [160, 38], [170, 33], [178, 41]],
    ];
    const linePoints = [];
    const brightPoints = [];
    for (const shape of constellations) {
        const points = shape.map(([az, el]) => toSky(az, el));
        brightPoints.push(...points);
        for (let i = 0; i < points.length - 1; i++) linePoints.push(points[i], points[i + 1]);
    }
    starDome.add(new THREE.LineSegments(new THREE.BufferGeometry().setFromPoints(linePoints),
        new THREE.LineBasicMaterial({ color: 0xc7b8db, transparent: true, opacity: .28, fog: false })));
    starDome.add(new THREE.Points(new THREE.BufferGeometry().setFromPoints(brightPoints), new THREE.PointsMaterial({
        size: 1.6, map: starSprite, color: 0xf1d492, transparent: true, depthWrite: false, blending: THREE.AdditiveBlending, fog: false,
    })));
    const skyFlares = [];
    for (let i = 0; i < 9; i++) {
        const sprite = new THREE.Sprite(new THREE.SpriteMaterial({ map: flare, color: 0xd8c8ff, blending: THREE.AdditiveBlending, depthWrite: false, fog: false, transparent: true }));
        sprite.position.copy(toSky(starRand() * 360, 8 + starRand() * 50, 70));
        const size = 2.5 + starRand() * 3;
        sprite.scale.set(size, size, 1);
        sprite.userData = { size, phase: starRand() * TAU };
        starDome.add(sprite);
        skyFlares.push(sprite);
    }
    animated.push((time, dt) => {
        if (REDUCED) return;
        starDome.rotation.y += dt * .004;
        for (const sprite of skyFlares) {
            const s = sprite.userData.size * (.75 + .25 * Math.sin(time * 1.3 + sprite.userData.phase));
            sprite.scale.set(s, s, 1);
        }
    });

    // The chamber floor: an inscribed disc, kept dark so candlelight pools on it.
    const floorTexture = canvasTexture(1024, 1024, (ctx, s) => {
        const c = s / 2;
        const base = ctx.createRadialGradient(c, c, 0, c, c, c);
        base.addColorStop(0, '#221a33');
        base.addColorStop(.55, '#140f1e');
        base.addColorStop(1, '#09080d');
        ctx.fillStyle = base;
        ctx.fillRect(0, 0, s, s);
        const scale = c / 10;
        ctx.strokeStyle = 'rgba(212,183,124,.5)';
        for (const [r, w, dash] of [[9.6, 3, []], [9.2, 1, []], [6.2, 2, [6, 10]], [2.4, 2, []], [2.0, 1, [2, 8]]]) {
            ctx.setLineDash(dash); ctx.lineWidth = w;
            ctx.beginPath(); ctx.arc(c, c, r * scale, 0, TAU); ctx.stroke();
        }
        ctx.setLineDash([]);
        for (let i = 0; i < 72; i++) {
            const a = i / 72 * TAU, long = i % 6 === 0;
            ctx.lineWidth = long ? 2 : 1;
            ctx.beginPath();
            ctx.moveTo(c + Math.cos(a) * 9.2 * scale, c + Math.sin(a) * 9.2 * scale);
            ctx.lineTo(c + Math.cos(a) * (long ? 8.5 : 8.9) * scale, c + Math.sin(a) * (long ? 8.5 : 8.9) * scale);
            ctx.stroke();
        }
        ctx.strokeStyle = 'rgba(212,183,124,.2)'; ctx.lineWidth = 1.5;
        for (const altar of Object.values(ALTARS)) {
            const x = c + Math.sin(altar.angle) * RING * scale, y = c + Math.cos(altar.angle) * RING * scale;
            ctx.beginPath(); ctx.moveTo(c + Math.sin(altar.angle) * 2.4 * scale, c + Math.cos(altar.angle) * 2.4 * scale); ctx.lineTo(x, y); ctx.stroke();
            ctx.beginPath(); ctx.arc(x, y, 1.6 * scale, 0, TAU); ctx.stroke();
        }
    });
    floorTexture.anisotropy = maxAnisotropy;
    const floor = new THREE.Mesh(new THREE.CircleGeometry(10, 128), new THREE.MeshStandardMaterial({
        map: floorTexture, emissiveMap: floorTexture, emissive: 0xffffff, emissiveIntensity: .12, roughness: .75, metalness: .15,
    }));
    floor.rotation.x = -Math.PI / 2;
    scene.add(floor);
    scene.add(new THREE.HemisphereLight(0x7a68b0, 0x0e0a14, 0.32));

    const material = {
        darkWood: new THREE.MeshStandardMaterial({ map: woodTexture('#2a1a12', '#120a06', '#4a3020', 3), roughness: .55 }),
        rusticWood: new THREE.MeshStandardMaterial({ map: woodTexture('#5a3a22', '#2a180c', '#7a5434', 9), roughness: .7 }),
        honeyWood: new THREE.MeshStandardMaterial({ map: woodTexture('#8a5c34', '#4e2f16', '#b07c4c', 13), roughness: .6 }),
        stone: new THREE.MeshStandardMaterial({ color: 0x4a4552, roughness: 1, flatShading: true }),
        darkStone: new THREE.MeshStandardMaterial({ color: 0x2c2832, roughness: 1, flatShading: true }),
        gold: new THREE.MeshStandardMaterial({ color: 0xd9b56a, metalness: 1, roughness: .3 }),
        bronze: new THREE.MeshStandardMaterial({ color: 0x8a6a40, metalness: .85, roughness: .45 }),
        blackMetal: new THREE.MeshStandardMaterial({ color: 0x1a1816, metalness: .7, roughness: .5 }),
        silver: new THREE.MeshStandardMaterial({ color: 0xc8c8cc, metalness: 1, roughness: .35 }),
        wax: new THREE.MeshStandardMaterial({ color: 0xf2e6cc, roughness: .6, emissive: 0x3a2008, emissiveIntensity: .4 }),
        redWax: new THREE.MeshStandardMaterial({ color: 0x8a1210, roughness: .55, emissive: 0x3a0604, emissiveIntensity: .25 }),
        amethyst: new THREE.MeshPhysicalMaterial({ color: 0x7b55c2, roughness: .16, clearcoat: 1, clearcoatRoughness: .08, emissive: 0x2a1250, emissiveIntensity: .7, iridescence: .3 }),
        quartz: new THREE.MeshPhysicalMaterial({ color: 0xece6e0, roughness: .35, clearcoat: .6 }),
        obsidian: new THREE.MeshPhysicalMaterial({ color: 0x0e0c12, roughness: .08, clearcoat: 1 }),
        velvet: new THREE.MeshPhysicalMaterial({ color: 0x150c1e, roughness: .9, sheen: 1, sheenColor: new THREE.Color(0x7a4a9e), sheenRoughness: .45 }),
        copper: new THREE.MeshStandardMaterial({ color: 0x7a4128, metalness: .9, roughness: .4 }),
        ceramic: new THREE.MeshPhysicalMaterial({ color: 0xe6ddcc, roughness: .3, clearcoat: .8 }),
        redSilk: new THREE.MeshPhysicalMaterial({ color: 0x9e1418, roughness: .5, sheen: .6, sheenColor: new THREE.Color(0xff6060) }),
    };
    const shadowTexture = glowTexture('rgba(0,0,0,.75)', 'rgba(0,0,0,0)');
    const mesh = (geometry, mat, x = 0, y = 0, z = 0) => {
        const m = new THREE.Mesh(geometry, mat);
        m.position.set(x, y, z);
        return m;
    };
    const contactShadow = (group, width, depth, y = .006) => {
        const shadow = mesh(new THREE.PlaneGeometry(width, depth), new THREE.MeshBasicMaterial({ map: shadowTexture, transparent: true, depthWrite: false }), 0, y, 0);
        shadow.rotation.x = -Math.PI / 2;
        group.add(shadow);
    };

    // Flames are billboards drawn by a noise shader; the glow comes from bloom plus a small halo.
    const flameGeometry = new THREE.PlaneGeometry(1, 1).translate(0, .5, 0);
    const flameMaterial = new THREE.ShaderMaterial({
        uniforms: { uTime: { value: 0 }, uSeed: { value: 0 } }, vertexShader: FLAME_VERTEX, fragmentShader: FLAME_FRAGMENT,
        transparent: true, depthWrite: false, blending: THREE.AdditiveBlending, side: THREE.DoubleSide,
    });
    const haloTexture = glowTexture('rgba(255,190,110,.9)', 'rgba(255,140,60,0)');
    const flames = [];
    const halos = [];
    const addFlame = (group, x, y, z, size) => {
        const flameMesh = new THREE.Mesh(flameGeometry, flameMaterial.clone());
        flameMesh.material.uniforms.uSeed.value = Math.random() * 100;
        flameMesh.scale.set(size * .42, size, 1);
        flameMesh.position.set(x, y, z);
        group.add(flameMesh);
        flames.push(flameMesh);
        const halo = new THREE.Sprite(new THREE.SpriteMaterial({ map: haloTexture, blending: THREE.AdditiveBlending, depthWrite: false, transparent: true, opacity: .22 }));
        halo.scale.set(size * 4.5, size * 4.5, 1);
        halo.position.set(x, y + size * .4, z);
        group.add(halo);
        halos.push(halo);
    };
    const candle = (group, x, z, baseY, radius, height, wax = material.wax, flameSize = .1) => {
        group.add(mesh(new THREE.CylinderGeometry(radius, radius * 1.04, height, 24), wax, x, baseY + height / 2, z));
        addFlame(group, x, baseY + height + .005, z, flameSize);
    };
    const teaLight = (group, x, z, baseY) => {
        group.add(mesh(new THREE.CylinderGeometry(.06, .06, .03, 20, 1, true), material.silver, x, baseY + .015, z));
        group.add(mesh(new THREE.CylinderGeometry(.056, .056, .022, 20), material.wax, x, baseY + .012, z));
        addFlame(group, x, baseY + .026, z, .07);
    };
    const flicker = (light, base, seed) => animated.push(time => {
        light.intensity = REDUCED ? base : base * (.88 + .12 * Math.sin(time * 9 + seed) * Math.sin(time * 3.7 + seed * 2));
    });
    const pointLight = (group, color, intensity, x, y, z, seed) => {
        const light = new THREE.PointLight(color, intensity, 0, 2);
        light.position.set(x, y, z);
        group.add(light);
        if (seed !== undefined) flicker(light, intensity, seed);
        return light;
    };
    const altarGroups = {};
    const place = (id, group) => {
        const { angle } = ALTARS[id];
        group.position.set(Math.sin(angle) * RING, 0, Math.cos(angle) * RING);
        group.rotation.y = angle; // local +z faces outward, toward a camera standing at this angle
        group.userData.altar = id;
        altarGroups[id] = group;
        scene.add(group);
    };
    const table = (group, wood, width, depth, height, legRadius) => {
        group.add(mesh(new THREE.BoxGeometry(width, .08, depth), wood, 0, height - .04, 0));
        group.add(mesh(new THREE.BoxGeometry(width - .2, .14, depth - .2), wood, 0, height - .15, 0));
        for (const [sx, sz] of [[-1, -1], [1, -1], [-1, 1], [1, 1]]) {
            group.add(mesh(new THREE.CylinderGeometry(legRadius, legRadius * .8, height - .08, 12), wood, sx * (width / 2 - .14), (height - .08) / 2, sz * (depth / 2 - .14)));
        }
        contactShadow(group, width + .9, depth + .9);
    };

    // Tarot: a dark table, a red pillar candle on a wood slice, tea lights, crystals, three cards face up.
    const tarot = new THREE.Group();
    const TAROT_TOP = 1.0;
    table(tarot, material.darkWood, 2.3, 1.3, TAROT_TOP, .05);
    tarot.add(mesh(new THREE.BoxGeometry(1.95, .01, 1.05), material.velvet, 0, TAROT_TOP + .005, 0));
    const slice = new THREE.Mesh(new THREE.CylinderGeometry(.4, .42, .06, 48), [
        new THREE.MeshStandardMaterial({ color: 0x4a3020, roughness: 1 }),
        new THREE.MeshStandardMaterial({ map: sliceTexture(), roughness: .8 }),
        new THREE.MeshStandardMaterial({ color: 0x3a2618, roughness: 1 }),
    ]);
    slice.position.set(-.05, TAROT_TOP + .04, -.22);
    tarot.add(slice);
    candle(tarot, -.05, -.24, TAROT_TOP + .07, .12, .4, material.redWax, .14);
    for (let i = 0; i < 5; i++) {
        const shard = mesh(new THREE.ConeGeometry(.035 + i % 2 * .012, .16 + i % 3 * .04, 6), material.amethyst, .26 + (i - 2) * .035, TAROT_TOP + .14, -.12 + (i % 2) * .05);
        shard.rotation.set((i - 2) * .22, i, (i - 2) * -.18);
        tarot.add(shard);
    }
    tarot.add(mesh(new THREE.SphereGeometry(.06, 24, 16), material.obsidian, .2, TAROT_TOP + .13, -.36));
    const quartz = mesh(new THREE.SphereGeometry(.07, 20, 14), material.quartz, -.42, TAROT_TOP + .04, .0);
    quartz.scale.set(1, .6, .8);
    tarot.add(quartz);
    const point = mesh(new THREE.BoxGeometry(.05, .05, .24), material.quartz, -.4, TAROT_TOP + .07, -.32);
    point.rotation.y = .6;
    tarot.add(point);
    for (const [x, z] of [[-.95, .42], [.95, .42], [-.92, -.42], [.9, -.4]]) teaLight(tarot, x, z, TAROT_TOP + .01);
    const cardNames = ['the-hanged-man', 'the-high-priestess', 'the-sun'];
    const cards = cardNames.map((name, i) => {
        const card = mesh(new THREE.PlaneGeometry(.3, .5), new THREE.MeshStandardMaterial({ map: load(`/static/cards/tarot/${name}.webp`), roughness: .55 }), (i - 1) * .4, TAROT_TOP + .014, .3);
        card.rotation.set(-Math.PI / 2, 0, (i - 1) * -.1);
        card.userData.rest = card.position.clone();
        tarot.add(card);
        return card;
    });
    const cardBack = new THREE.MeshStandardMaterial({ map: load('/static/cards/tarot/card-back.webp'), roughness: .5 });
    const edge = new THREE.MeshStandardMaterial({ color: 0xe8dcc3, roughness: .8 });
    const deck = new THREE.Mesh(new THREE.BoxGeometry(.3, .08, .5), [edge, edge, cardBack, edge, edge, edge]);
    deck.position.set(.72, TAROT_TOP + .05, -.08);
    deck.rotation.y = .3;
    tarot.add(deck);
    pointLight(tarot, 0xff7a36, 2.6, -.05, TAROT_TOP + .7, -.2, 1);
    pointLight(tarot, 0xffa860, 1.6, 0, TAROT_TOP + .3, .45, 2);
    place('tarot', tarot);

    // Runes: a rustic table, a black printed runner, amethyst rune stones on linen, a lantern, tea lights.
    const runes = new THREE.Group();
    const RUNE_TOP = .9;
    table(runes, material.rusticWood, 2.2, 1.2, RUNE_TOP, .07);
    const runner = mesh(new THREE.PlaneGeometry(.62, 1.24), new THREE.MeshStandardMaterial({ map: runnerTexture(), roughness: .95 }), -.42, RUNE_TOP + .003, 0);
    runner.rotation.x = -Math.PI / 2;
    runes.add(runner);
    const linen = mesh(new THREE.PlaneGeometry(.78, .64), new THREE.MeshStandardMaterial({ map: linenTexture('#9a8a70', '#5e5242'), roughness: 1 }), .38, RUNE_TOP + .004, .08);
    linen.rotation.set(-Math.PI / 2, 0, .12);
    runes.add(linen);
    const stoneRand = seeded(31);
    const stoneGeometry = new THREE.SphereGeometry(.07, 20, 12);
    for (let i = 0; i < 9; i++) {
        const sx = .38 + (i % 3 - 1) * .21 + (stoneRand() - .5) * .05, sz = .08 + (Math.floor(i / 3) - 1) * .17 + (stoneRand() - .5) * .04;
        const stone = mesh(stoneGeometry, material.amethyst, sx, RUNE_TOP + .022, sz);
        stone.scale.set(1, .42, .74);
        stone.rotation.y = stoneRand() * TAU;
        runes.add(stone);
        const glyph = mesh(new THREE.PlaneGeometry(.085, .085), new THREE.MeshBasicMaterial({
            map: runeDecalTexture(RUNE_NAMES[(i * 5) % 24]), transparent: true, depthWrite: false, color: new THREE.Color(1.6, 1.4, 1.1),
        }), sx, RUNE_TOP + .052, sz);
        glyph.rotation.set(-Math.PI / 2, 0, stone.rotation.y * .2);
        runes.add(glyph);
    }
    // Lantern.
    const lantern = new THREE.Group();
    for (const [x, z] of [[-1, -1], [1, -1], [-1, 1], [1, 1]]) lantern.add(mesh(new THREE.BoxGeometry(.018, .34, .018), material.blackMetal, x * .1, .19, z * .1));
    lantern.add(mesh(new THREE.BoxGeometry(.24, .025, .24), material.blackMetal, 0, .012, 0));
    lantern.add(mesh(new THREE.ConeGeometry(.17, .12, 4), material.blackMetal, 0, .42, 0).rotateY(Math.PI / 4));
    const handle = mesh(new THREE.TorusGeometry(.05, .008, 8, 24), material.blackMetal, 0, .52, 0);
    lantern.add(handle);
    const glass = new THREE.MeshBasicMaterial({ color: 0xffd9a0, transparent: true, opacity: .07, depthWrite: false, blending: THREE.AdditiveBlending, side: THREE.DoubleSide });
    for (let i = 0; i < 4; i++) {
        const pane = mesh(new THREE.PlaneGeometry(.2, .32), glass, Math.sin(i * Math.PI / 2) * .1, .19, Math.cos(i * Math.PI / 2) * .1);
        pane.rotation.y = i * Math.PI / 2;
        lantern.add(pane);
    }
    candle(lantern, 0, 0, .025, .045, .14, material.wax, .08);
    lantern.position.set(-.82, RUNE_TOP, -.38);
    runes.add(lantern);
    // Copper bowl of herbs.
    const bowlProfile = [[0, 0], [.08, 0], [.13, .03], [.16, .08], [.165, .1], [.155, .1], [.15, .08], [.12, .04], [0, .035]].map(([x, y]) => new THREE.Vector2(x, y));
    runes.add(mesh(new THREE.LatheGeometry(bowlProfile, 32), material.copper, .78, RUNE_TOP, -.38));
    runes.add(mesh(new THREE.CircleGeometry(.14, 24), new THREE.MeshStandardMaterial({ color: 0x3a3a22, roughness: 1 }), .78, RUNE_TOP + .075, -.38).rotateX(-Math.PI / 2));
    for (const [x, z] of [[-.85, .45], [-.05, .5], [.4, .5], [.85, .42]]) teaLight(runes, x, z, RUNE_TOP);
    const leftStone = mesh(roughen(new THREE.BoxGeometry(.52, 2.5, .38, 2, 6, 2), .14, 11), material.stone, -1.45, 1.25, -.78);
    leftStone.rotation.z = .05;
    const rightStone = mesh(roughen(new THREE.BoxGeometry(.46, 2.1, .36, 2, 5, 2), .14, 13), material.stone, 1.5, 1.05, -.8);
    rightStone.rotation.z = -.07;
    runes.add(leftStone, rightStone);
    pointLight(runes, 0xffa050, 3.4, -.82, RUNE_TOP + .35, -.38, 3);
    pointLight(runes, 0xffb070, 1.8, .1, RUNE_TOP + .35, .5, 4);
    place('runes', runes);

    // I Ching: honey wood in a shaft of golden light; coins on red cord, yarrow stalks, an open book, tea.
    const iching = new THREE.Group();
    const ICHING_TOP = .8;
    table(iching, material.honeyWood, 2.0, 1.1, ICHING_TOP, .06);
    const pageGeometry = side => {
        const geometry = new THREE.PlaneGeometry(.44, .6, 16, 1);
        geometry.rotateX(-Math.PI / 2);
        const position = geometry.attributes.position;
        for (let i = 0; i < position.count; i++) {
            const u = (position.getX(i) + .22) / .44; // 0 at spine for the right page
            const fromSpine = side > 0 ? u : 1 - u;
            position.setY(i, Math.sin(fromSpine * Math.PI * .9) * .035 + fromSpine * .01);
        }
        geometry.translate(side * .22, 0, 0);
        geometry.computeVertexNormals();
        return geometry;
    };
    const book = new THREE.Group();
    book.add(mesh(new THREE.BoxGeometry(.96, .025, .66), new THREE.MeshStandardMaterial({ color: 0x3a2214, roughness: .7 }), 0, .012, 0));
    book.add(mesh(pageGeometry(-1), new THREE.MeshStandardMaterial({ map: pageTexture([[1, 1, 1, 0, 0, 1]]), roughness: .9, side: THREE.DoubleSide }), 0, .028, 0));
    book.add(mesh(pageGeometry(1), new THREE.MeshStandardMaterial({ map: pageTexture([[0, 1, 0, 1, 1, 1], [1, 0, 1, 1, 0, 0]]), roughness: .9, side: THREE.DoubleSide }), 0, .028, 0));
    book.position.set(.3, ICHING_TOP, .12);
    book.rotation.y = -.12;
    iching.add(book);
    const coinFace = new THREE.MeshStandardMaterial({ map: coinTexture(), metalness: .75, roughness: .5 });
    const coinPositions = [[-.66, .32, .2], [-.52, .4, -.3], [-.42, .27, .9], [-.58, .18, 1.6]];
    for (const [x, z, spin] of coinPositions) {
        const coin = new THREE.Mesh(new THREE.CylinderGeometry(.075, .075, .012, 40), [material.bronze, coinFace, coinFace]);
        coin.position.set(x, ICHING_TOP + .01, z);
        coin.rotation.set(spin * .05, spin, 0);
        iching.add(coin);
    }
    const cordCurve = new THREE.CatmullRomCurve3([[-.3, .21], [-.42, .27], [-.52, .4], [-.66, .32], [-.58, .18], [-.7, .08], [-.82, .02]].map(([x, z], i) => new THREE.Vector3(x, ICHING_TOP + .022 + (i % 2) * .006, z)));
    iching.add(new THREE.Mesh(new THREE.TubeGeometry(cordCurve, 64, .009, 6), material.redSilk));
    iching.add(mesh(new THREE.SphereGeometry(.025, 12, 8), material.redSilk, -.82, ICHING_TOP + .025, .02));
    const tassel = mesh(new THREE.ConeGeometry(.032, .16, 12), material.redSilk, -.91, ICHING_TOP + .018, -.04);
    tassel.rotation.set(0, 0, Math.PI / 2 - .2);
    iching.add(tassel);
    const stalkCount = 40;
    const stalks = new THREE.InstancedMesh(new THREE.CylinderGeometry(.0055, .0055, .86, 5), new THREE.MeshStandardMaterial({ color: 0xc9a46a, roughness: .7 }), stalkCount);
    const stalkMatrix = new THREE.Matrix4();
    const stalkRand = seeded(53);
    for (let i = 0; i < stalkCount; i++) {
        const a = stalkRand() * TAU, r = Math.sqrt(stalkRand()) * .04;
        stalkMatrix.makeRotationZ(Math.PI / 2 + (stalkRand() - .5) * .04).setPosition(.05 + (stalkRand() - .5) * .04, ICHING_TOP + .045 + Math.sin(a) * r, -.33 + Math.cos(a) * r);
        stalks.setMatrixAt(i, stalkMatrix);
    }
    iching.add(stalks);
    const tie = mesh(new THREE.TorusGeometry(.047, .009, 8, 24), new THREE.MeshStandardMaterial({ color: 0x4a2a6a, roughness: .6 }), .05, ICHING_TOP + .045, -.33);
    tie.rotation.y = Math.PI / 2;
    iching.add(tie);
    const cupProfile = [[0, 0], [.04, 0], [.045, .01], [.075, .05], [.085, .1], [.08, .1], [.07, .055], [.035, .015], [0, .015]].map(([x, y]) => new THREE.Vector2(x, y));
    iching.add(mesh(new THREE.LatheGeometry(cupProfile, 32), material.ceramic, -.62, ICHING_TOP, -.28));
    iching.add(mesh(new THREE.CircleGeometry(.074, 24), new THREE.MeshPhysicalMaterial({ color: 0x5a2a0a, roughness: .05, clearcoat: 1 }), -.62, ICHING_TOP + .085, -.28).rotateX(-Math.PI / 2));
    iching.add(mesh(roughen(new THREE.DodecahedronGeometry(.13, 1), .04, 61), material.darkStone, .82, ICHING_TOP + .09, -.36));
    const hexagram = new THREE.Group();
    const lineGlow = new THREE.MeshBasicMaterial({ color: new THREE.Color(1.0, .82, .5), transparent: true, opacity: .55 });
    [1, 0, 1, 1, 0, 1].forEach((solid, i) => {
        const y = i * .1;
        if (solid) hexagram.add(mesh(new THREE.BoxGeometry(.5, .03, .02), lineGlow, 0, y, 0));
        else for (const x of [-.15, .15]) hexagram.add(mesh(new THREE.BoxGeometry(.2, .03, .02), lineGlow, x, y, 0));
    });
    hexagram.position.set(0, 1.85, -.1);
    hexagram.scale.setScalar(.8);
    iching.add(hexagram);
    animated.push(time => { if (!REDUCED) hexagram.position.y = 1.85 + Math.sin(time * 1.1) * .05; });
    const sun = new THREE.SpotLight(0xffb55c, 42, 0, .5, .7, 2);
    sun.position.set(1.4, 3.6, -1.4);
    sun.target.position.set(0, ICHING_TOP, 0);
    iching.add(sun, sun.target);
    const shaftLength = Math.hypot(1.4, 3.6 - ICHING_TOP, 1.4);
    const shaft = mesh(new THREE.CylinderGeometry(.18, .85, shaftLength, 24, 1, true), new THREE.ShaderMaterial({
        uniforms: { uColor: { value: new THREE.Color(1.0, .72, .38) }, uStrength: { value: .42 } },
        vertexShader: `varying vec2 vUv; varying float vFacing;
            void main(){
                vUv = uv;
                vec4 mv = modelViewMatrix * vec4(position, 1.0);
                vFacing = abs(dot(normalize(normalMatrix * normal), normalize(-mv.xyz)));
                gl_Position = projectionMatrix * mv;
            }`,
        fragmentShader: `uniform vec3 uColor; uniform float uStrength; varying vec2 vUv; varying float vFacing;
            void main(){
                float along = smoothstep(0.0, 0.3, vUv.y) * smoothstep(1.0, 0.55, vUv.y);
                float a = along * pow(vFacing, 2.0) * uStrength;
                gl_FragColor = vec4(uColor * a, a);
            }`,
        transparent: true, depthWrite: false, blending: THREE.AdditiveBlending,
    }), .7, (3.6 + ICHING_TOP) / 2, -.7);
    shaft.lookAt(new THREE.Vector3(1.4, 3.6, -1.4));
    shaft.rotateX(Math.PI / 2);
    iching.add(shaft);
    candle(iching, .78, .36, ICHING_TOP, .04, .16, material.wax, .08);
    place('iching', iching);

    // Numbers: a glowing zodiac wheel around an armillary sphere, numerals and star flares in orbit.
    const number = new THREE.Group();
    number.add(mesh(new THREE.CylinderGeometry(.5, .56, .16, 32), material.darkStone, 0, .08, 0));
    number.add(mesh(new THREE.CylinderGeometry(.12, .2, 1.05, 24), material.gold, 0, .68, 0));
    contactShadow(number, 1.8, 1.8);
    const wheelCenter = 2.15;
    const wheel = mesh(new THREE.CircleGeometry(1.15, 96), new THREE.MeshBasicMaterial({
        map: zodiacTexture(), transparent: true, depthWrite: false, blending: THREE.AdditiveBlending,
        color: new THREE.Color(.75, .85, 1.7), side: THREE.DoubleSide,
    }), 0, wheelCenter, -.05);
    number.add(wheel);
    const armillary = new THREE.Group();
    const ringGeometry = new THREE.TorusGeometry(.42, .014, 10, 96);
    for (const [rx, ry, rz] of [[Math.PI / 2, 0, 0], [0, 0, 0], [0, Math.PI / 2, 0], [Math.PI / 2, 0, .41]]) {
        const ring = new THREE.Mesh(ringGeometry, material.gold);
        ring.rotation.set(rx, ry, rz);
        armillary.add(ring);
    }
    armillary.add(mesh(new THREE.SphereGeometry(.07, 24, 12), new THREE.MeshBasicMaterial({ color: new THREE.Color(2, 1.9, 2.6) })));
    armillary.position.set(0, wheelCenter, .15);
    number.add(armillary);
    const numerals = [];
    const numeralValues = [1, 2, 3, 4, 5, 6, 7, 8, 9, 11, 2, 7, 8, 5, 6, 11];
    const makeNumerals = () => {
        const textures = new Map();
        numeralValues.forEach((n, i) => {
            if (!textures.has(n)) {
                textures.set(n, canvasTexture(128, 128, (ctx, s) => {
                    ctx.fillStyle = '#ffffff';
                    ctx.font = '400 74px "Cormorant Garamond", Georgia, serif';
                    ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
                    ctx.shadowColor = 'rgba(190,170,255,.9)'; ctx.shadowBlur = 14;
                    ctx.fillText(String(n), s / 2, s / 2 + 4);
                }));
            }
            const sprite = new THREE.Sprite(new THREE.SpriteMaterial({ map: textures.get(n), transparent: true, depthWrite: false, color: new THREE.Color(1.5, 1.4, 1.9) }));
            const size = .22 + (i % 4) * .08;
            sprite.scale.set(size, size, 1);
            sprite.userData = { phase: i / numeralValues.length * TAU, radius: 1.35 + (i % 3) * .25, tilt: (i % 5 - 2) * .25 };
            number.add(sprite);
            numerals.push(sprite);
        });
    };
    Promise.race([document.fonts.load('400 74px "Cormorant Garamond"'), new Promise(resolve => setTimeout(resolve, 1200))]).catch(() => {}).then(makeNumerals);
    const altarFlares = [];
    const flareRand = seeded(88);
    for (let i = 0; i < 7; i++) {
        const sprite = new THREE.Sprite(new THREE.SpriteMaterial({ map: flare, color: new THREE.Color(1.4, 1.2, 2.2), blending: THREE.AdditiveBlending, depthWrite: false, transparent: true }));
        sprite.position.set((flareRand() - .5) * 3, 1.2 + flareRand() * 2.4, (flareRand() - .5) * 1.2);
        const size = .35 + flareRand() * .45;
        sprite.userData = { size, phase: flareRand() * TAU };
        number.add(sprite);
        altarFlares.push(sprite);
    }
    pointLight(number, 0x3a5bff, 6, -.8, 1.6, .6);
    pointLight(number, 0xd04fd0, 4, .8, 2.4, .5);
    animated.push((time, dt) => {
        if (!REDUCED) {
            wheel.rotation.z -= dt * .05;
            armillary.rotation.y += dt * .25;
            armillary.rotation.x = Math.sin(time * .2) * .15;
        }
        for (const sprite of numerals) {
            const { phase, radius, tilt } = sprite.userData;
            const a = phase + (REDUCED ? 0 : time * .12);
            sprite.position.set(Math.cos(a) * radius, wheelCenter + Math.sin(a) * radius * .55 + tilt * .4, Math.sin(a * 2) * .35);
        }
        for (const sprite of altarFlares) {
            const s = sprite.userData.size * (REDUCED ? 1 : .6 + .4 * Math.sin(time * 1.7 + sprite.userData.phase));
            sprite.scale.set(s, s, 1);
        }
    });
    place('number', number);

    // The singularity: let the Oracle choose.
    const singularity = new THREE.Group();
    singularity.position.set(0, 1.75, 0);
    singularity.userData.altar = 'oracle';
    scene.add(singularity);
    const facing = new THREE.Group(); // parts that always face the viewer
    singularity.add(facing);
    facing.add(new THREE.Mesh(new THREE.SphereGeometry(.42, 48, 24), new THREE.MeshBasicMaterial({ color: 0x000000 })));
    facing.add(new THREE.Mesh(new THREE.TorusGeometry(.46, .016, 12, 128), new THREE.MeshBasicMaterial({ color: new THREE.Color(1.15, .98, .74) })));
    const haloMaterial = new THREE.SpriteMaterial({ map: glowTexture('rgba(171,140,230,.8)', 'rgba(109,79,176,0)'), blending: THREE.AdditiveBlending, depthWrite: false });
    const voidHalo = new THREE.Sprite(haloMaterial);
    voidHalo.scale.set(3.3, 3.3, 1); // small enough that the floor never clips it
    voidHalo.position.z = -.6; // behind the core, in the camera-facing frame
    facing.add(voidHalo);
    const diskUniforms = { uTime: { value: 0 }, uPower: { value: 1 }, uLinear: linearOutput };
    const disk = new THREE.Mesh(new THREE.RingGeometry(.58, 1.75, 160, 1), new THREE.ShaderMaterial({
        uniforms: diskUniforms, transparent: true, depthWrite: false, side: THREE.DoubleSide, blending: THREE.AdditiveBlending,
        vertexShader: 'varying vec2 vPos; void main(){ vPos = position.xy; gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0); }',
        fragmentShader: `uniform float uTime; uniform float uPower; uniform float uLinear; varying vec2 vPos;
            void main(){
                float r = length(vPos);
                float t = (r - 0.58) / 1.17;
                float a = atan(vPos.y, vPos.x);
                float band = smoothstep(0.0, 0.06, t) * (1.0 - smoothstep(0.35, 1.0, t));
                float swirl = 0.5 + 0.5 * sin(a * 3.0 - r * 7.0 + uTime * 1.7 * uPower);
                float fine = 0.5 + 0.5 * sin(a * 11.0 + r * 19.0 - uTime * 2.3 * uPower);
                float beaming = 0.75 + 0.45 * sin(a);
                vec3 hot = vec3(1.0, 0.86, 0.6);
                vec3 cool = vec3(0.55, 0.38, 0.95);
                vec3 color = mix(hot, cool, smoothstep(0.0, 0.8, t));
                if (uLinear > 0.5) color = pow(color, vec3(2.2));
                float alpha = band * (0.35 + 0.45 * swirl + 0.2 * fine) * uPower * beaming;
                gl_FragColor = vec4(color * alpha * 1.3, alpha);
            }`,
    }));
    disk.rotation.x = -Math.PI / 2 + .3;
    singularity.add(disk);
    const spiralCount = 420;
    const spiralRand = seeded(99);
    const spiral = Array.from({ length: spiralCount }, () => ({ r: .6 + spiralRand() * 2.8, a: spiralRand() * TAU, y: (spiralRand() - .5) * .12 }));
    const spiralPositions = new Float32Array(spiralCount * 3);
    const spiralGeometry = new THREE.BufferGeometry();
    spiralGeometry.setAttribute('position', new THREE.BufferAttribute(spiralPositions, 3));
    const spiralPoints = new THREE.Points(spiralGeometry, new THREE.PointsMaterial({
        size: .06, map: starSprite, color: 0xf3dcab, transparent: true, depthWrite: false, blending: THREE.AdditiveBlending,
    }));
    spiralPoints.rotation.x = .3;
    singularity.add(spiralPoints);
    const voidLight = new THREE.PointLight(0x9f7bff, 7, 0, 2);
    singularity.add(voidLight);
    let power = 1;
    let targetPower = 1;
    animated.push((time, dt) => {
        power += (targetPower - power) * Math.min(1, dt * 2.5);
        diskUniforms.uTime.value = time;
        diskUniforms.uPower.value = power;
        haloMaterial.opacity = Math.min(1, .6 * power);
        voidLight.intensity = 7 * power;
        facing.quaternion.copy(camera.quaternion);
        for (let i = 0; i < spiralCount; i++) {
            const p = spiral[i];
            if (!REDUCED) {
                p.a += dt * (1.3 * power) / p.r;
                p.r -= dt * .22 * power / p.r;
                if (p.r < .5) { p.r = 3.3; p.a = spiralRand() * TAU; }
            }
            spiralPositions.set([Math.cos(p.a) * p.r, p.y, Math.sin(p.a) * p.r], i * 3);
        }
        spiralGeometry.attributes.position.needsUpdate = true;
    });

    // Dust drifting through the candlelight.
    const dustCount = 320;
    const dustRand = seeded(123);
    const dust = Array.from({ length: dustCount }, () => ({ a: dustRand() * TAU, r: 1.5 + dustRand() * 7, y: .2 + dustRand() * 3.2, speed: .2 + dustRand() * .5 }));
    const dustPositions = new Float32Array(dustCount * 3);
    const dustGeometry = new THREE.BufferGeometry();
    dustGeometry.setAttribute('position', new THREE.BufferAttribute(dustPositions, 3));
    scene.add(new THREE.Points(dustGeometry, new THREE.PointsMaterial({
        size: .035, map: starSprite, color: 0xffd8a0, transparent: true, opacity: .55, depthWrite: false, blending: THREE.AdditiveBlending,
    })));
    animated.push((time, dt) => {
        for (let i = 0; i < dustCount; i++) {
            const p = dust[i];
            if (!REDUCED) { p.a += dt * .015 * p.speed; p.y += Math.sin(time * p.speed + i) * dt * .02; }
            dustPositions.set([Math.cos(p.a) * p.r, p.y, Math.sin(p.a) * p.r], i * 3);
        }
        dustGeometry.attributes.position.needsUpdate = true;
    });

    // Flames turn to face the viewer around their vertical axis, so they live in world space.
    scene.updateMatrixWorld(true);
    for (const flameMesh of flames) scene.attach(flameMesh);
    animated.push(time => {
        for (const flameMesh of flames) {
            flameMesh.material.uniforms.uTime.value = time;
            flameMesh.rotation.set(0, Math.atan2(camera.position.x - flameMesh.position.x, camera.position.z - flameMesh.position.z), 0);
        }
    });

    // Camera: orbit the ring, glide to an altar to approach it.
    const look = new THREE.Vector3(0, .9, 0);
    const lookTarget = look.clone();
    let theta = 0, thetaTarget = 0;
    let orbitRadius = 11, orbitHeight = 4.3;
    let radius = REDUCED ? 11 : 19, radiusTarget = 11;
    let height = REDUCED ? 4.3 : 10, heightTarget = 4.3;
    let mode = 'chamber';
    let current = 'tarot';

    function resize() {
        const width = window.innerWidth, h = window.innerHeight;
        renderer.setSize(width, h, false);
        composer.setPixelRatio(pixelRatio);
        composer.setSize(width, h);
        camera.aspect = width / h;
        const wanted = THREE.MathUtils.radToDeg(2 * Math.atan(Math.tan(THREE.MathUtils.degToRad(27)) / camera.aspect));
        camera.fov = THREE.MathUtils.clamp(wanted, 50, 72);
        camera.updateProjectionMatrix();
        const halfWidth = Math.atan(Math.tan(THREE.MathUtils.degToRad(camera.fov / 2)) * camera.aspect);
        orbitRadius = THREE.MathUtils.clamp(.68 * RING / Math.tan(halfWidth), 8.6, 11.5);
        orbitHeight = orbitRadius * .42;
        if (mode !== 'approach') { radiusTarget = orbitRadius; heightTarget = orbitHeight; }
    }
    window.addEventListener('resize', resize);
    resize();

    function setLowQuality() {
        bloomOn = false;
        linearOutput.value = 0;
        pixelRatio = 1;
        renderer.setPixelRatio(pixelRatio);
        resize();
        for (const halo of halos) halo.material.opacity = .7;
    }
    if (!bloomOn) setLowQuality();

    const nearestAngle = (target, from) => target + Math.round((from - target) / TAU) * TAU;
    const facingAltar = () => {
        let best = 'tarot', distance = Infinity;
        for (const [id, altar] of Object.entries(ALTARS)) {
            const d = Math.abs(nearestAngle(altar.angle, theta) - theta);
            if (d < distance) { distance = d; best = id; }
        }
        return best;
    };

    // Labels are real buttons placed over the scene. They sit above an altar and slide to its
    // front edge as it turns toward the viewer, so the nearest label never covers the singularity.
    const labels = Object.fromEntries([...document.querySelectorAll('.altar-label')].map(el => [el.dataset.altar, el]));
    const above = new THREE.Vector3(), below = new THREE.Vector3();
    const labelAnchor = id => {
        if (id === 'oracle') return new THREE.Vector3(0, .35, 0);
        const position = altarGroups[id].position;
        const frontness = (position.x * Math.sin(theta) + position.z * Math.cos(theta)) / RING;
        above.copy(position).setY(ALTARS[id].labelY);
        below.copy(position).multiplyScalar(1 + 1.25 / RING).setY(0);
        return above.lerp(below, THREE.MathUtils.smoothstep(frontness, .35, .9));
    };
    const projected = new THREE.Vector3();
    function placeLabels() {
        const show = mode === 'chamber';
        const facingId = facingAltar();
        const width = window.innerWidth, h = window.innerHeight;
        for (const [id, el] of Object.entries(labels)) {
            projected.copy(labelAnchor(id)).project(camera);
            const visible = show && projected.z < 1;
            el.dataset.hidden = String(!visible);
            el.tabIndex = visible ? 0 : -1;
            el.classList.toggle('facing', id === facingId);
            const x = Math.round(THREE.MathUtils.clamp((projected.x + 1) / 2 * width, 64, width - 64));
            const y = Math.round(THREE.MathUtils.clamp((1 - projected.y) / 2 * h, 70, h - 60));
            el.style.transform = `translate(${x}px, ${y}px) translate(-50%, -50%)`;
        }
    }

    const approachPanel = document.getElementById('approach');
    const hint = document.getElementById('hint');
    const toast = document.getElementById('toast');
    let toastTimer;
    function showToast(text, ms = 2600) {
        toast.textContent = text;
        toast.classList.add('visible');
        clearTimeout(toastTimer);
        if (ms) toastTimer = setTimeout(() => toast.classList.remove('visible'), ms);
    }

    function approach(id, explicitTheta) {
        mode = 'approach';
        current = id;
        const altar = ALTARS[id];
        thetaTarget = explicitTheta ?? nearestAngle(altar.angle, theta);
        const portrait = camera.aspect < 1;
        radiusTarget = RING + (portrait ? 4.2 : 3.4);
        heightTarget = portrait ? 3.4 : 2.9;
        lookTarget.copy(altarGroups[id].position).setY(altar.lookY);
        document.getElementById('approach-title').textContent = altar.name;
        document.getElementById('approach-tagline').textContent = altar.tagline;
        document.getElementById('hold-text').textContent = altar.verb;
        approachPanel.hidden = false;
        hint.style.opacity = 0;
        document.getElementById('approach-title').focus({ preventScroll: true });
    }

    function returnToChamber() {
        mode = 'chamber';
        thetaTarget = nearestAngle(ALTARS[current].angle, theta);
        radiusTarget = orbitRadius;
        heightTarget = orbitHeight;
        lookTarget.set(0, .9, 0);
        approachPanel.hidden = true;
        hint.style.opacity = 1;
        resetHold();
        labels[current].focus({ preventScroll: true });
    }

    async function letTheOracleChoose() {
        if (mode === 'choosing') return;
        mode = 'choosing';
        hint.style.opacity = 0;
        targetPower = 2.6;
        showToast('The Oracle is choosing…', 0);
        const started = performance.now();
        let chosen;
        try {
            const response = await fetch('/sanctum/choose', { method: 'POST' });
            if (!response.ok) throw new Error(String(response.status));
            chosen = (await response.json()).tradition;
        } catch {
            chosen = null;
        }
        if (!ALTARS[chosen]) {
            const pick = new Uint32Array(1);
            crypto.getRandomValues(pick);
            chosen = Object.keys(ALTARS)[pick[0] % 4];
        }
        const wait = REDUCED ? 0 : Math.max(0, 1700 - (performance.now() - started));
        setTimeout(() => {
            targetPower = 1.3;
            showToast(`The Oracle chose ${ALTARS[chosen].name}`);
            let next = nearestAngle(ALTARS[chosen].angle, theta);
            if (!REDUCED) while (next < theta + Math.PI) next += TAU;
            approach(chosen, next);
            setTimeout(() => { targetPower = 1; }, 2000);
        }, wait);
    }

    function select(id) {
        if (mode === 'choosing') return;
        if (id === 'oracle') letTheOracleChoose();
        else approach(id);
    }
    for (const [id, el] of Object.entries(labels)) el.addEventListener('click', () => select(id));
    document.getElementById('back-button').addEventListener('click', returnToChamber);
    window.addEventListener('keydown', event => {
        if (event.key === 'Escape' && mode === 'approach') returnToChamber();
    });

    // Drag to turn; a short tap picks whatever is under the finger.
    const raycaster = new THREE.Raycaster();
    const pointer = new THREE.Vector2();
    const pickable = [...Object.values(altarGroups), singularity];
    let drag = null;
    canvas.addEventListener('pointerdown', event => {
        drag = { x: event.clientX, y: event.clientY, theta: thetaTarget, moved: 0, id: event.pointerId };
        canvas.setPointerCapture(event.pointerId);
    });
    canvas.addEventListener('pointermove', event => {
        if (!drag || drag.id !== event.pointerId) return;
        const dx = event.clientX - drag.x;
        drag.moved = Math.max(drag.moved, Math.hypot(dx, event.clientY - drag.y));
        if (mode === 'chamber' && drag.moved > 8) {
            canvas.classList.add('dragging');
            thetaTarget = drag.theta - dx * .0065;
            theta = thetaTarget;
        }
    });
    const endDrag = event => {
        if (!drag || drag.id !== event.pointerId) return;
        canvas.classList.remove('dragging');
        if (drag.moved <= 8) {
            pointer.set(event.clientX / window.innerWidth * 2 - 1, -(event.clientY / window.innerHeight) * 2 + 1);
            raycaster.setFromCamera(pointer, camera);
            const hit = raycaster.intersectObjects(pickable, true)[0];
            let node = hit?.object;
            while (node && !node.userData.altar) node = node.parent;
            if (node) select(node.userData.altar);
        } else if (mode === 'chamber') {
            thetaTarget = Math.round(thetaTarget / (Math.PI / 2)) * (Math.PI / 2);
        }
        drag = null;
    };
    canvas.addEventListener('pointerup', endDrag);
    canvas.addEventListener('pointercancel', endDrag);

    // Hold to begin: the cards lift while the ring fills, then hand off.
    const holdButton = document.getElementById('hold-button');
    const holdProgress = document.getElementById('hold-progress');
    let holdStart = null, holdAmount = 0, holdTimer = null, leaving = false;
    function resetHold() { holdStart = null; clearTimeout(holdTimer); }
    function begin() {
        if (leaving) return;
        leaving = true;
        resetHold();
        document.body.classList.add('leaving');
        setTimeout(() => { window.location.href = `/#read/${current}`; }, REDUCED ? 0 : 550);
    }
    // A timer, not the frame loop, decides completion, so slow devices still count a full hold.
    holdButton.addEventListener('pointerdown', event => {
        event.preventDefault();
        holdStart = performance.now();
        clearTimeout(holdTimer);
        holdTimer = setTimeout(begin, HOLD_MS);
    });
    for (const type of ['pointerup', 'pointerleave', 'pointercancel']) holdButton.addEventListener(type, resetHold);
    holdButton.addEventListener('contextmenu', event => event.preventDefault());
    holdButton.addEventListener('click', event => { if (event.detail === 0) begin(); }); // keyboard activation
    animated.push(() => {
        const target = holdStart === null ? 0 : Math.min(1, (performance.now() - holdStart) / HOLD_MS);
        holdAmount = holdStart === null ? Math.max(0, holdAmount - .06) : target;
        holdProgress.style.strokeDashoffset = String(144.5 * (1 - holdAmount));
        cards.forEach((card, i) => {
            card.position.y = card.userData.rest.y + (current === 'tarot' ? holdAmount * (.25 + i * .05) : 0);
        });
    });

    if (PARAMS.get('altar') in ALTARS) approach(PARAMS.get('altar'));

    // Measure a few seconds after the intro; drop bloom and resolution if frames are slow.
    const frameSamples = [];
    const adaptive = PARAMS.get('quality') !== 'high';
    const clock = new THREE.Clock();
    function frame() {
        const raw = clock.getDelta();
        const dt = Math.min(raw, .05);
        const time = clock.elapsedTime;
        if (adaptive && bloomOn && time > 2.5 && time < 5.5) frameSamples.push(raw);
        if (adaptive && bloomOn && time >= 5.5 && frameSamples.length) {
            const average = frameSamples.reduce((a, b) => a + b, 0) / frameSamples.length;
            frameSamples.length = 0;
            if (average > 1 / 32) setLowQuality();
        }
        const ease = REDUCED ? 1 : 1 - Math.exp(-dt * 3.2);
        if (mode === 'choosing' && !REDUCED) thetaTarget += dt * 2.4;
        theta += (thetaTarget - theta) * ease;
        radius += (radiusTarget - radius) * ease;
        height += (heightTarget - height) * ease;
        look.lerp(lookTarget, ease);
        camera.position.set(Math.sin(theta) * radius, height, Math.cos(theta) * radius);
        camera.lookAt(look);
        for (const update of animated) update(time, dt);
        placeLabels();
        if (bloomOn) composer.render(dt); else renderer.render(scene, camera);
        requestAnimationFrame(frame);
    }
    frame();
}

if (webglAvailable()) {
    start();
} else {
    document.getElementById('fallback').hidden = false;
    for (const id of ['scene', 'altar-labels', 'hint']) document.getElementById(id).hidden = true;
}
