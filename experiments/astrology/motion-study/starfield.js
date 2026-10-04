(function () {
  "use strict";

  const TAU = Math.PI * 2;
  const GLYPHS = {
    Sun: "☉", Moon: "☽", Mercury: "☿", Venus: "♀", Mars: "♂",
    Jupiter: "♃", Saturn: "♄", Uranus: "♅", Neptune: "♆", Pluto: "♇",
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

  class CelestialField {
    constructor(canvas, chart, options = {}) {
      if (!(canvas instanceof HTMLCanvasElement)) {
        throw new TypeError("CelestialField requires a canvas element.");
      }

      this.canvas = canvas;
      this.ctx = canvas.getContext("2d", { alpha: true });
      this.chart = chart || {};
      this.onPhase = typeof options.onPhase === "function" ? options.onPhase : null;
      this.planetNames = Object.keys(this.chart.planets || {}).filter((name) =>
        Number.isFinite(Number(this.chart.planets[name]?.longitude))
      );
      this.aspects = Array.isArray(this.chart.major_aspects) ? this.chart.major_aspects : [];
      this.selected = null;
      this.relevant = new Set();
      this.particles = [];
      this.anchors = new Map();
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

      this.resize();
      this.createParticles();
      this.render(performance.now());

      if (this.reducedMotion) this.emitPhase("resolved");
      else this.ensureLoop();
    }

    createParticles() {
      let seed = 0x51a7f1e1;
      for (const name of this.planetNames) {
        const longitude = Math.round(Number(this.chart.planets[name].longitude) * 1000);
        seed = Math.imul(seed ^ longitude, 16777619);
      }
      const random = makeRandom(seed);
      const isMobile = window.matchMedia("(max-width: 700px)").matches;
      const count = isMobile ? 720 : 1500;
      const clusteredCount = Math.floor(count * 0.86);

      for (let index = 0; index < count; index += 1) {
        const decorative = index >= clusteredCount || this.planetNames.length === 0;
        const depth = 0.35 + random() * 0.65;
        const ambientRadius = Math.pow(random(), 0.64);
        const arm = index % 5;
        const ambientAngle = (arm / 5) * TAU + ambientRadius * 7.6 + (random() - 0.5) * 0.72;
        const bright = random() > 0.982;
        const planetIndex = decorative ? -1 : index % this.planetNames.length;
        const cloudDistance = Math.pow(random(), 0.66);
        const cloudArm = index % 3;

        this.particles.push({
          decorative,
          planet: planetIndex >= 0 ? this.planetNames[planetIndex] : null,
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
          cloudDistance,
          cloudAngle: (cloudArm / 3) * TAU + cloudDistance * 4.4 + (random() - 0.5) * 0.58,
        });
      }
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

      if (this.transition && oldWidth > 1 && oldHeight > 1) {
        const sx = this.width / oldWidth;
        const sy = this.height / oldHeight;
        for (const point of this.transition.from) {
          point.x *= sx;
          point.y *= sy;
        }
      }
      this.render(performance.now());
    }

    buildAnchors() {
      this.anchors.clear();
      const cx = this.width / 2;
      const cy = this.height / 2;
      this.planetNames.forEach((name, index) => {
        const longitude = Number(this.chart.planets[name].longitude);
        const angle = (longitude - 90) * Math.PI / 180;
        const distance = this.radius * (index % 2 === 0 ? 0.62 : 0.76);
        this.anchors.set(name, {
          x: cx + Math.cos(angle) * distance,
          y: cy - Math.sin(angle) * distance,
          angle,
        });
      });
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
      const cloudRadius = this.radius * (0.016 + particle.cloudDistance * 0.072);
      const angle = particle.cloudAngle + anchor.angle * 0.34 + atTime * 0.12;
      return {
        x: anchor.x + Math.cos(angle) * cloudRadius,
        y: anchor.y + Math.sin(angle) * cloudRadius * 0.62,
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
      const now = this.time * 1000;
      if (this.reducedMotion || this.userPaused || this.hidden || (this.mode === "chart" && !this.transition)) {
        this.mode = "chart";
        this.transition = null;
        this.render(performance.now());
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
      this.relevant = new Set(this.selected ? [this.selected] : []);
      if (this.selected) {
        for (const aspect of this.aspects) {
          if (aspect.body_1 === this.selected) this.relevant.add(aspect.body_2);
          if (aspect.body_2 === this.selected) this.relevant.add(aspect.body_1);
        }
      }
      this.render(performance.now());
    }

    chartOpacity(now) {
      if (!this.transition) return this.mode === "chart" ? 1 : 0;
      const progress = smoothstep((now - this.transition.started) / this.transition.duration);
      return this.transition.kind === "reveal" ? progress : 1 - progress;
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

      for (const aspect of this.aspects) {
        const first = this.anchors.get(aspect.body_1);
        const second = this.anchors.get(aspect.body_2);
        if (!first || !second) continue;
        const active = this.selected && (aspect.body_1 === this.selected || aspect.body_2 === this.selected);
        const faded = this.selected && !active;
        const aspectName = String(aspect.aspect || "").toLowerCase();
        const warm = aspectName.includes("square") || aspectName.includes("opposition");
        ctx.strokeStyle = warm
          ? `rgba(190, 184, 216, ${(active ? 0.44 : faded ? 0.035 : 0.1) * opacity})`
          : `rgba(128, 195, 230, ${(active ? 0.52 : faded ? 0.035 : 0.12) * opacity})`;
        ctx.lineWidth = active ? 1.15 : 0.65;
        ctx.beginPath();
        ctx.moveTo(first.x, first.y);
        ctx.lineTo(second.x, second.y);
        ctx.stroke();
      }
      ctx.restore();
    }

    drawParticles(now, chartOpacity) {
      const ctx = this.ctx;
      for (let index = 0; index < this.particles.length; index += 1) {
        const particle = this.particles[index];
        const point = this.positionFor(particle, index, now);
        const isChartStar = chartOpacity > 0.5 && !particle.decorative;
        const relevant = particle.planet && this.relevant.has(particle.planet);
        const selectedFade = this.selected && particle.planet && !relevant;
        const twinkle = isChartStar ? 1 : 0.78 + Math.sin(this.time * particle.twinkleSpeed + particle.twinkle) * 0.22;
        let alpha = particle.alpha * twinkle;
        if (chartOpacity > 0 && particle.decorative) alpha *= 0.42;
        if (selectedFade) alpha *= 0.28;
        if (relevant) alpha = Math.min(1, alpha * 1.3);
        const ambientBoost = 1 + (1 - chartOpacity) * 0.3;
        alpha = Math.min(1, alpha * ambientBoost);

        const color = particle.tint < 0.28 ? "177, 215, 242"
          : particle.tint < 0.7 ? "224, 232, 241" : "255, 255, 255";
        const size = particle.size * (0.72 + particle.depth * 0.36) * ambientBoost;

        if (particle.bright && alpha > 0.2) {
          ctx.fillStyle = `rgba(${color}, ${alpha * 0.12})`;
          ctx.beginPath();
          ctx.arc(point.x, point.y, size * 3.2, 0, TAU);
          ctx.fill();
        }
        ctx.fillStyle = `rgba(${color}, ${alpha})`;
        ctx.beginPath();
        ctx.arc(point.x, point.y, size, 0, TAU);
        ctx.fill();
      }
    }

    drawAnchors(opacity) {
      if (opacity <= 0) return;
      const ctx = this.ctx;
      ctx.save();
      ctx.textAlign = "center";
      ctx.textBaseline = "middle";
      ctx.font = `${clamp(this.radius * 0.045, 10, 14)}px Georgia, serif`;

      for (const [name, anchor] of this.anchors) {
        const active = name === this.selected;
        const relevant = this.relevant.has(name);
        const faded = this.selected && !relevant;
        const halo = active ? 16 : relevant ? 10 : 6;
        const gradient = ctx.createRadialGradient(anchor.x, anchor.y, 0, anchor.x, anchor.y, halo);
        gradient.addColorStop(0, `rgba(223, 242, 255, ${(active ? 0.9 : relevant ? 0.56 : 0.35) * opacity})`);
        gradient.addColorStop(1, "rgba(130, 190, 230, 0)");
        ctx.fillStyle = gradient;
        ctx.beginPath();
        ctx.arc(anchor.x, anchor.y, halo, 0, TAU);
        ctx.fill();

        ctx.fillStyle = `rgba(239, 247, 255, ${(faded ? 0.18 : active ? 0.98 : 0.85) * opacity})`;
        ctx.beginPath();
        ctx.arc(anchor.x, anchor.y, active ? 2.25 : 1.45, 0, TAU);
        ctx.fill();

        const glyph = GLYPHS[name];
        if (glyph) {
          const offset = 10 + (active ? 3 : 0);
          ctx.fillStyle = `rgba(218, 232, 246, ${(faded ? 0.12 : active ? 0.9 : 0.38) * opacity})`;
          ctx.fillText(glyph, anchor.x + Math.cos(anchor.angle) * offset, anchor.y - Math.sin(anchor.angle) * offset);
        }
      }
      ctx.restore();
    }

    render(now) {
      if (this.destroyed || !this.ctx) return;
      const motionNow = this.time * 1000;
      this.ctx.clearRect(0, 0, this.width, this.height);
      const opacity = this.chartOpacity(motionNow);
      this.drawChartGeometry(opacity);
      this.drawParticles(motionNow, opacity);
      this.drawAnchors(opacity);

      if (this.transition && motionNow - this.transition.started >= this.transition.duration) {
        const kind = this.transition.kind;
        this.mode = kind === "reveal" ? "chart" : "ambient";
        this.transition = null;
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
      this.particles.length = 0;
      this.anchors.clear();
      this.ctx.clearRect(0, 0, this.width, this.height);
      this.onPhase = null;
    }
  }

  globalThis.CelestialField = CelestialField;
})();
