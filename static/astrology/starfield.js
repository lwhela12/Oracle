(function () {
  "use strict";

  const TAU = Math.PI * 2;
  const GLYPHS = {
    Sun: "☉", Moon: "☽", Mercury: "☿", Venus: "♀", Mars: "♂",
    Jupiter: "♃", Saturn: "♄", Uranus: "♅", Neptune: "♆", Pluto: "♇", Rahu: "☊", Ketu: "☋",
  };

  function clamp(value, min, max) {
    return Math.max(min, Math.min(max, value));
  }

  function smoothstep(value) {
    const x = clamp(value, 0, 1);
    return x * x * (3 - 2 * x);
  }

  function makeRandom(seed) {
    return function random() {
      seed |= 0;
      seed = (seed + 0x6d2b79f5) | 0;
      let value = Math.imul(seed ^ (seed >>> 15), 1 | seed);
      value = (value + Math.imul(value ^ (value >>> 7), 61 | value)) ^ value;
      return ((value ^ (value >>> 14)) >>> 0) / 4294967296;
    };
  }

  function sameAspect(first, second) {
    if (!first || !second) return false;
    if (first === second) return true;
    if (first.aspect === "graha drishti" || second.aspect === "graha drishti") {
      return first.aspect === second.aspect && first.body_1 === second.body_1 && first.body_2 === second.body_2 && first.house_distance === second.house_distance;
    }
    const sameBodies = (
      first.body_1 === second.body_1 && first.body_2 === second.body_2
    ) || (
      first.body_1 === second.body_2 && first.body_2 === second.body_1
    );
    if (!sameBodies || first.aspect !== second.aspect) return false;
    if (first.orb == null || second.orb == null) return true;
    return Math.abs(Number(first.orb) - Number(second.orb)) < 0.0001;
  }

  class CelestialField {
    constructor(canvas, chart, options = {}) {
      if (!(canvas instanceof HTMLCanvasElement)) {
        throw new TypeError("CelestialField requires a canvas element.");
      }

      this.canvas = canvas;
      this.ctx = canvas.getContext("2d", { alpha: true });
      this.chart = chart || {};
      this.onPhase = typeof options.onPhase === "function" ? options.onPhase : null;
      this.onRevealProgress = typeof options.onRevealProgress === "function" ? options.onRevealProgress : null;
      this.lastRevealProgress = null;
      this.nodeLayer = options.nodeLayer instanceof HTMLElement ? options.nodeLayer : null;
      this.onSelect = typeof options.onSelect === "function" ? options.onSelect : null;
      this.planetNames = Object.keys(this.chart.planets || {}).filter((name) =>
        Number.isFinite(Number(this.chart.planets[name]?.longitude))
      );
      this.aspects = this.chart.chart_kind === 'transit'
        ? (this.chart.transit_aspects || []).map(a => ({...a,body_1:a.transit_body,body_2:'Natal '+a.natal_body}))
        : this.chart.tradition === 'vedic' ? (this.chart.vedic_aspects || [])
        : Array.isArray(this.chart.major_aspects) ? this.chart.major_aspects : [];
      this.selected = null;
      this.selectedAspect = null;
      this.relevant = new Set();
      this.particles = [];
      this.anchors = new Map();
      this.planetNodes = new Map();
      this.width = 1;
      this.height = 1;
      this.radius = 1;
      this.time = 0;
      this.lastFrame = 0;
      this.raf = null;
      this.transition = null;
      this.userPaused = false;
      this.hidden = document.hidden;
      this.destroyed = false;

      this.motionQuery = window.matchMedia("(prefers-reduced-motion: reduce)");
      this.reducedMotion = this.motionQuery.matches;
      this.mode = this.reducedMotion ? "chart" : "ambient";

      this.handleVisibility = () => {
        this.hidden = document.hidden;
        if (this.hidden) this.stopLoop();
        else {
          this.lastFrame = 0;
          this.render(performance.now());
          this.ensureLoop();
        }
      };
      this.handleMotionPreference = (event) => {
        this.reducedMotion = event.matches;
        if (event.matches) {
          const transitionKind = this.transition?.kind;
          if (transitionKind === "reveal") this.mode = "chart";
          if (transitionKind === "disperse") this.mode = "ambient";
          this.transition = null;
          this.stopLoop();
          this.render(performance.now());
          this.updatePlanetNodes();
          if (transitionKind === "reveal") this.emitPhase("resolved");
        } else {
          this.lastFrame = 0;
          this.ensureLoop();
        }
      };

      document.addEventListener("visibilitychange", this.handleVisibility);
      if (this.motionQuery.addEventListener) {
        this.motionQuery.addEventListener("change", this.handleMotionPreference);
      } else {
        this.motionQuery.addListener(this.handleMotionPreference);
      }

      this.resizeObserver = typeof ResizeObserver === "function"
        ? new ResizeObserver(() => this.resize())
        : null;
      if (this.resizeObserver) this.resizeObserver.observe(canvas);
      else {
        this.handleWindowResize = () => this.resize();
        window.addEventListener("resize", this.handleWindowResize);
      }

      this.createPlanetNodes();
      this.resize();
      this.createParticles();
      this.render(performance.now());

      if (this.reducedMotion) this.emitPhase("resolved");
      else this.ensureLoop();
    }

    createPlanetNodes() {
      if (!this.nodeLayer) return;
      for (const name of this.planetNames) {
        const button = document.createElement("button");
        const label = document.createElement("span");
        const glyph = GLYPHS[name];
        const handleSelect = (event) => {
          if (this.destroyed) return;
          const selectedName = event.detail > 0 ? this.planetNearestPointer(event, name) : name;
          this.selectPlanet(selectedName);
          if (this.onSelect) this.onSelect(selectedName);
        };

        button.type = "button";
        button.className = "planet-node";
        button.dataset.planet = name;
        button.setAttribute("aria-label", name);
        button.setAttribute("aria-pressed", "false");
        button.title = name;
        button.hidden = true;
        label.className = "node-label";
        label.textContent = glyph ? `${glyph} ${name}` : name;
        button.appendChild(label);
        button.addEventListener("click", handleSelect);
        this.nodeLayer.appendChild(button);
        this.planetNodes.set(name, { button, handleSelect });
      }
    }

    planetNearestPointer(event, fallbackName) {
      const canvasRect = this.canvas.getBoundingClientRect();
      const pointerX = event.clientX - canvasRect.left;
      const pointerY = event.clientY - canvasRect.top;
      if (!Number.isFinite(pointerX) || !Number.isFinite(pointerY)) return fallbackName;

      let nearestName = fallbackName;
      let nearestAnchor = this.anchors.get(fallbackName);
      let nearestDistance = Number.POSITIVE_INFINITY;
      for (const [name, anchor] of this.anchors) {
        const distance = Math.hypot(pointerX - anchor.x, pointerY - anchor.y);
        if (distance < nearestDistance) {
          nearestName = name;
          nearestAnchor = anchor;
          nearestDistance = distance;
        }
      }

      if (!nearestAnchor) return nearestName;
      const coincident = [];
      for (const [name, anchor] of this.anchors) {
        if (Math.hypot(anchor.x - nearestAnchor.x, anchor.y - nearestAnchor.y) <= 2) {
          coincident.push(name);
        }
      }
      if (coincident.length < 2) return nearestName;
      const currentIndex = coincident.indexOf(this.selected);
      return coincident[(currentIndex + 1) % coincident.length];
    }

    syncPlanetNodes() {
      if (!this.nodeLayer) return;
      const canvasRect = this.canvas.getBoundingClientRect();
      const layerRect = this.nodeLayer.getBoundingClientRect();
      const offsetX = canvasRect.left - layerRect.left;
      const offsetY = canvasRect.top - layerRect.top;

      for (const [name, node] of this.planetNodes) {
        const anchor = this.anchors.get(name);
        if (!anchor) continue;
        node.button.style.left = `${offsetX + anchor.x}px`;
        node.button.style.top = `${offsetY + anchor.y}px`;
      }
    }

    updatePlanetNodes() {
      const visible = this.mode === "chart" && !this.transition;
      for (const [name, node] of this.planetNodes) {
        node.button.hidden = !visible;
        node.button.setAttribute("aria-pressed", String(name === this.selected));
      }
    }

    createParticles() {
      let seed = 0x51a7f1e1;
      for (const name of this.planetNames) {
        const longitude = Math.round(Number(this.chart.planets[name].longitude) * 1000);
        seed = Math.imul(seed ^ longitude, 16777619);
      }
      const random = makeRandom(seed);
      const isMobile = window.matchMedia("(max-width: 700px)").matches;
      const glyphParticleCount = isMobile ? 105 : 155;
      const decorativeCount = isMobile ? 96 : 190;

      for (const [planetIndex, name] of this.planetNames.entries()) {
        const glyphPoints = this.sampleGlyph(GLYPHS[name] || "•", glyphParticleCount, random);
        for (const point of glyphPoints) {
          const depth = 0.45 + random() * 0.55;
          const ambientRadius = Math.pow(random(), 0.64);
          const arm = this.particles.length % 5;
          this.particles.push({
            decorative: false,
            planet: name,
            depth,
            size: 0.58 + random() * 0.58 * depth,
            alpha: (0.58 + random() * 0.38) * point.alpha,
            tint: random(),
            bright: random() > 0.985,
            twinkle: random() * TAU,
            twinkleSpeed: 0.28 + random() * 0.62,
            ambientRadius,
            ambientAngle: (arm / 5) * TAU + ambientRadius * 7.6 + (random() - 0.5) * 0.72,
            ambientSpeed: (0.012 + random() * 0.026) * (0.55 + depth),
            wobble: random() * TAU,
            glyphX: point.x,
            glyphY: point.y,
            glyphPhase: planetIndex * 0.79 + random() * 0.24,
            // A minority of stars peel away and return, preserving a readable core.
            wisp: random() < 0.27,
            flowPhase: random() * TAU,
            flowSpeed: 0.35 + random() * 0.22,
          });
        }
      }

      for (let index = 0; index < decorativeCount; index += 1) {
        const depth = 0.35 + random() * 0.65;
        const ambientRadius = Math.pow(random(), 0.64);
        const arm = index % 5;
        const ambientAngle = (arm / 5) * TAU + ambientRadius * 7.6 + (random() - 0.5) * 0.72;
        const bright = random() > 0.982;

        this.particles.push({
          decorative: true,
          planet: null,
          depth,
          size: bright ? 1.25 + random() * 0.85 : 0.34 + random() * 0.72 * depth,
          alpha: 0.26 + random() * 0.66,
          tint: random(),
          bright,
          twinkle: random() * TAU,
          twinkleSpeed: 0.4 + random() * 1.2,
          ambientRadius,
          ambientAngle,
          ambientSpeed: (0.012 + random() * 0.026) * (0.55 + depth),
          wobble: random() * TAU,
        });
      }
    }

    sampleGlyph(glyph, count, random) {
      const mask = document.createElement("canvas");
      mask.width = 96;
      mask.height = 96;
      const context = mask.getContext("2d", { willReadFrequently: true });
      if (!context || typeof context.getImageData !== "function") {
        return Array.from({ length: count }, (_, index) => {
          const angle = (index / count) * TAU;
          return { x: Math.cos(angle) * 0.46, y: Math.sin(angle) * 0.46, alpha: 1 };
        });
      }

      context.clearRect(0, 0, mask.width, mask.height);
      context.fillStyle = "#fff";
      context.textAlign = "center";
      context.textBaseline = "middle";
      context.font = '68px "Apple Symbols", "Segoe UI Symbol", "Noto Sans Symbols 2", Georgia, serif';
      context.fillText(glyph, mask.width / 2, mask.height / 2 + 2);

      const pixels = context.getImageData(0, 0, mask.width, mask.height).data;
      const candidates = [];
      let minX = mask.width;
      let minY = mask.height;
      let maxX = 0;
      let maxY = 0;
      for (let y = 1; y < mask.height - 1; y += 2) {
        for (let x = 1; x < mask.width - 1; x += 2) {
          const alpha = pixels[(y * mask.width + x) * 4 + 3];
          if (alpha < 36) continue;
          candidates.push({ x, y, alpha: alpha / 255 });
          minX = Math.min(minX, x);
          minY = Math.min(minY, y);
          maxX = Math.max(maxX, x);
          maxY = Math.max(maxY, y);
        }
      }

      if (candidates.length === 0) {
        return [{ x: 0, y: 0, alpha: 1 }];
      }
      for (let index = candidates.length - 1; index > 0; index -= 1) {
        const swapIndex = Math.floor(random() * (index + 1));
        [candidates[index], candidates[swapIndex]] = [candidates[swapIndex], candidates[index]];
      }

      const centerX = (minX + maxX) / 2;
      const centerY = (minY + maxY) / 2;
      const span = Math.max(1, maxX - minX, maxY - minY);
      const points = [];
      for (let index = 0; index < count; index += 1) {
        const source = candidates[index % candidates.length];
        points.push({
          x: (source.x - centerX) / span,
          y: (source.y - centerY) / span,
          alpha: 0.68 + source.alpha * 0.32,
        });
      }
      return points;
    }

    resize() {
      if (this.destroyed) return;
      const rect = this.canvas.getBoundingClientRect();
      const oldWidth = this.width;
      const oldHeight = this.height;
      this.width = Math.max(1, rect.width || this.canvas.clientWidth || 1);
      this.height = Math.max(1, rect.height || this.canvas.clientHeight || 1);
      this.radius = Math.min(this.width, this.height) * 0.38;
      const dpr = Math.min(window.devicePixelRatio || 1, 1.75);
      this.canvas.width = Math.round(this.width * dpr);
      this.canvas.height = Math.round(this.height * dpr);
      this.ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      this.buildAnchors();
      this.syncPlanetNodes();

      if (this.transition && oldWidth > 1 && oldHeight > 1) {
        const sx = this.width / oldWidth;
        const sy = this.height / oldHeight;
        for (const point of this.transition.from) {
          point.x *= sx;
          point.y *= sy;
        }
      }
      this.render(performance.now());
      this.updatePlanetNodes();
    }

    buildAnchors() {
      this.anchors.clear();
      const cx = this.width / 2;
      const cy = this.height / 2;
      const placed = [];
      const resolved = new Map();
      const preferredRadii = [0.68, 0.84, 0.52, 0.94, 0.38, 0.76, 0.60, 0.46, 0.88, 0.32];
      const minSpacing = this.glyphSize() + 7;
      const ordered = this.planetNames.map((name, index) => ({
        name,
        index,
        longitude: Number(this.chart.planets[name].longitude),
      })).sort((first, second) => first.longitude - second.longitude || first.index - second.index);

      for (const { name, longitude } of ordered) {
        const angle = (longitude - 90) * Math.PI / 180;
        let best = null;
        for (const radiusFactor of preferredRadii) {
          const distance = this.radius * radiusFactor;
          const candidate = {
            x: cx + Math.cos(angle) * distance,
            y: cy - Math.sin(angle) * distance,
            angle,
            radiusFactor,
          };
          const nearest = placed.length === 0 ? Number.POSITIVE_INFINITY : Math.min(
            ...placed.map((anchor) => Math.hypot(candidate.x - anchor.x, candidate.y - anchor.y))
          );
          if (!best || nearest > best.nearest) best = { ...candidate, nearest };
          if (nearest >= minSpacing) {
            best = { ...candidate, nearest };
            break;
          }
        }
        resolved.set(name, best);
        placed.push(best);
      }

      this.planetNames.forEach((name) => {
        const anchor = resolved.get(name);
        if (!anchor) return;
        const longitude = Number(this.chart.planets[name].longitude);
        const angle = (longitude - 90) * Math.PI / 180;
        this.anchors.set(name, {
          x: anchor.x,
          y: anchor.y,
          angle,
          radiusFactor: anchor.radiusFactor,
        });
      });
    }

    glyphSize() {
      return clamp(this.radius * 0.20, 28, this.width < 520 ? 32 : 42);
    }

    ambientPosition(particle, atTime = this.time) {
      const cx = this.width / 2;
      const cy = this.height / 2;
      const angle = particle.ambientAngle + atTime * particle.ambientSpeed;
      const radius = this.radius * (0.06 + particle.ambientRadius * 1.28);
      const breathing = 1 + Math.sin(atTime * 0.11 + particle.wobble) * 0.018;
      return {
        x: cx + Math.cos(angle) * radius * breathing,
        y: cy + Math.sin(angle) * radius * 0.61 * breathing
          + Math.sin(angle * 2.1 + particle.wobble) * this.radius * 0.035,
      };
    }

    chartPosition(particle, atTime = this.time) {
      if (particle.decorative || !particle.planet) {
        const ambient = this.ambientPosition(particle, atTime * 0.52);
        return {
          x: this.width / 2 + (ambient.x - this.width / 2) * 0.92,
          y: this.height / 2 + (ambient.y - this.height / 2) * 0.92,
        };
      }
      const anchor = this.anchors.get(particle.planet);
      if (!anchor) return this.ambientPosition(particle, atTime);
      const breathing = 1 + Math.sin(atTime * 0.54 + particle.glyphPhase) * 0.035;
      const scale = this.glyphSize() * breathing;
      const phase = atTime * particle.flowSpeed + particle.flowPhase;
      const release = particle.wisp ? Math.pow((1 - Math.cos(phase)) / 2, 2) : 0;
      const curl = phase * 1.7 + particle.wobble;
      const drift = scale * (0.018 + release * 0.34);
      return {
        x: anchor.x + particle.glyphX * scale + Math.cos(curl) * drift,
        y: anchor.y + particle.glyphY * scale + Math.sin(curl) * drift * 0.72,
      };
    }

    positionFor(particle, index, now) {
      if (!this.transition) {
        return this.mode === "chart"
          ? this.chartPosition(particle)
          : this.ambientPosition(particle);
      }
      const progress = smoothstep((now - this.transition.started) / this.transition.duration);
      const target = this.transition.kind === "reveal"
        ? this.chartPosition(particle)
        : this.ambientPosition(particle);
      const start = this.transition.from[index];
      return {
        x: start.x + (target.x - start.x) * progress,
        y: start.y + (target.y - start.y) * progress,
      };
    }

    capturePositions(now) {
      return this.particles.map((particle, index) => this.positionFor(particle, index, now));
    }

    reveal() {
      if (this.destroyed) return;
      this.emitPhase("gathering");
      for (const { button } of this.planetNodes.values()) button.hidden = true;
      const now = this.time * 1000;
      if (this.reducedMotion || this.userPaused || this.hidden || (this.mode === "chart" && !this.transition)) {
        this.mode = "chart";
        this.transition = null;
        this.render(performance.now());
        this.updatePlanetNodes();
        this.emitPhase("resolved");
        return;
      }
      this.transition = {
        kind: "reveal",
        started: now,
        duration: 3000,
        from: this.capturePositions(now),
      };
      this.lastFrame = 0;
      this.ensureLoop();
    }

    disperse() {
      if (this.destroyed) return;
      this.emitPhase("drifting");
      for (const { button } of this.planetNodes.values()) button.hidden = true;
      const now = this.time * 1000;
      if (this.reducedMotion || this.userPaused || this.hidden || (this.mode === "ambient" && !this.transition)) {
        this.mode = "ambient";
        this.transition = null;
        this.render(performance.now());
        return;
      }
      this.transition = {
        kind: "disperse",
        started: now,
        duration: 1800,
        from: this.capturePositions(now),
      };
      this.lastFrame = 0;
      this.ensureLoop();
    }

    setPaused(paused) {
      this.userPaused = Boolean(paused);
      if (this.userPaused) this.stopLoop();
      else {
        this.lastFrame = 0;
        this.render(performance.now());
        this.ensureLoop();
      }
    }

    selectPlanet(name) {
      this.selected = name && this.anchors.has(name) ? name : null;
      this.selectedAspect = null;
      this.updateRelevant();
      this.updatePlanetNodes();
      this.render(performance.now());
    }

    selectAspect(aspect) {
      this.selectedAspect = aspect
        ? this.aspects.find((candidate) => sameAspect(candidate, aspect)) || null
        : null;
      this.updateRelevant();
      this.render(performance.now());
    }

    updateRelevant() {
      if (this.selectedAspect) {
        this.relevant = new Set([this.selectedAspect.body_1, this.selectedAspect.body_2]);
        return;
      }
      this.relevant = new Set(this.selected ? [this.selected] : []);
      if (this.selected) {
        for (const aspect of this.aspects) {
          if (aspect.body_1 === this.selected) this.relevant.add(aspect.body_2);
          if (aspect.body_2 === this.selected) this.relevant.add(aspect.body_1);
        }
      }
    }

    chartOpacity(now) {
      if (!this.transition) return this.mode === "chart" ? 1 : 0;
      const progress = smoothstep((now - this.transition.started) / this.transition.duration);
      return this.transition.kind === "reveal" ? progress : 1 - progress;
    }

    anchorFor(name) {
      if(this.anchors.has(name)) return this.anchors.get(name);
      const natal=this.chart.natal_chart?.planets?.[name.replace(/^Natal /,'')];
      if(!name.startsWith('Natal ') || !natal) return null;
      const angle=(natal.longitude-90)*Math.PI/180;
      return {x:this.width/2+Math.cos(angle)*this.radius*.97,y:this.height/2-Math.sin(angle)*this.radius*.97,angle};
    }

    drawChartGeometry(opacity) {
      if (opacity <= 0) return;
      const ctx = this.ctx;
      const cx = this.width / 2;
      const cy = this.height / 2;

      ctx.save();
      ctx.strokeStyle = `rgba(173, 204, 232, ${0.22 * opacity})`;
      ctx.lineWidth = 0.7;
      ctx.beginPath();
      ctx.arc(cx, cy, this.radius, 0, TAU);
      ctx.stroke();

      for (let degree = 0; degree < 360; degree += 5) {
        const angle = (degree - 90) * Math.PI / 180;
        const major = degree % 30 === 0;
        const inner = this.radius - (major ? 8 : 3.5);
        const outer = this.radius + (major ? 2 : 0);
        ctx.strokeStyle = `rgba(198, 218, 238, ${(major ? 0.38 : 0.15) * opacity})`;
        ctx.beginPath();
        ctx.moveTo(cx + Math.cos(angle) * inner, cy - Math.sin(angle) * inner);
        ctx.lineTo(cx + Math.cos(angle) * outer, cy - Math.sin(angle) * outer);
        ctx.stroke();
      }

      // Longitude labels turn the expressive field into a readable chart.
      const signs = ['ARI','TAU','GEM','CAN','LEO','VIR','LIB','SCO','SAG','CAP','AQU','PIS'];
      ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
      ctx.font = `${this.width < 420 ? 8 : 10}px sans-serif`;
      signs.forEach((sign,index) => {
        const angle = (index * 30 + 15 - 90) * Math.PI / 180;
        ctx.fillStyle = `rgba(188,207,230,${0.62 * opacity})`;
        ctx.fillText(sign,cx + Math.cos(angle) * this.radius * 1.09,cy - Math.sin(angle) * this.radius * 1.09);
      });
      for (const house of this.chart.whole_sign_cusps || []) {
        const angle = (house.longitude + 15 - 90) * Math.PI / 180;
        ctx.fillStyle = `rgba(175,196,219,${0.55 * opacity})`;
        ctx.fillText(String(house.house),cx + Math.cos(angle) * this.radius * 0.90,cy - Math.sin(angle) * this.radius * 0.90);
      }
      for (const [key,label] of [['ascendant','ASC'],['midheaven','MC']]) {
        if (!this.chart[key]) continue;
        const angle = (this.chart[key].longitude - 90) * Math.PI / 180;
        ctx.strokeStyle = `rgba(226,232,244,${0.7 * opacity})`;
        ctx.beginPath();
        ctx.moveTo(cx + Math.cos(angle) * this.radius * .97,cy - Math.sin(angle) * this.radius * .97);
        ctx.lineTo(cx + Math.cos(angle) * this.radius * 1.05,cy - Math.sin(angle) * this.radius * 1.05);
        ctx.stroke();
        ctx.fillStyle = `rgba(226,232,244,${0.8 * opacity})`;
        ctx.fillText(label,cx + Math.cos(angle) * this.radius * 1.20,cy - Math.sin(angle) * this.radius * 1.20);
      }

      if(this.chart.natal_chart) {
        for(const name of Object.keys(this.chart.natal_chart.planets)) {
          const marker=this.anchorFor('Natal '+name), active=this.relevant.has('Natal '+name);
          if(!marker) continue;
          ctx.fillStyle=`rgba(213,194,157,${(active ? .95 : .35)*opacity})`;
          ctx.beginPath();ctx.arc(marker.x,marker.y,active?4:2,0,TAU);ctx.fill();
          if(active) {
            ctx.font='10px -apple-system, sans-serif';ctx.textAlign='center';
            ctx.fillText('Birth '+name,marker.x+Math.cos(marker.angle)*23,marker.y-Math.sin(marker.angle)*23);
          }
        }
      }
      for (const aspect of this.aspects) {
        const first = this.anchorFor(aspect.body_1);
        const second = this.anchorFor(aspect.body_2);
        if (!first || !second) continue;
        const aspectFocus = Boolean(this.selectedAspect);
        const active = aspectFocus
          ? aspect === this.selectedAspect
          : this.selected && (aspect.body_1 === this.selected || aspect.body_2 === this.selected);
        const faded = aspectFocus ? !active : this.selected && !active;
        const aspectName = String(aspect.aspect || "").toLowerCase();
        const warm = aspectName.includes("square") || aspectName.includes("opposition");
        ctx.strokeStyle = warm
          ? `rgba(190, 184, 216, ${(active ? 0.72 : faded ? 0.025 : 0.1) * opacity})`
          : `rgba(128, 195, 230, ${(active ? 0.78 : faded ? 0.025 : 0.12) * opacity})`;
        ctx.lineWidth = active ? 1.45 : 0.65;
        ctx.beginPath();
        ctx.moveTo(first.x, first.y);
        ctx.lineTo(second.x, second.y);
        ctx.stroke();
        if (active && aspect.aspect === 'graha drishti') {
          const angle = Math.atan2(second.y - first.y, second.x - first.x);
          const tipX = first.x + (second.x - first.x) * 0.7;
          const tipY = first.y + (second.y - first.y) * 0.7;
          ctx.beginPath();
          ctx.moveTo(tipX - Math.cos(angle - 0.5) * 8, tipY - Math.sin(angle - 0.5) * 8);
          ctx.lineTo(tipX, tipY);
          ctx.lineTo(tipX - Math.cos(angle + 0.5) * 8, tipY - Math.sin(angle + 0.5) * 8);
          ctx.stroke();
        }
      }
      ctx.restore();
    }

    drawParticles(now, chartOpacity) {
      const ctx = this.ctx;
      const baseAlpha = ctx.globalAlpha;
      const settledGlow = smoothstep((chartOpacity - 0.55) / 0.45);
      const focused = Boolean(this.selectedAspect || this.selected);
      const ambientBoost = 1 + (1 - chartOpacity) * 0.3;
      for (let index = 0; index < this.particles.length; index += 1) {
        const particle = this.particles[index];
        const point = this.positionFor(particle, index, now);
        const isChartStar = chartOpacity > 0.5 && !particle.decorative;
        const relevant = particle.planet && this.relevant.has(particle.planet);
        const selectedFade = focused && particle.planet && !relevant;
        const twinkle = isChartStar
          ? 0.9 + Math.sin(this.time * particle.twinkleSpeed + particle.twinkle) * 0.1
          : 0.78 + Math.sin(this.time * particle.twinkleSpeed + particle.twinkle) * 0.22;
        let alpha = particle.alpha * twinkle;
        if (isChartStar && particle.wisp) {
          const phase = this.time * particle.flowSpeed + particle.flowPhase;
          const release = Math.pow((1 - Math.cos(phase)) / 2, 2);
          alpha *= 0.82 - release * 0.48;
        }
        if (chartOpacity > 0 && particle.decorative) alpha *= 0.42;
        if (selectedFade) alpha *= 0.28;
        if (relevant) alpha = Math.min(1, alpha * 1.3);
        alpha = Math.min(1, alpha * ambientBoost * (particle.decorative ? 1 : 1 + settledGlow * 0.3));

        // Reuse three opaque colors; avoid parsing a new rgba string for every star.
        // Match rgba's 8-bit alpha rounding to preserve the rendered brightness.
        const color = particle.tint < 0.28 ? "rgb(177, 215, 242)"
          : particle.tint < 0.7 ? "rgb(224, 232, 241)" : "rgb(255, 255, 255)";
        const size = particle.size * (0.72 + particle.depth * 0.36) * ambientBoost;
        ctx.fillStyle = color;

        if (particle.bright && alpha > 0.2) {
          ctx.globalAlpha = baseAlpha * Math.round(alpha * (0.12 + (particle.decorative ? 0 : settledGlow * 0.04)) * 255) / 255;
          ctx.beginPath();
          ctx.arc(point.x, point.y, size * 3.2, 0, TAU);
          ctx.fill();
        }
        ctx.globalAlpha = baseAlpha * Math.round(alpha * 255) / 255;
        ctx.beginPath();
        ctx.arc(point.x, point.y, size, 0, TAU);
        ctx.fill();
      }
      ctx.globalAlpha = baseAlpha;
    }

    drawAnchors(opacity) {
      if (opacity <= 0) return;
      const ctx = this.ctx;
      ctx.save();
      ctx.textAlign = "center";
      ctx.textBaseline = "middle";

      for (const [name, anchor] of this.anchors) {
        const aspectFocus = Boolean(this.selectedAspect);
        const active = aspectFocus ? this.relevant.has(name) : name === this.selected;
        const relevant = this.relevant.has(name);
        const faded = (aspectFocus || this.selected) && !relevant;
        const halo = active ? this.glyphSize() * 0.72 : relevant ? this.glyphSize() * 0.58 : 6;
        const gradient = ctx.createRadialGradient(anchor.x, anchor.y, 0, anchor.x, anchor.y, halo);
        gradient.addColorStop(0, `rgba(223, 242, 255, ${(active ? 0.20 : relevant ? 0.12 : 0.06) * opacity})`);
        gradient.addColorStop(1, "rgba(130, 190, 230, 0)");
        ctx.fillStyle = gradient;
        ctx.beginPath();
        ctx.arc(anchor.x, anchor.y, halo, 0, TAU);
        ctx.fill();

        if (!faded && (active || relevant)) {
          ctx.strokeStyle = `rgba(218, 235, 250, ${(active ? 0.32 : 0.2) * opacity})`;
          ctx.lineWidth = 0.7;
          ctx.beginPath();
          ctx.arc(anchor.x, anchor.y, this.glyphSize() * 0.62, 0, TAU);
          ctx.stroke();
        }
      }
      ctx.restore();
    }

    render(now) {
      if (this.destroyed || !this.ctx) return;
      const motionNow = this.time * 1000;
      this.ctx.clearRect(0, 0, this.width, this.height);
      const opacity = this.chartOpacity(motionNow);
      if (opacity !== this.lastRevealProgress) {
        this.lastRevealProgress = opacity;
        this.onRevealProgress?.(opacity);
      }
      this.drawChartGeometry(opacity);
      this.drawParticles(motionNow, opacity);
      this.drawAnchors(opacity);

      if (this.transition && motionNow - this.transition.started >= this.transition.duration) {
        const kind = this.transition.kind;
        this.mode = kind === "reveal" ? "chart" : "ambient";
        this.transition = null;
        this.updatePlanetNodes();
        if (kind === "reveal") this.emitPhase("resolved");
      }
    }

    frame = (now) => {
      this.raf = null;
      if (this.destroyed || this.userPaused || this.hidden || this.reducedMotion) return;
      if (this.lastFrame) this.time += Math.min(0.05, (now - this.lastFrame) / 1000);
      this.lastFrame = now;
      this.render(now);
      this.ensureLoop();
    };

    ensureLoop() {
      if (this.raf !== null || this.destroyed || this.userPaused || this.hidden || this.reducedMotion) return;
      this.raf = requestAnimationFrame(this.frame);
    }

    stopLoop() {
      if (this.raf !== null) cancelAnimationFrame(this.raf);
      this.raf = null;
    }

    emitPhase(phase) {
      if (!this.onPhase) return;
      const callback = this.onPhase;
      const schedule = typeof queueMicrotask === "function"
        ? queueMicrotask
        : (task) => Promise.resolve().then(task);
      schedule(() => {
        if (!this.destroyed && this.onPhase === callback) callback(phase);
      });
    }

    destroy() {
      if (this.destroyed) return;
      this.destroyed = true;
      this.stopLoop();
      document.removeEventListener("visibilitychange", this.handleVisibility);
      if (this.motionQuery.removeEventListener) {
        this.motionQuery.removeEventListener("change", this.handleMotionPreference);
      } else {
        this.motionQuery.removeListener(this.handleMotionPreference);
      }
      if (this.resizeObserver) this.resizeObserver.disconnect();
      if (this.handleWindowResize) window.removeEventListener("resize", this.handleWindowResize);
      for (const { button, handleSelect } of this.planetNodes.values()) {
        button.removeEventListener("click", handleSelect);
        button.remove();
      }
      this.planetNodes.clear();
      this.particles.length = 0;
      this.anchors.clear();
      this.selectedAspect = null;
      this.ctx.clearRect(0, 0, this.width, this.height);
      this.onPhase = null;
      this.onRevealProgress = null;
      this.onSelect = null;
      this.nodeLayer = null;
    }
  }

  globalThis.CelestialField = CelestialField;
})();
