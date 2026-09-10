/* Plain-text model output contract. No model calls or HTML rendering here. */
(function(root) {
    function parse(text) {
        const result={heart:'',depth:'',symbols:{},quote:'',layered:false};
        const source=String(text||'').replace(/\r\n/g,'\n');
        if (!source.trimStart().startsWith('[[HEART]]')) {
            result.depth='[[HEART]]'.startsWith(source.trim()) ? '' : source;
            return result;
        }
        result.layered=true;
        let key=null;
        for(const line of source.split('\n')) {
            const marker=line.trim().match(/^\[\[(HEART|DEPTH|QUOTE|SYMBOL:(\d+):BRIEF|SYMBOL:(\d+):DEPTH)\]\]$/);
            if(marker) { key=marker[1]; continue; }
            // Do not flash incomplete delimiters while tokens arrive.
            if(line.trim().startsWith('[[')) continue;
            if(key==='HEART') result.heart+=line+'\n';
            else if(key==='DEPTH') result.depth+=line+'\n';
            else if(key==='QUOTE') result.quote+=line+'\n';
            else if(key?.startsWith('SYMBOL:')) {
                const [,number,part]=key.split(':');
                if(!result.symbols[number]) result.symbols[number]={brief:'',depth:''};
                result.symbols[number][part.toLowerCase()]+=line+'\n';
            }
        }
        for(const key of ['heart','depth','quote']) result[key]=result[key].trim();
        return result;
    }
    function plain(text) { return String(text||'').replace(/^#{1,6}\s+.*$/gm,'').replace(/[*_`>]/g,'').replace(/\s+/g,' ').trim(); }
    function quotes(layers) {
        const passages=[layers.heart,layers.depth,...Object.values(layers.symbols).flatMap(s=>[s.brief,s.depth])].map(plain);
        const candidates=[...new Set(passages.flatMap(p=>p.match(/[^.!?]+[.!?]+(?:[”"])?/g)||[]).map(s=>s.trim()).filter(s=>s.length>=25&&s.length<=280))];
        const score=s=>(/^you\b|^your\b/i.test(s)?8:0)+(/\byou(?:r|’re|'re)?\b/i.test(s)?4:0)+(/\b(becoming|ready|courage|threshold|precipice|strength|choose|carry|outgrown|beginning)\b/i.test(s)?2:0)-(/\b(card|rune|spread|hexagram)\b/i.test(s)?3:0);
        candidates.sort((a,b)=>score(b)-score(a));
        const selected=plain(layers.quote).replace(/^[“"]|[”"]$/g,'');
        // The model can nominate a line, but cannot invent a quotation absent from the reading.
        if(selected.length>=25&&selected.length<=280&&passages.some(p=>p.includes(selected))) candidates.unshift(selected);
        return [...new Set(candidates)].slice(0,3);
    }
    const api={parse,quotes};
    if(typeof module!=='undefined') module.exports=api;
    root.ReadingLayers=api;
})(typeof window!=='undefined'?window:globalThis);
