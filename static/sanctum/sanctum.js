// The Sanctum: a prototype 3D entry. Every object is generated here; the only
// images are the existing card back and rune art. Choosing an altar hands off
// to the existing reading flow at /#read/<tradition>.
import * as THREE from '/static/vendor/three/three.module.min.js';

const REDUCED = matchMedia('(prefers-reduced-motion: reduce)').matches;
const TAU = Math.PI * 2;
const RING = 4.4; // distance of each altar from the singularity
const HOLD_MS = 1100;
const ALTARS = {
    tarot: { name: 'Tarot', tagline: 'Find perspective in the cards', angle: 0, verb: 'Hold to draw', labelY: 2.0 },
    iching: { name: 'I Ching', tagline: 'Navigate the nature of change', angle: Math.PI / 2, verb: 'Hold to cast', labelY: 2.75 },
    number: { name: 'Numbers', tagline: 'Discover meaning in a number', angle: Math.PI, verb: 'Hold to draw', labelY: 3.0 },
    runes: { name: 'Runes', tagline: 'Listen to the wisdom of symbols', angle: -Math.PI / 2, verb: 'Hold to cast', labelY: 2.85 },
};

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

function canvasTexture(size, draw) {
    const canvas = document.createElement('canvas');
    canvas.width = canvas.height = size;
    draw(canvas.getContext('2d'), size);
    const texture = new THREE.CanvasTexture(canvas);
    texture.colorSpace = THREE.SRGBColorSpace;
    return texture;
}

function glowTexture(inner, outer) {
    return canvasTexture(128, (ctx, s) => {
        const g = ctx.createRadialGradient(s / 2, s / 2, 0, s / 2, s / 2, s / 2);
        g.addColorStop(0, inner);
        g.addColorStop(1, outer);
        ctx.fillStyle = g;
        ctx.fillRect(0, 0, s, s);
    });
}

function start() {
    const canvas = document.getElementById('scene');
    const renderer = new THREE.WebGLRenderer({ canvas, antialias: true, powerPreference: 'high-performance' });
    renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
    renderer.toneMapping = THREE.ACESFilmicToneMapping;
    renderer.toneMappingExposure = 1.2;

    const scene = new THREE.Scene();
    scene.fog = new THREE.FogExp2(0x0c0a14, 0.024);
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

    // Sky dome: violet at the horizon, near-black overhead.
    const skyMaterial = new THREE.ShaderMaterial({
        side: THREE.BackSide, depthWrite: false,
        vertexShader: 'varying vec3 vDir; void main(){ vDir = normalize(position); gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0); }',
        fragmentShader: `varying vec3 vDir;
            void main(){
                float h = vDir.y;
                vec3 top = vec3(0.018, 0.014, 0.036);
                vec3 horizon = vec3(0.13, 0.08, 0.21);
                vec3 low = vec3(0.03, 0.022, 0.05);
                vec3 color = h > 0.0 ? mix(horizon, top, pow(h, 0.5)) : mix(horizon, low, pow(-h, 0.35));
                gl_FragColor = vec4(color, 1.0);
            }`,
    });
    const sky = new THREE.Mesh(new THREE.SphereGeometry(90, 32, 16), skyMaterial);
    scene.add(sky);

    // A soft environment so metal reads as metal without an HDR download.
    const envScene = new THREE.Scene();
    envScene.add(new THREE.Mesh(new THREE.SphereGeometry(10, 16, 8), skyMaterial));
    for (const [x, y, z, color] of [[6, 4, 2, 0xffd9a0], [-5, 3, -4, 0xb08cff], [0, 6, -6, 0xffe6c0]]) {
        const panel = new THREE.Mesh(new THREE.PlaneGeometry(4, 2), new THREE.MeshBasicMaterial({ color, side: THREE.DoubleSide }));
        panel.position.set(x, y, z);
        panel.lookAt(0, 0, 0);
        envScene.add(panel);
    }
    const pmrem = new THREE.PMREMGenerator(renderer);
    scene.environment = pmrem.fromScene(envScene, 0.04).texture;
    pmrem.dispose();

    // Stars and a few constellations in the dome.
    const starDome = new THREE.Group();
    scene.add(starDome);
    const starSprite = glowTexture('rgba(255,255,255,1)', 'rgba(255,255,255,0)');
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
    const toSky = (azimuth, elevation) => {
        const a = THREE.MathUtils.degToRad(azimuth), e = THREE.MathUtils.degToRad(elevation);
        return new THREE.Vector3(Math.sin(a) * Math.cos(e) * 78, Math.sin(e) * 78, -Math.cos(a) * Math.cos(e) * 78);
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
    animated.push((time, dt) => { if (!REDUCED) starDome.rotation.y += dt * .004; });

    // The chamber floor: an inscribed disc.
    const floorTexture = canvasTexture(1024, (ctx, s) => {
        const c = s / 2;
        const base = ctx.createRadialGradient(c, c, 0, c, c, c);
        base.addColorStop(0, '#2c2245');
        base.addColorStop(.55, '#1a1428');
        base.addColorStop(1, '#0b0a11');
        ctx.fillStyle = base;
        ctx.fillRect(0, 0, s, s);
        const scale = c / 10;
        ctx.strokeStyle = 'rgba(212,183,124,.55)';
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
        ctx.strokeStyle = 'rgba(212,183,124,.22)'; ctx.lineWidth = 1.5;
        for (const altar of Object.values(ALTARS)) {
            const x = c + Math.sin(altar.angle) * RING * scale, y = c + Math.cos(altar.angle) * RING * scale;
            ctx.beginPath(); ctx.moveTo(c + Math.sin(altar.angle) * 2.4 * scale, c + Math.cos(altar.angle) * 2.4 * scale); ctx.lineTo(x, y); ctx.stroke();
            ctx.beginPath(); ctx.arc(x, y, 1.45 * scale, 0, TAU); ctx.stroke();
        }
    });
    floorTexture.anisotropy = maxAnisotropy;
    const floor = new THREE.Mesh(new THREE.CircleGeometry(10, 128), new THREE.MeshStandardMaterial({
        map: floorTexture, emissiveMap: floorTexture, emissive: 0xffffff, emissiveIntensity: .22, roughness: .8, metalness: .15,
    }));
    floor.rotation.x = -Math.PI / 2;
    scene.add(floor);

    scene.add(new THREE.HemisphereLight(0x8c78c0, 0x120e1a, 0.6));

    const material = {
        wood: new THREE.MeshStandardMaterial({ color: 0x3d2619, roughness: .55, metalness: .05 }),
        darkWood: new THREE.MeshStandardMaterial({ color: 0x24160e, roughness: .6 }),
        velvet: new THREE.MeshStandardMaterial({ color: 0x3b2160, roughness: .95 }),
        gold: new THREE.MeshStandardMaterial({ color: 0xd9b56a, metalness: 1, roughness: .3 }),
        stone: new THREE.MeshStandardMaterial({ color: 0x5f5a6b, roughness: 1, flatShading: true }),
        darkStone: new THREE.MeshStandardMaterial({ color: 0x3f3a48, roughness: 1, flatShading: true }),
        lacquer: new THREE.MeshStandardMaterial({ color: 0x5c1c16, roughness: .28, metalness: .1 }),
        wax: new THREE.MeshStandardMaterial({ color: 0xeee2c8, roughness: .7 }),
        void: new THREE.MeshBasicMaterial({ color: 0x120c10 }),
    };
    const flame = new THREE.MeshBasicMaterial({ color: 0xffd08a });
    const mesh = (geometry, mat, x = 0, y = 0, z = 0) => {
        const m = new THREE.Mesh(geometry, mat);
        m.position.set(x, y, z);
        return m;
    };
    const candle = (group, x, z, height = .28, baseY = 0) => {
        group.add(mesh(new THREE.CylinderGeometry(.045, .05, height, 16), material.wax, x, baseY + height / 2, z));
        const tip = mesh(new THREE.SphereGeometry(.03, 12, 8), flame, x, baseY + height + .045, z);
        tip.scale.y = 1.9;
        group.add(tip);
        const light = new THREE.PointLight(0xffb066, 3.2, 0, 2);
        light.position.set(x, baseY + height + .12, z);
        group.add(light);
        const seed = Math.random() * 100;
        animated.push(time => {
            const flicker = REDUCED ? 1 : .86 + .14 * Math.sin(time * 9 + seed) * Math.sin(time * 3.7 + seed * 2);
            light.intensity = 3.2 * flicker;
            tip.scale.y = 1.9 * (.9 + .1 * flicker);
        });
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

    // Tarot: a reader's table with a velvet cloth and three cards face down.
    const tarot = new THREE.Group();
    tarot.add(mesh(new THREE.BoxGeometry(2.3, .1, 1.3), material.wood, 0, .95, 0));
    tarot.add(mesh(new THREE.BoxGeometry(2.1, .18, 1.1), material.darkWood, 0, .82, 0));
    for (const [x, z] of [[-.95, -.5], [.95, -.5], [-.95, .5], [.95, .5]]) tarot.add(mesh(new THREE.CylinderGeometry(.05, .035, .8, 12), material.darkWood, x, .4, z));
    tarot.add(mesh(new THREE.BoxGeometry(1.96, .012, 1.06), material.gold, 0, 1.003, 0));
    tarot.add(mesh(new THREE.BoxGeometry(1.9, .016, 1.0), material.velvet, 0, 1.008, 0));
    const cardBack = load('/static/cards/tarot/card-back.webp');
    const cardMaterial = new THREE.MeshStandardMaterial({ map: cardBack, roughness: .45, metalness: .1 });
    const cards = [-.5, 0, .5].map((x, i) => {
        const card = mesh(new THREE.PlaneGeometry(.36, .6), cardMaterial, x, 1.022, .06);
        card.rotation.set(-Math.PI / 2, 0, (i - 1) * -.08);
        card.userData.rest = card.position.clone();
        tarot.add(card);
        return card;
    });
    const edge = new THREE.MeshStandardMaterial({ color: 0xe8dcc3, roughness: .8 });
    const deck = new THREE.Mesh(new THREE.BoxGeometry(.36, .1, .6), [edge, edge, cardMaterial, edge, edge, edge]);
    deck.position.set(.86, 1.066, -.22);
    deck.rotation.y = .25;
    tarot.add(deck);
    candle(tarot, -.86, -.34, .3, 1.0);
    place('tarot', tarot);

    // Runes: a rough stone altar between two standing stones.
    const runes = new THREE.Group();
    runes.add(mesh(roughen(new THREE.BoxGeometry(1.7, .62, .95, 3, 2, 2), .12, 3), material.darkStone, 0, .31, 0));
    runes.add(mesh(roughen(new THREE.BoxGeometry(2.05, .24, 1.2, 4, 1, 3), .07, 5), material.stone, 0, .72, 0));
    const leftStone = mesh(roughen(new THREE.BoxGeometry(.52, 2.5, .38, 2, 6, 2), .14, 11), material.stone, -1.32, 1.25, -.6);
    leftStone.rotation.z = .05;
    const rightStone = mesh(roughen(new THREE.BoxGeometry(.46, 2.1, .36, 2, 5, 2), .14, 13), material.stone, 1.36, 1.05, -.66);
    rightStone.rotation.z = -.07;
    runes.add(leftStone, rightStone);
    const runeRand = seeded(21);
    for (const [name, x, z] of [['ansuz', -.55, .1], ['raidho', -.05, -.18], ['algiz', .45, .12], ['wunjo', .1, .3], ['sowilo', .7, -.2]]) {
        const stone = mesh(new THREE.PlaneGeometry(.32, .32), new THREE.MeshStandardMaterial({
            map: load(`/static/runes/${name}.webp`), transparent: true, alphaTest: .15, roughness: .9,
        }), x, .86, z);
        stone.rotation.set(-Math.PI / 2, 0, (runeRand() - .5) * 1.2);
        runes.add(stone);
    }
    const brazier = new THREE.Group();
    brazier.add(mesh(new THREE.CylinderGeometry(.22, .12, .16, 24), material.gold, 0, .62, 0));
    brazier.add(mesh(new THREE.CylinderGeometry(.04, .07, .55, 12), material.gold, 0, .27, 0));
    const ember = mesh(new THREE.SphereGeometry(.13, 16, 8), new THREE.MeshBasicMaterial({ color: 0xff9a4a }), 0, .7, 0);
    ember.scale.y = .5;
    brazier.add(ember);
    const fire = new THREE.PointLight(0xff8a3d, 5, 0, 2);
    fire.position.set(0, 1.0, 0);
    brazier.add(fire);
    brazier.position.set(1.05, 0, .75);
    runes.add(brazier);
    animated.push(time => { fire.intensity = REDUCED ? 5 : 4.2 + Math.sin(time * 7.3) * .6 + Math.sin(time * 13.1) * .3; });
    place('runes', runes);

    // I Ching: a round lacquered table, three bronze coins, a hexagram above.
    const iching = new THREE.Group();
    iching.add(mesh(new THREE.CylinderGeometry(.16, .34, .7, 24), material.lacquer, 0, .35, 0));
    iching.add(mesh(new THREE.CylinderGeometry(1.0, 1.0, .09, 64), material.lacquer, 0, .74, 0));
    const rim = mesh(new THREE.TorusGeometry(1.0, .028, 12, 96), material.gold, 0, .785, 0);
    rim.rotation.x = Math.PI / 2;
    iching.add(rim);
    iching.add(mesh(new THREE.CylinderGeometry(.8, .8, .012, 64), new THREE.MeshStandardMaterial({ color: 0x23131a, roughness: .9 }), 0, .79, 0));
    for (const [x, z, tilt] of [[-.36, .1, .0], [.02, -.18, .12], [.36, .16, -.08]]) {
        const coin = new THREE.Group();
        coin.add(mesh(new THREE.CylinderGeometry(.15, .15, .026, 40), material.gold));
        coin.add(mesh(new THREE.BoxGeometry(.06, .03, .06), material.void));
        coin.position.set(x, .81, z);
        coin.rotation.set(tilt, x * 3, 0);
        iching.add(coin);
    }
    const hexagram = new THREE.Group();
    const lineGlow = new THREE.MeshBasicMaterial({ color: 0xf1d492 });
    [1, 0, 1, 1, 0, 1].forEach((solid, i) => {
        const y = i * .14;
        if (solid) hexagram.add(mesh(new THREE.BoxGeometry(.72, .045, .03), lineGlow, 0, y, 0));
        else for (const x of [-.22, .22]) hexagram.add(mesh(new THREE.BoxGeometry(.28, .045, .03), lineGlow, x, y, 0));
    });
    const hexHalo = new THREE.Sprite(new THREE.SpriteMaterial({ map: glowTexture('rgba(241,212,146,.45)', 'rgba(241,212,146,0)'), blending: THREE.AdditiveBlending, depthWrite: false }));
    hexHalo.scale.set(2.2, 2.2, 1);
    hexHalo.position.set(0, .35, 0);
    hexagram.add(hexHalo);
    hexagram.position.set(0, 1.6, 0);
    iching.add(hexagram);
    candle(iching, .62, -.42, .24, .79);
    animated.push(time => { if (!REDUCED) hexagram.position.y = 1.6 + Math.sin(time * 1.1) * .06; });
    place('iching', iching);

    // Numbers: an armillary sphere on a column, numerals in orbit.
    const number = new THREE.Group();
    number.add(mesh(new THREE.CylinderGeometry(.48, .54, .16, 32), material.darkStone, 0, .08, 0));
    number.add(mesh(new THREE.CylinderGeometry(.12, .2, 1.1, 24), material.gold, 0, .7, 0));
    const armillary = new THREE.Group();
    const ringGeometry = new THREE.TorusGeometry(.78, .022, 10, 96);
    for (const [rx, ry, rz] of [[Math.PI / 2, 0, 0], [0, 0, 0], [0, Math.PI / 2, 0], [Math.PI / 2, 0, .41]]) {
        const ring = new THREE.Mesh(ringGeometry, material.gold);
        ring.rotation.set(rx, ry, rz);
        armillary.add(ring);
    }
    armillary.add(mesh(new THREE.SphereGeometry(.12, 24, 12), new THREE.MeshBasicMaterial({ color: 0xe9dcff })));
    const orbLight = new THREE.PointLight(0xb79cff, 4, 0, 2);
    armillary.add(orbLight);
    armillary.position.set(0, 2.05, 0);
    number.add(armillary);
    const numerals = [];
    const makeNumerals = () => {
        for (let n = 1; n <= 9; n++) {
            const sprite = new THREE.Sprite(new THREE.SpriteMaterial({
                map: canvasTexture(128, (ctx, s) => {
                    ctx.fillStyle = '#f1d492';
                    ctx.font = '600 84px Cinzel, "Cormorant Garamond", Georgia, serif';
                    ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
                    ctx.shadowColor = 'rgba(241,212,146,.8)'; ctx.shadowBlur = 16;
                    ctx.fillText(String(n), s / 2, s / 2 + 4);
                }), transparent: true, depthWrite: false,
            }));
            sprite.scale.set(.32, .32, 1);
            sprite.userData = { phase: n / 9 * TAU, tilt: (n % 3 - 1) * .35 };
            number.add(sprite);
            numerals.push(sprite);
        }
    };
    Promise.race([document.fonts.load('600 84px Cinzel'), new Promise(resolve => setTimeout(resolve, 1200))]).catch(() => {}).then(makeNumerals);
    animated.push((time, dt) => {
        if (!REDUCED) { armillary.rotation.y += dt * .25; armillary.rotation.x = Math.sin(time * .2) * .15; }
        for (const sprite of numerals) {
            const a = sprite.userData.phase + (REDUCED ? 0 : time * .22);
            sprite.position.set(Math.cos(a) * 1.25, 2.05 + Math.sin(a * 2 + sprite.userData.tilt) * .35, Math.sin(a) * 1.25);
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
    const photonRing = new THREE.Mesh(new THREE.TorusGeometry(.46, .016, 12, 128), new THREE.MeshBasicMaterial({ color: 0xffe2a8 }));
    facing.add(photonRing);
    const haloMaterial = new THREE.SpriteMaterial({ map: glowTexture('rgba(171,140,230,.85)', 'rgba(109,79,176,0)'), blending: THREE.AdditiveBlending, depthWrite: false });
    const halo = new THREE.Sprite(haloMaterial);
    halo.scale.set(4.6, 4.6, 1);
    singularity.add(halo);
    const diskUniforms = { uTime: { value: 0 }, uPower: { value: 1 } };
    const disk = new THREE.Mesh(new THREE.RingGeometry(.58, 1.75, 160, 1), new THREE.ShaderMaterial({
        uniforms: diskUniforms, transparent: true, depthWrite: false, side: THREE.DoubleSide, blending: THREE.AdditiveBlending,
        vertexShader: 'varying vec2 vPos; void main(){ vPos = position.xy; gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0); }',
        fragmentShader: `uniform float uTime; uniform float uPower; varying vec2 vPos;
            void main(){
                float r = length(vPos);
                float t = (r - 0.58) / 1.17;
                float a = atan(vPos.y, vPos.x);
                float band = smoothstep(0.0, 0.06, t) * (1.0 - smoothstep(0.35, 1.0, t));
                float swirl = 0.5 + 0.5 * sin(a * 3.0 - r * 7.0 + uTime * 1.7 * uPower);
                float fine = 0.5 + 0.5 * sin(a * 11.0 + r * 19.0 - uTime * 2.3 * uPower);
                vec3 hot = vec3(1.0, 0.86, 0.6);
                vec3 cool = vec3(0.55, 0.38, 0.95);
                vec3 color = mix(hot, cool, smoothstep(0.0, 0.8, t));
                float alpha = band * (0.35 + 0.45 * swirl + 0.2 * fine) * uPower;
                gl_FragColor = vec4(color * alpha * 1.5, alpha);
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
    const voidLight = new THREE.PointLight(0x9f7bff, 9, 0, 2);
    singularity.add(voidLight);
    let power = 1;
    let targetPower = 1;
    animated.push((time, dt) => {
        power += (targetPower - power) * Math.min(1, dt * 2.5);
        diskUniforms.uTime.value = time;
        diskUniforms.uPower.value = power;
        haloMaterial.opacity = Math.min(1, .75 * power);
        voidLight.intensity = 9 * power;
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

    const nearestAngle = (target, from) => target + Math.round((from - target) / TAU) * TAU;
    const facingAltar = () => {
        let best = 'tarot', distance = Infinity;
        for (const [id, altar] of Object.entries(ALTARS)) {
            const d = Math.abs(nearestAngle(altar.angle, theta) - theta);
            if (d < distance) { distance = d; best = id; }
        }
        return best;
    };

    // Labels are real buttons placed over the scene.
    const labels = Object.fromEntries([...document.querySelectorAll('.altar-label')].map(el => [el.dataset.altar, el]));
    // Labels sit above an altar, and slide to its front edge as it turns toward
    // the viewer, so the nearest altar's label never lands on the singularity.
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
        lookTarget.copy(altarGroups[id].position).setY(id === 'tarot' ? .55 : .9);
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

    if (new URLSearchParams(location.search).get('altar') in ALTARS) approach(new URLSearchParams(location.search).get('altar'));

    const clock = new THREE.Clock();
    function frame() {
        const dt = Math.min(clock.getDelta(), .05);
        const time = clock.elapsedTime;
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
        renderer.render(scene, camera);
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
