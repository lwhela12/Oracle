(function () {
    'use strict';

    const formats = {
        story: { w: 1080, h: 1920, label: '1080 × 1920 · PNG' },
        post:  { w: 1080, h: 1080, label: '1080 × 1080 · PNG' }
    };
    const SERIF = "'Cormorant Garamond', Georgia, 'Times New Roman', serif";
    const DISPLAY = "'Cinzel', 'Cormorant Garamond', Georgia, serif";
    const SANS = "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif";
    let fontsReady = null;

    function ensureFonts() {
        if (!fontsReady) {
            fontsReady = (document.fonts && document.fonts.load)
                ? Promise.all([
                    document.fonts.load('700 48px "Cormorant Garamond"'),
                    document.fonts.load('600 24px Cinzel')
                ]).catch(() => {})
                : Promise.resolve();
        }
        return fontsReady;
    }

    function font(weight, size, family) {
        return `${weight} ${size}px ${family}`;
    }

    function drawTrackedText(ctx, text, cx, y, tracking) {
        if ('letterSpacing' in ctx) {
            ctx.letterSpacing = `${tracking}px`;
            ctx.textAlign = 'center';
            ctx.fillText(text, cx + tracking / 2, y);
            ctx.letterSpacing = '0px';
            return;
        }
        const chars = [...text];
        const widths = chars.map(c => ctx.measureText(c).width);
        const total = widths.reduce((a, b) => a + b, 0) + tracking * (chars.length - 1);
        let x = cx - total / 2;
        ctx.textAlign = 'left';
        chars.forEach((c, i) => {
            ctx.fillText(c, x, y);
            x += widths[i] + tracking;
        });
    }

    function wrapLines(ctx, text, maxWidth) {
        const words = text.split(/\s+/).filter(Boolean);
        const lines = [];
        let line = '';
        for (const word of words) {
            const test = line ? `${line} ${word}` : word;
            if (!line || ctx.measureText(test).width <= maxWidth) {
                line = test;
            } else {
                lines.push(line);
                line = word;
            }
        }
        if (line) lines.push(line);
        return lines;
    }

    function balanceLines(ctx, text, maxWidth, lines) {
        if (lines.length < 2) return lines;
        const spreadOf = (ls) => {
            const ws = ls.map(l => ctx.measureText(l).width);
            return Math.max(...ws) - Math.min(...ws);
        };
        let best = lines;
        let bestSpread = spreadOf(lines);
        for (let f = 0.97; f >= 0.7; f -= 0.03) {
            const cand = wrapLines(ctx, text, maxWidth * f);
            if (cand.length !== lines.length) break;
            const spread = spreadOf(cand);
            if (spread < bestSpread) { best = cand; bestSpread = spread; }
        }
        return best;
    }

    function fitQuote(ctx, text, maxWidth, maxHeight, maxSize, minSize, lhRatio) {
        for (let size = maxSize; size >= minSize; size -= 2) {
            ctx.font = font(700, size, SERIF);
            const lines = wrapLines(ctx, text, maxWidth);
            const lineHeight = Math.round(size * lhRatio);
            if (lines.length * lineHeight <= maxHeight && lines.every(line => ctx.measureText(line).width <= maxWidth)) {
                return { size, lines: balanceLines(ctx, text, maxWidth, lines), lineHeight };
            }
        }
        ctx.font = font(700, minSize, SERIF);
        const lines = wrapLines(ctx, text, maxWidth);
        const lineHeight = Math.round(minSize * lhRatio);
        const maxLines = Math.max(1, Math.floor(maxHeight / lineHeight));
        if (lines.length > maxLines) {
            lines.length = maxLines;
            let last = lines[maxLines - 1];
            while (last.length > 3 && ctx.measureText(`${last}…`).width > maxWidth) last = last.slice(0, -1).trimEnd();
            lines[maxLines - 1] = `${last.replace(/[,.;:\s]+$/, '')}…`;
        }
        return { size: minSize, lines, lineHeight };
    }

    function drawAmbientFill(ctx, snapshot, width, height) {
        const { canvas: source, content } = snapshot;
        const targetAspect = width / height;
        let sx = content.x;
        let sy = content.y;
        let sw = content.w;
        let sh = content.h;
        if (sw / sh > targetAspect) {
            sw = sh * targetAspect;
            sx = content.x + (content.w - sw) / 2;
        } else {
            sh = sw / targetAspect;
            sy = content.y + (content.h - sh) / 2;
        }
        const small = document.createElement('canvas');
        small.width = 12;
        small.height = Math.max(1, Math.round(12 / targetAspect));
        const smallCtx = small.getContext('2d');
        smallCtx.imageSmoothingEnabled = true;
        smallCtx.imageSmoothingQuality = 'high';
        smallCtx.drawImage(source, sx, sy, sw, sh, 0, 0, small.width, small.height);

        const mid = document.createElement('canvas');
        mid.width = 72;
        mid.height = Math.max(1, Math.round(72 / targetAspect));
        const midCtx = mid.getContext('2d');
        midCtx.imageSmoothingEnabled = true;
        midCtx.imageSmoothingQuality = 'high';
        midCtx.drawImage(small, 0, 0, mid.width, mid.height);

        ctx.save();
        ctx.globalAlpha = 0.88;
        const over = 1.08;
        ctx.drawImage(mid, -(width * (over - 1)) / 2, -(height * (over - 1)) / 2, width * over, height * over);
        ctx.restore();
    }

    function drawFallbackAmbient(ctx, width, height) {
        const gradient = ctx.createRadialGradient(width / 2, height * 0.45, 0, width / 2, height * 0.45, Math.max(width, height) * 0.7);
        gradient.addColorStop(0, 'rgba(120, 82, 40, 0.55)');
        gradient.addColorStop(0.5, 'rgba(40, 24, 50, 0.6)');
        gradient.addColorStop(1, 'rgba(8, 6, 18, 1)');
        ctx.fillStyle = gradient;
        ctx.fillRect(0, 0, width, height);
    }

    function roundRect(ctx, x, y, width, height, radius) {
        const r = Math.max(0, Math.min(radius, width / 2, height / 2));
        ctx.beginPath();
        ctx.moveTo(x + r, y);
        ctx.lineTo(x + width - r, y);
        ctx.arcTo(x + width, y, x + width, y + r, r);
        ctx.lineTo(x + width, y + height - r);
        ctx.arcTo(x + width, y + height, x + width - r, y + height, r);
        ctx.lineTo(x + r, y + height);
        ctx.arcTo(x, y + height, x, y + height - r, r);
        ctx.lineTo(x, y + r);
        ctx.arcTo(x, y, x + r, y, r);
        ctx.closePath();
    }

    function drawFramedArt(ctx, snapshot, art, radius) {
        const { canvas: source, content } = snapshot;
        const x = Math.round(art.x);
        const y = Math.round(art.y);
        const width = Math.round(art.w);
        const height = Math.round(art.h);
        if (width < 2 || height < 2) return;

        ctx.save();
        ctx.shadowColor = 'rgba(0, 0, 0, 0.7)';
        ctx.shadowBlur = 54;
        ctx.shadowOffsetY = 22;
        ctx.fillStyle = '#0a0812';
        roundRect(ctx, x, y, width, height, radius);
        ctx.fill();
        ctx.restore();

        ctx.save();
        roundRect(ctx, x, y, width, height, radius);
        ctx.clip();
        ctx.drawImage(source, content.x, content.y, content.w, content.h, x, y, width, height);
        ctx.restore();

        ctx.save();
        ctx.strokeStyle = 'rgba(229, 193, 88, 0.34)';
        ctx.lineWidth = 2;
        roundRect(ctx, x + 1, y + 1, width - 2, height - 2, Math.max(0, radius - 1));
        ctx.stroke();
        ctx.restore();
    }

    function computeLayout(ctx, format, width, height, snapshot, quote) {
        const isStory = format === 'story';
        const aspect = snapshot ? snapshot.content.w / Math.max(1, snapshot.content.h) : 1;
        const layout = {
            W: width,
            H: height,
            isStory,
            headerY: isStory ? 250 : 92,
            footerY: isStory ? height - 250 : height - 72,
            art: null,
            quote: null
        };
        const contentTop = isStory ? 300 : 156;
        const contentBottom = isStory ? height - 330 : height - 150;
        const zoneHeight = contentBottom - contentTop;
        const attributionHeight = isStory ? 24 : 20;
        const attributionGap = isStory ? 40 : 30;

        if (!isStory && snapshot && aspect < 1.2) {
            const margin = 64;
            const columnGap = 44;
            const artColumnWidth = 470;
            let artWidth = artColumnWidth;
            let artHeight = artWidth / aspect;
            if (artHeight > zoneHeight) { artHeight = zoneHeight; artWidth = artHeight * aspect; }
            layout.art = { x: margin + (artColumnWidth - artWidth) / 2, y: contentTop + (zoneHeight - artHeight) / 2, w: artWidth, h: artHeight };

            const quoteX = margin + artColumnWidth + columnGap;
            const quoteWidth = width - margin - quoteX;
            const fit = fitQuote(ctx, quote, quoteWidth, zoneHeight - attributionGap - attributionHeight, 46, 26, 1.22);
            const quoteHeight = fit.lines.length * fit.lineHeight;
            const blockHeight = quoteHeight + attributionGap + attributionHeight;
            const top = contentTop + (zoneHeight - blockHeight) / 2;
            layout.quote = { cx: quoteX + quoteWidth / 2, top, width: quoteWidth, fit, attrY: top + quoteHeight + attributionGap + attributionHeight * 0.75 };
            return layout;
        }

        const tall = snapshot && aspect < 0.85;
        const artMaxWidth = isStory ? 940 : 960;
        const artCapHeight = isStory ? 1060 : 540;
        const artMinHeight = isStory ? 560 : 300;
        const artGap = isStory ? 52 : 48;
        const quoteMaxWidth = isStory ? 900 : 920;
        const quoteMaxSize = isStory ? (tall ? 56 : 62) : 50;
        const quoteMinSize = isStory ? 40 : 28;
        const quoteBlockCap = isStory ? (tall ? 270 : 330) : 240;

        let fit = fitQuote(ctx, quote, quoteMaxWidth, quoteBlockCap, quoteMaxSize, quoteMinSize, 1.22);
        let quoteHeight = fit.lines.length * fit.lineHeight;
        let art = null;
        if (snapshot) {
            let availableArtHeight = zoneHeight - quoteHeight - attributionGap - attributionHeight - artGap;
            if (availableArtHeight < artMinHeight) {
                fit = fitQuote(ctx, quote, quoteMaxWidth, Math.max(80, zoneHeight - artMinHeight - artGap - attributionGap - attributionHeight), quoteMaxSize, quoteMinSize, 1.22);
                quoteHeight = fit.lines.length * fit.lineHeight;
                availableArtHeight = zoneHeight - quoteHeight - attributionGap - attributionHeight - artGap;
            }
            let artHeight = Math.min(artCapHeight, Math.max(artMinHeight, availableArtHeight));
            let artWidth = artHeight * aspect;
            if (artWidth > artMaxWidth) { artWidth = artMaxWidth; artHeight = artWidth / aspect; }
            art = { w: artWidth, h: artHeight };
        }
        const groupHeight = (art ? art.h + artGap : 0) + quoteHeight + attributionGap + attributionHeight;
        let y = contentTop + Math.max(0, (zoneHeight - groupHeight) * 0.42);
        if (art) {
            layout.art = { x: (width - art.w) / 2, y, w: art.w, h: art.h };
            y += art.h + artGap;
        }
        layout.quote = { cx: width / 2, top: y, width: quoteMaxWidth, fit, attrY: y + quoteHeight + attributionGap + attributionHeight * 0.75 };
        return layout;
    }

    function drawType(ctx, layout, title, quote) {
        const { isStory } = layout;
        ctx.textBaseline = 'alphabetic';

        ctx.save();
        ctx.font = font(600, isStory ? 27 : 23, SANS);
        ctx.fillStyle = 'rgba(255, 255, 255, 0.74)';
        ctx.shadowColor = 'rgba(0, 0, 0, 0.9)';
        ctx.shadowBlur = 12;
        ctx.shadowOffsetY = 2;
        drawTrackedText(ctx, title, layout.W / 2, layout.headerY, isStory ? 7 : 6);
        ctx.restore();

        const quoteLayout = layout.quote;
        ctx.save();
        ctx.font = font(700, quoteLayout.fit.size, SERIF);
        ctx.fillStyle = '#ffffff';
        ctx.textAlign = 'center';
        ctx.shadowColor = 'rgba(0, 0, 0, 0.95)';
        ctx.shadowBlur = 22;
        ctx.shadowOffsetY = 3;
        let y = quoteLayout.top + quoteLayout.fit.size * 0.82;
        quoteLayout.fit.lines.forEach(line => {
            ctx.fillText(line, quoteLayout.cx, y);
            y += quoteLayout.fit.lineHeight;
        });
        ctx.restore();

        ctx.save();
        ctx.font = font(600, isStory ? 21 : 18, DISPLAY);
        ctx.fillStyle = 'rgba(255, 255, 255, 0.78)';
        ctx.shadowColor = 'rgba(0, 0, 0, 0.9)';
        ctx.shadowBlur = 10;
        ctx.shadowOffsetY = 2;
        drawTrackedText(ctx, '— THE QUANTUM ORACLE', quoteLayout.cx, quoteLayout.attrY, isStory ? 5 : 4);
        ctx.restore();

        ctx.save();
        ctx.font = font(300, isStory ? 28 : 24, SANS);
        ctx.fillStyle = 'rgba(255, 255, 255, 0.56)';
        ctx.shadowColor = 'rgba(0, 0, 0, 0.8)';
        ctx.shadowBlur = 8;
        ctx.shadowOffsetY = 1;
        drawTrackedText(ctx, 'qoracle.app', layout.W / 2, layout.footerY, isStory ? 6 : 5);
        ctx.restore();
    }

    function compose({ format = 'story', title, quote, snapshot }) {
        const resolvedFormat = formats[format] ? format : 'story';
        const spec = formats[resolvedFormat];
        const width = spec.w;
        const height = spec.h;
        const canvas = document.createElement('canvas');
        canvas.width = width;
        canvas.height = height;
        const ctx = canvas.getContext('2d');
        ctx.imageSmoothingEnabled = true;
        ctx.imageSmoothingQuality = 'high';

        ctx.fillStyle = '#080612';
        ctx.fillRect(0, 0, width, height);
        if (snapshot) drawAmbientFill(ctx, snapshot, width, height);
        else drawFallbackAmbient(ctx, width, height);

        let gradient = ctx.createLinearGradient(0, 0, 0, height);
        gradient.addColorStop(0, 'rgba(6, 4, 14, 0.62)');
        gradient.addColorStop(0.35, 'rgba(6, 4, 14, 0.24)');
        gradient.addColorStop(0.7, 'rgba(6, 4, 14, 0.46)');
        gradient.addColorStop(1, 'rgba(6, 4, 14, 0.80)');
        ctx.fillStyle = gradient;
        ctx.fillRect(0, 0, width, height);

        const layout = computeLayout(ctx, resolvedFormat, width, height, snapshot, quote);
        if (snapshot && layout.art) drawFramedArt(ctx, snapshot, layout.art, layout.isStory ? 30 : 26);

        const vignette = ctx.createRadialGradient(width / 2, height / 2, Math.min(width, height) * 0.42, width / 2, height / 2, Math.hypot(width, height) * 0.58);
        vignette.addColorStop(0, 'rgba(4, 3, 8, 0)');
        vignette.addColorStop(1, 'rgba(4, 3, 8, 0.62)');
        ctx.fillStyle = vignette;
        ctx.fillRect(0, 0, width, height);

        if (layout.quote) {
            const quoteLayout = layout.quote;
            const quoteHeight = quoteLayout.fit.lines.length * quoteLayout.fit.lineHeight;
            const centerY = quoteLayout.top + quoteHeight / 2;
            const radiusX = quoteLayout.width * 0.72;
            const radiusY = quoteHeight * 0.9 + 120;
            ctx.save();
            ctx.translate(quoteLayout.cx, centerY);
            ctx.scale(radiusX / radiusY, 1);
            const halo = ctx.createRadialGradient(0, 0, 0, 0, 0, radiusY);
            halo.addColorStop(0, 'rgba(6, 4, 14, 0.5)');
            halo.addColorStop(0.6, 'rgba(6, 4, 14, 0.28)');
            halo.addColorStop(1, 'rgba(6, 4, 14, 0)');
            ctx.fillStyle = halo;
            ctx.fillRect(-radiusY * 2, -radiusY, radiusY * 4, radiusY * 2);
            ctx.restore();
        }

        drawType(ctx, layout, title, quote);
        return canvas;
    }

    window.OracleShareCard = Object.freeze({ formats, ensureFonts, compose });
}());
