/* Export existing reading content locally; no generation or server storage. */
function readingMarkdownText(markdown) {
    const root = document.createElement('div');
    root.innerHTML = renderMarkdown(markdown || '');
    root.querySelectorAll('br').forEach(el => el.replaceWith('\n'));
    root.querySelectorAll('li').forEach(el => el.prepend('• '));
    root.querySelectorAll('p,h1,h2,h3,h4,h5,h6,li,blockquote,pre,tr').forEach(el => el.append('\n\n'));
    root.querySelectorAll('td,th').forEach(el => el.append(' | '));
    return root.textContent.replace(/[ \t]+\n/g, '\n').replace(/\n{3,}/g, '\n\n').trim();
}
function fullReadingExport() {
    const data = currentReadingData || {};
    const layers = currentReadingLayers;
    const sections = [];
    const add = (title, text) => { if (text?.trim()) sections.push({title, text:text.trim()}); };
    const symbols = data.cards || data.runes || [];
    const symbolName = index => {
        const item = symbols[index];
        return item ? `${data.positions?.[index] || `Symbol ${index + 1}`}: ${item.name}${item.is_reversed || item.reversed ? ' (reversed)' : ''}` : `Symbol ${index + 1}`;
    };
    if (symbols.length) add('Your spread', symbols.map((_,index) => symbolName(index)).join('\n'));
    if (data.hexagram) {
        const hex = data.hexagram;
        add('Your cast', [`Hexagram ${hex.number}: ${hex.name}`, hex.changing_lines?.length ? `Changing lines: ${hex.changing_lines.join(', ')}` : 'No changing lines', hex.transformed ? `Becoming Hexagram ${hex.transformed.number}: ${hex.transformed.name}` : ''].filter(Boolean).join('\n'));
    }
    if (data.quantum_number != null) add('Your number', String(data.quantum_number));
    add('At the heart of your reading', readingMarkdownText(layers.heart));
    add(layers.heart ? 'The full interpretation' : 'Your reading', readingMarkdownText(layers.depth));
    Object.entries(layers.symbols || {}).sort(([a],[b]) => Number(a)-Number(b)).forEach(([number, value]) => {
        add(symbolName(Number(number)-1), [value.brief, value.depth].filter(Boolean).map(readingMarkdownText).join('\n\n'));
    });
    // Built-in visual demos predate layered readings.
    if (!layers.heart && !layers.depth && !Object.keys(layers.symbols || {}).length) add('Your reading', oracleStreamText.innerText);
    return {title:getReadingSpreadTitle(currentTradition, data), sections};
}
function fullReadingText(reading = fullReadingExport()) {
    return ['Quantum Oracle', reading.title, ...reading.sections.map(s => `${s.title}\n${s.text}`), 'qoracle.app'].join('\n\n');
}
async function copyFullReading() {
    const feedback = document.getElementById('socialShareFeedback');
    const text = fullReadingText();
    try {
        if (navigator.clipboard?.writeText) await navigator.clipboard.writeText(text);
        else {
            const field = document.createElement('textarea');
            field.value = text;
            field.style.cssText = 'position:fixed;opacity:0;pointer-events:none';
            document.getElementById('socialExportModal').append(field);
            field.select();
            let copied;
            try { copied = document.execCommand('copy'); } finally { field.remove(); document.getElementById('copyReadingBtn').focus(); }
            if (!copied) throw new Error('Clipboard unavailable');
        }
        feedback.textContent = 'Full reading copied.';
    } catch (_) { feedback.textContent = 'Copy was blocked by your browser. You can download the PDF instead.'; }
}
function readingPdfSpread(snapshot) {
    if (!snapshot?.canvas || !snapshot.content) throw new Error('Spread image unavailable');
    const {x,y,w,h} = snapshot.content;
    if (w <= 0 || h <= 0) throw new Error('Spread image is empty');
    const canvas = document.createElement('canvas');
    canvas.width = Math.ceil(w); canvas.height = Math.ceil(h);
    const ctx = canvas.getContext('2d');
    ctx.fillStyle = '#101017'; ctx.fillRect(0,0,canvas.width,canvas.height);
    ctx.drawImage(snapshot.canvas,x,y,w,h,0,0,canvas.width,canvas.height);
    return canvas.toDataURL('image/jpeg',0.94);
}
function generateReadingPdf(reading, spreadImage) {
    return new Promise((resolve,reject) => {
        const worker = new Worker('/static/reading-pdf-worker.js?v=20260915a');
        const finish = (error, blob) => {
            clearTimeout(timer);
            worker.terminate();
            if (error) reject(error); else resolve(blob);
        };
        const timer = setTimeout(() => finish(new Error('PDF generation timed out')),45000);
        worker.onmessage = event => {
            if (event.data.error) finish(new Error(event.data.error));
            else if (event.data.blob instanceof Blob) finish(null,event.data.blob);
            else finish(new Error('Invalid PDF result'));
        };
        worker.onerror = event => { event.preventDefault(); finish(new Error('PDF generation failed')); };
        worker.postMessage({reading,spreadImage});
    });
}
async function downloadReadingPdf() {
    const button = document.getElementById('downloadReadingPdfBtn');
    const feedback = document.getElementById('socialShareFeedback');
    if (button.disabled) return;
    const label = button.querySelector('.pdf-button-label');
    const reading = fullReadingExport();
    const snapshot = talismanSnapshotPromise || Promise.resolve(talismanSnapshot);
    button.disabled = true;
    button.setAttribute('aria-busy','true');
    label.textContent = 'Preparing…';
    feedback.textContent = 'Preparing your PDF…';
    try {
        // Give the busy state a paint before cropping the spread image.
        await new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)));
        const altar = await snapshot;
        const spreadImage = readingPdfSpread(altar);
        const blob = await generateReadingPdf(reading,spreadImage);
        const url = URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.download = `qoracle-${reading.title.toLowerCase().replace(/[^a-z0-9]+/g,'-').replace(/-$/,'')}.pdf`;
        document.body.append(link); link.click(); link.remove();
        setTimeout(() => URL.revokeObjectURL(url),60000);
        feedback.textContent = 'Your PDF is ready.';
    } catch (_) { feedback.textContent = 'The PDF could not be prepared. Please try again, or copy the reading.'; }
    finally {
        button.disabled = false;
        button.removeAttribute('aria-busy');
        label.textContent = 'Download PDF';
    }
}
