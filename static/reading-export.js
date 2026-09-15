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
    if (document.getElementById('exportIncludeQuestion').checked) add('Your question', seekerInquiryDisplay.textContent);
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
let readingPdfLibrary;
function loadReadingPdfLibrary() {
    if (!readingPdfLibrary) {
        const load = src => new Promise((resolve,reject) => {
            const script = document.createElement('script');
            script.src = src;
            script.onload = resolve;
            script.onerror = () => { script.remove(); reject(new Error('PDF library unavailable')); };
            document.head.append(script);
        });
        readingPdfLibrary = load('/static/vendor/pdfmake/pdfmake.min.js').then(() => load('/static/vendor/pdfmake/vfs_fonts.js')).catch(error => { readingPdfLibrary = null; throw error; });
    }
    return readingPdfLibrary;
}
function readingPdfDefinition(reading) {
    const content = [
        {text:'QUANTUM ORACLE', fontSize:10, characterSpacing:2, color:'#856329', margin:[0,0,0,14]},
        {text:reading.title, fontSize:24, bold:true, color:'#282432', margin:[0,0,0,22]}
    ];
    reading.sections.forEach(section => {
        content.push({text:section.title, style:'section', headlineLevel:1});
        section.text.split(/\n\n+/).forEach(text => content.push({text, margin:[0,0,0,10]}));
    });
    return {
        info:{title:reading.title, author:'Quantum Oracle'},
        pageSize:'A4', pageMargins:[48,48,48,48], content,
        defaultStyle:{font:'Roboto', fontSize:11, lineHeight:1.35, color:'#282432'},
        styles:{section:{fontSize:14, bold:true, color:'#856329', margin:[0,14,0,8]}},
        pageBreakBefore:(node, following) => node.headlineLevel === 1 && following.length === 0,
        footer:(page,count) => ({columns:[{text:'qoracle.app',color:'#756e7c'},{text:`${page} / ${count}`,alignment:'right',color:'#756e7c'}],fontSize:9,margin:[48,16,48,0]})
    };
}
async function downloadReadingPdf() {
    const button = document.getElementById('downloadReadingPdfBtn');
    const feedback = document.getElementById('socialShareFeedback');
    const reading = fullReadingExport();
    button.disabled = true;
    feedback.textContent = 'Preparing your full reading…';
    try {
        await loadReadingPdfLibrary();
        const blob = await new Promise(resolve => pdfMake.createPdf(readingPdfDefinition(reading)).getBlob(resolve));
        const url = URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.download = `qoracle-${reading.title.toLowerCase().replace(/[^a-z0-9]+/g,'-').replace(/-$/,'')}.pdf`;
        document.body.append(link); link.click(); link.remove();
        setTimeout(() => URL.revokeObjectURL(url),60000);
        feedback.textContent = 'Your full reading PDF is ready.';
    } catch (_) { feedback.textContent = 'The PDF could not be prepared. Please try again, or copy the reading.'; }
    finally { button.disabled = false; }
}
