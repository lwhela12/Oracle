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
        readingPdfLibrary = load('/static/vendor/pdfmake/pdfmake.min.js').then(() => load('/static/vendor/pdfmake/vfs_fonts.js')).then(() => load('/static/vendor/pdfmake/cormorant.js')).then(() => {
            pdfMake.fonts = {Roboto:{normal:'Roboto-Regular.ttf',bold:'Roboto-Medium.ttf',italics:'Roboto-Italic.ttf',bolditalics:'Roboto-MediumItalic.ttf'}};
            pdfMake.fonts.Cormorant = {normal:'Cormorant-regular.ttf',bold:'Cormorant-semibold.ttf',italics:'Cormorant-regular.ttf',bolditalics:'Cormorant-semibold.ttf'};
        }).catch(error => { readingPdfLibrary = null; throw error; });
    }
    return readingPdfLibrary;
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
function readingPdfBackground(_, size) {
    // Sparse, deterministic stars stay in the margins, clear of the reading text.
    const sky = [{type:'rect',x:0,y:0,w:size.width,h:size.height,color:'#101017'}];
    for (let i=0;i<48;i++) {
        const left = i % 2 === 0;
        sky.push({type:'ellipse',x:left ? 8+(i*17)%24 : size.width-8-(i*17)%24,y:22+(i*83)%(size.height-44),r1:i%7===0 ? 1.2 : 0.55,r2:i%7===0 ? 1.2 : 0.55,color:i%3===0 ? '#88724e' : '#45404f'});
    }
    sky.push({type:'line',x1:48,y1:size.height-44,x2:size.width-48,y2:size.height-44,lineWidth:0.5,lineColor:'#665337'});
    return {canvas:sky};
}
function readingPdfDefinition(reading, spreadImage) {
    const content = [
        {text:'QUANTUM ORACLE', font:'Cormorant', fontSize:18, characterSpacing:2, color:'#d4b77c', alignment:'center', margin:[0,0,0,10]},
        {text:reading.title, font:'Cormorant', fontSize:28, bold:true, color:'#f2eee6', alignment:'center', margin:[0,0,0,20]}
    ];
    if (spreadImage) content.push({image:spreadImage,fit:[499,300],alignment:'center',margin:[0,0,0,18]});
    reading.sections.forEach(section => {
        content.push({text:section.title, style:'section', headlineLevel:1});
        section.text.split(/\n\n+/).forEach(text => content.push({text, margin:[0,0,0,10]}));
    });
    return {
        info:{title:reading.title, author:'Quantum Oracle'},
        pageSize:'A4', pageMargins:[48,40,48,60], content,
        background:readingPdfBackground,
        defaultStyle:{font:'Roboto', fontSize:11, lineHeight:1.35, color:'#e6e0d9'},
        styles:{section:{font:'Cormorant',fontSize:20,bold:true,color:'#d4b77c',margin:[0,14,0,8]}},
        pageBreakBefore:(node, following) => node.headlineLevel === 1 && following.length === 0,
        footer:(page,count) => ({columns:[{text:'qoracle.app',color:'#bcb6c5'},{text:`${page} / ${count}`,alignment:'right',color:'#bcb6c5'}],fontSize:9,margin:[48,20,48,0]})
    };
}
async function downloadReadingPdf() {
    const button = document.getElementById('downloadReadingPdfBtn');
    const feedback = document.getElementById('socialShareFeedback');
    const reading = fullReadingExport();
    const snapshot = talismanSnapshotPromise || Promise.resolve(talismanSnapshot);
    button.disabled = true;
    feedback.textContent = 'Preparing your full reading…';
    try {
        const [, altar] = await Promise.all([loadReadingPdfLibrary(), snapshot]);
        const spreadImage = readingPdfSpread(altar);
        const blob = await new Promise(resolve => pdfMake.createPdf(readingPdfDefinition(reading, spreadImage)).getBlob(resolve));
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
