/* PDF layout and font work stay off the UI thread. No network uploads. */
importScripts('/static/vendor/pdfmake/pdfmake.min.js','/static/vendor/pdfmake/vfs_fonts.js','/static/vendor/pdfmake/cormorant.js');
pdfMake.fonts = {
    Roboto:{normal:'Roboto-Regular.ttf',bold:'Roboto-Medium.ttf',italics:'Roboto-Italic.ttf',bolditalics:'Roboto-MediumItalic.ttf'},
    Cormorant:{normal:'Cormorant-regular.ttf',bold:'Cormorant-semibold.ttf',italics:'Cormorant-regular.ttf',bolditalics:'Cormorant-semibold.ttf'}
};
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

self.onmessage = event => {
    try {
        const {reading,spreadImage} = event.data;
        pdfMake.createPdf(readingPdfDefinition(reading,spreadImage)).getBlob(blob => self.postMessage({blob}));
    } catch (error) { self.postMessage({error:error.message || 'PDF generation failed'}); }
};
