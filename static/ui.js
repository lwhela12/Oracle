/* Deterministic navigation, reading setup, and presentation. Generation lives in the existing API. */
const TRADITION_INFO = {
    tarot: { name: 'Tarot', action: 'Draw cards', description: 'A reading uses the imagery of Tarot to reflect on your question. Choose a single card for a focused answer, or a spread to explore several perspectives.', prompt: 'What would you like a fresh perspective on?', spreads: { '3-card': 'Past, present & future · 3 cards', 'yes-no': 'Focused guidance / yes or no · 1 card', '5-card': 'Your situation, challenge & possibilities · 5 cards', celtic: 'A deeper look at the whole picture · 10 cards' } },
    runes: { name: 'Runes', action: 'Cast runes', description: 'A rune reading brings a set of symbolic meanings to your question. Each position in a cast offers a different perspective, from a single point of focus to a wider view of your situation.', prompt: 'What situation are you seeking guidance on?', spreads: { norns: 'Past, present & what is unfolding · 3 runes', single: 'One symbol, one point of focus · 1 rune', 'five-cross': 'Explore the forces around your situation · 5 runes', 'thor-hammer': 'A practical perspective on your next steps · 5 runes', 'nine-worlds': 'Explore nine aspects of your situation · 9 runes' } },
    iching: { name: 'I Ching', action: 'Cast hexagram', description: 'The Book of Changes offers a way to reflect on a situation in motion. Your cast forms a six-line hexagram. Changing lines, when present, connect it to a second hexagram and another perspective.', prompt: 'What change or decision are you considering?', spreads: { iching: 'One hexagram, with changing lines when present' } },
    number: { name: 'Numerology', action: 'Draw a number', description: 'A number from 1 to 999 becomes the starting point for a symbolic reading. Bring a question, or simply explore the themes and associations of the number you receive.', prompt: 'What would you like to reflect on?', spreads: { number: 'A symbolic interpretation of a number from 1 to 999' } }
};
const chosenSpreads = Object.fromEntries(Object.entries(TRADITION_SPREADS).map(([key, value]) => [key, value.default]));
const pageScroll = new Map();
let oracleRoute = 'read';
let lastReadRoute = 'read';
let learningReturnRoute = 'read';
let consultationController = null;
let consultationVersion = 0;
let isConsulting = false;
let readingComplete = false;

function escapeText(value) {
    return String(value ?? '').replace(/[&<>"']/g, char => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[char]));
}
function navigateOracle(route, { replace = false, restore = false, focus = true } = {}) {
    pageScroll.set(oracleRoute, window.scrollY);
    if (route.startsWith('learn') && !oracleRoute.startsWith('learn')) learningReturnRoute = oracleRoute;
    const valid = /^(read(?:\/(tarot|runes|iching|number))?|reading|learn(?:\/(tarot|runes|iching|number|how))?|journal)$/.test(route);
    if (!valid || (route === 'reading' && !currentReadingData && !isConsulting)) route = 'read';
    if (route.startsWith('read/')) {
        if (isConsulting) cancelConsultation();
        setTradition(route.split('/')[1]);
    }
    oracleRoute = route;
    if (route === 'reading' && currentReadingData) currentTradition = getReadingTradition(currentReadingData);
    if (route === 'read' || route === 'reading' || route.startsWith('read/')) lastReadRoute = route;
    const pageId = route.startsWith('read/') ? 'consultation-portal' : route === 'reading' ? 'reading-stage' : route.startsWith('learn') ? 'learn-page' : route === 'journal' ? 'history-drawer' : 'home-page';
    document.querySelectorAll('.app-page').forEach(page => { page.hidden = page.id !== pageId; });
    document.body.dataset.view = route.split('/')[0];
    document.querySelectorAll('[data-nav]').forEach(link => {
        const selected = link.dataset.nav === (route.startsWith('learn') ? 'learn' : route === 'journal' ? 'journal' : 'read');
        if (selected) link.setAttribute('aria-current', 'page'); else link.removeAttribute('aria-current');
    });
    if (route.startsWith('learn')) renderLearning(route.split('/')[1]);
    if (route === 'journal') renderHistoryDrawer();
    document.getElementById('resume-reading').hidden = !currentReadingData && !isConsulting;
    if (location.hash !== '#' + route) history[replace ? 'replaceState' : 'pushState']({oracle: true}, '', '#' + route);
    const heading = document.querySelector('#' + pageId + ' h1');
    if (focus && heading) heading.focus({preventScroll: true});
    window.scrollTo({top: restore ? (pageScroll.get(route) || 0) : 0, behavior: 'instant'});
}
function setTradition(tradition) {
    if (!TRADITION_INFO[tradition]) return;
    currentTradition = tradition;
    currentSpreadType = chosenSpreads[tradition];
    document.getElementById('setup-title').textContent = TRADITION_INFO[tradition].name;
    document.getElementById('setup-emblem').innerHTML = getTraditionEmblemSvg(tradition);
    document.getElementById('setup-description').textContent = TRADITION_INFO[tradition].description;
    userInquiry.placeholder = TRADITION_INFO[tradition].prompt;
    updateSpreadOptions();
}
function updateSpreadOptions() {
    const config = TRADITION_SPREADS[currentTradition];
    const info = TRADITION_INFO[currentTradition];
    spreadStep.hidden = config.options.length < 2;
    spreadStepTitle.textContent = 'Choose your spread';
    spreadOptions.innerHTML = config.options.map(option => `<label class="spread-choice"><input type="radio" name="spread" value="${option.id}" ${option.id === currentSpreadType ? 'checked' : ''}><span><strong>${option.label}</strong><small>${info.spreads[option.id]}</small></span></label>`).join('');
    spreadOptions.querySelectorAll('input').forEach(input => input.addEventListener('change', () => {
        currentSpreadType = input.value;
        chosenSpreads[currentTradition] = input.value;
    }));
    const modifiers = document.getElementById('tradition-modifiers');
    modifiers.hidden = currentTradition !== 'runes';
    modifiers.querySelector('.option-controls').innerHTML = currentTradition === 'runes' ? `<label class="setting-row" for="rune-reversals"><span><strong>Reversed runes</strong><small>Include reversed meanings (Merkstave)</small></span><input id="rune-reversals" type="checkbox" role="switch" ${runeAllowReversals ? 'checked' : ''}></label><label class="rune-set-label" for="rune-set">Rune set</label><select id="rune-set"><option value="24" ${!runeIncludeWyrd ? 'selected' : ''}>24 runes · Traditional</option><option value="25" ${runeIncludeWyrd ? 'selected' : ''}>25 runes · Include the blank rune</option></select>` : '';
    if (currentTradition === 'runes') {
        document.getElementById('rune-reversals').onchange = e => { runeAllowReversals = e.target.checked; };
        document.getElementById('rune-set').onchange = e => { runeIncludeWyrd = e.target.value === '25'; };
    }
    consultBtn.innerHTML = `${info.action}<span aria-hidden="true">→</span>`;
}
function setInquiry(text) { userInquiry.value = text; userInquiry.focus(); }
function openTraditionLore(tradition = currentTradition) { navigateOracle('learn/' + tradition); }
function openQuantumInfoModal() { navigateOracle('learn/how'); }
function returnFromLearning() { navigateOracle(learningReturnRoute, {restore: true}); }
// Keep a reader's open chapters when visiting a reading and returning to Learn.
const learningChapterState = new Map();
function learningChapters(key, chapters) {
    const saved = learningChapterState.get(key);
    return `<div class="learning-controls"><label for="learning-topic">In this guide</label><div><select id="learning-topic"><option value="">Jump to a topic…</option>${chapters.map(chapter => `<option value="${chapter.id}">${chapter.title}</option>`).join('')}</select><button class="text-button" id="learning-expand">Expand all</button></div></div><div class="learning-chapters">${chapters.map((chapter, index) => `<details data-chapter="${chapter.id}" ${saved ? saved.has(chapter.id) ? 'open' : '' : index === 0 ? 'open' : ''}><summary><span>${chapter.title}<small>${chapter.description}</small></span></summary><div class="article-prose">${chapter.body}</div></details>`).join('')}</div>`;
}
function bindLearningChapters(key) {
    const root = document.getElementById('learn-content');
    const chapters = [...root.querySelectorAll('[data-chapter]')];
    if (!chapters.length) return;
    const expand = document.getElementById('learning-expand');
    const remember = () => {
        learningChapterState.set(key, new Set(chapters.filter(chapter => chapter.open).map(chapter => chapter.dataset.chapter)));
        expand.textContent = chapters.every(chapter => chapter.open) ? 'Collapse all' : 'Expand all';
    };
    chapters.forEach(chapter => chapter.addEventListener('toggle', remember));
    expand.addEventListener('click', () => {
        const open = !chapters.every(chapter => chapter.open);
        chapters.forEach(chapter => { chapter.open = open; });
        remember();
    });
    document.getElementById('learning-topic').addEventListener('change', event => {
        const chapter = chapters.find(chapter => chapter.dataset.chapter === event.target.value);
        if (!chapter) return;
        chapter.open = true;
        remember();
        chapter.querySelector('summary').focus({preventScroll:true});
        chapter.scrollIntoView({block:'start',behavior:'instant'});
        event.target.value = '';
    });
    remember();
}
function renderLearning(tradition) {
    const root = document.getElementById('learn-content');
    const title = document.getElementById('learn-title');
    const intro = title.nextElementSibling;
    const returnLabel = learningReturnRoute === 'reading' ? 'Back to your reading' : learningReturnRoute.startsWith('read/') ? 'Back to your question' : 'Back to readings';
    const returnButton = `<button class="text-button learning-return" onclick="returnFromLearning()">← ${returnLabel}</button>`;
    if (!tradition) {
        title.innerHTML = 'Explore the traditions.<br>Deepen your practice.';
        intro.textContent = 'Follow your curiosity—from your first reading to the symbols, stories, and ideas behind it.';
        root.innerHTML = `<div class="learn-grid">${Object.entries(TRADITION_INFO).map(([key, info]) => `<a href="#learn/${key}" class="learn-choice"><span class="page-emblem" aria-hidden="true">${getTraditionEmblemSvg(key)}</span><h2>${info.name}</h2><p>${LEARNING_GUIDES[key].overview}</p><span class="learn-choice-link">Explore ${info.name} <span aria-hidden="true">↗</span></span></a>`).join('')}</div><a class="how-link" href="#learn/how"><span><strong>How does the Oracle work?</strong><small>Quantum randomness, synchronicity, the draw, and the art of interpretation.</small></span><span aria-hidden="true">→</span></a>${returnButton}`;
        return;
    }
    if (tradition === 'how') {
        title.textContent = 'How the Oracle works.';
        intro.textContent = 'A meeting of chance, symbolism, and your question.';
        root.innerHTML = `<a href="#learn" class="back-link">← All learning</a><div class="learning-article">${learningChapters('how', ORACLE_LEARNING)}</div>${returnButton}`;
    } else {
        const info = TRADITION_INFO[tradition];
        const lore = TRADITION_LORE[tradition];
        const guide = LEARNING_GUIDES[tradition];
        const chapters = [
            {id:'symbols',title:guide.symbolsTitle,description:'The structure and symbolic language of the tradition.',body:lore.mechanics},
            {id:'spreads',title:'Choose a reading',description:'Understand each spread and what its positions mean.',body:`<div class="learn-spreads">${TRADITION_SPREADS[tradition].options.map(option => `<section class="learn-spread-guide"><h3>${option.label}</h3>${guide.spreads[option.id]}<a href="#read/${tradition}" data-learn-spread="${option.id}" data-tradition="${tradition}"><span>Try this reading</span><span aria-hidden="true">→</span></a></section>`).join('')}</div>`},
            ...(guide.extra || []),
            {id:'interpretation',title:'How to interpret your reading',description:'Move from individual symbols to a connected reading.',body:guide.interpretation},
            {id:'usage',title:'When to use it',description:'Questions and situations that suit this tradition.',body:lore.usage},
            {id:'practice',title:'Build a personal practice',description:'Prepare a question, reflect, and return to what you learn.',body:guide.practice},
            {id:'history',title:'History & origins',description:lore.era,body:`<p class="learning-native">${lore.nativeName}</p>${lore.history}`},
            {id:'draw',title:'How the Oracle draws',description:'The process behind this reading.',body:`${guide.draw}<p><a href="#learn/how">Explore quantum randomness, synchronicity & the role of AI →</a></p>`},
            ...(guide.sources ? [{id:'sources',title:'Sources & further exploration',description:'Continue with original texts and historical collections.',body:`<ul>${guide.sources.map(([label,url]) => `<li><a href="${url}" target="_blank" rel="noopener noreferrer">${label}</a></li>`).join('')}</ul>`}] : [])
        ];
        title.textContent = info.name;
        intro.textContent = guide.subtitle;
        root.innerHTML = `<a href="#learn" class="back-link">← All traditions</a><div class="learning-article"><div class="learning-intro"><span class="page-emblem" aria-hidden="true">${getTraditionEmblemSvg(tradition)}</span><div><p>${info.description}</p><a href="#read/${tradition}" class="text-button">Start a reading <span aria-hidden="true">→</span></a></div></div>${learningChapters(tradition, chapters)}</div><div class="learn-actions"><a href="#read/${tradition}" class="primary-button">Try a ${info.name} reading <span aria-hidden="true">→</span></a>${returnButton}</div>`;
    }
    bindLearningChapters(tradition);
}
function openSettings() { document.getElementById('settings-dialog').showModal(); }
function persistPreference(key, value) { try { localStorage.setItem(key, value); } catch (_) { /* Browsing remains usable without persistence. */ } }
function toggleTheme() {
    const light = themeBtn.checked;
    document.body.dataset.theme = light ? 'light' : 'dark';
    document.querySelector('meta[name="theme-color"]').content = light ? '#f7f4ed' : '#101017';
    persistPreference('theme', light ? 'light' : 'dark');
}
function toggleSound() { soundEnabled = soundBtn.checked; persistPreference('soundEnabled', soundEnabled); if (soundEnabled) { initAudio(); sounds.chime(); } }
function toggleMusic() { musicEnabled = musicBtn.checked; persistPreference('musicEnabled', musicEnabled); if (musicEnabled) startAmbientMusic(); else stopAmbientMusic(); }
function getReadingTradition(data) { return data.quantum_number ? 'number' : TRADITION_INFO[data.type] ? data.type : currentTradition; }
function describeReading(data) {
    const tradition = getReadingTradition(data);
    const spread = TRADITION_SPREADS[tradition]?.options.find(option => option.id === data.spread_type);
    document.getElementById('reading-spread-label').textContent = spread && TRADITION_SPREADS[tradition].options.length > 1 ? spread.label : '';
}
function cancelConsultation() {
    consultationVersion++;
    consultationController?.abort();
    consultationController = null;
    isConsulting = false;
    thinkingIndicator.style.display = 'none';
    oracleStreamText.setAttribute('aria-busy', 'false');
    consultBtn.disabled = false;
}
async function executeConsultation() {
    if (isConsulting) return;
    initAudio();
    if (musicEnabled) startAmbientMusic();
    const tradition = currentTradition;
    const question = userInquiry.value.trim();
    const body = { message: question || 'Provide sacred guidance and reveal the truth of my path.', mode: tradition, spread_type: currentSpreadType, allow_reversals: runeAllowReversals, include_wyrd: runeIncludeWyrd, session_id: sessionId };
    const version = ++consultationVersion;
    const controller = new AbortController();
    consultationController = controller;
    isConsulting = true;
    readingComplete = false;
    currentReadingData = null;
    activeTarotSpread = null;
    activeRuneSpread = null;
    consultBtn.disabled = true;
    document.getElementById('reading-share-btn').disabled = true;
    document.getElementById('reading-save-status').textContent = '';
    document.getElementById('reading-error').hidden = true;
    activeReadingBadge.textContent = TRADITION_SPREADS[tradition].badgeTitle;
    describeReading({type:tradition,spread_type:currentSpreadType});
    seekerInquiryDisplay.textContent = question || 'General guidance';
    visualStageCard.innerHTML = '';
    visualStageCard.hidden = true;
    oracleStreamText.innerHTML = '';
    oracleStreamText.setAttribute('aria-busy', 'true');
    thinkingIndicator.style.display = 'flex';
    navigateOracle('reading');
    let text = '';
    let done = false;
    const timeout = setTimeout(() => controller.abort(), 120000);
    const acceptMetadata = data => {
        currentReadingData = data;
        visualStageCard.hidden = false;
        renderVisualStage(data);
        thinkingIndicator.querySelector('span').textContent = 'Your interpretation is unfolding…';
    };
    const acceptEvent = block => {
        const event = block.match(/^event:\s*(.+)$/m)?.[1]?.trim();
        const data = block.split('\n').filter(line => line.startsWith('data:')).map(line => line.slice(5).trim()).join('\n');
        if (!data) return;
        const parsed = JSON.parse(data);
        if (event === 'metadata') acceptMetadata(parsed);
        else if (event === 'token') { text += parsed.token || ''; oracleStreamText.innerHTML = renderMarkdown(text); }
        else if (event === 'done') done = true;
        else if (event === 'error') throw new Error('The reading could not be completed. Please try again.');
    };
    try {
        const response = await fetch('/chat/stream', {method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify(body), signal: controller.signal});
        if (!response.ok && ![404,405,501].includes(response.status)) throw new Error('The Oracle could not be reached. Please try again in a moment.');
        if (response.ok && response.body && response.headers.get('content-type')?.includes('text/event-stream')) {
            const reader = response.body.getReader();
            const decoder = new TextDecoder();
            let buffer = '';
            while (true) {
                const chunk = await reader.read();
                if (version !== consultationVersion) { await reader.cancel(); return; }
                buffer += decoder.decode(chunk.value, {stream: !chunk.done});
                let boundary;
                while (!done && (boundary = buffer.search(/\r?\n\r?\n/)) >= 0) {
                    const block = buffer.slice(0, boundary).replace(/\r\n/g, '\n');
                    const delimiter = buffer.slice(boundary).match(/^\r?\n\r?\n/)[0].length;
                    buffer = buffer.slice(boundary + delimiter);
                    acceptEvent(block);
                }
                // Some hosts (Vercel) keep the connection open after the generator finishes. The done event is the end of the reading.
                if (done) { reader.cancel().catch(() => {}); break; }
                if (chunk.done) { if (buffer.trim()) acceptEvent(buffer.replace(/\r\n/g, '\n')); break; }
            }
        } else {
            // Compatibility for hosts without the streaming route. Never silently redraw after partial output.
            const fallback = await fetch('/chat', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(body), signal:controller.signal});
            const data = await fallback.json();
            if (!fallback.ok || data.error) throw new Error('The reading could not be completed. Please try again.');
            if (version !== consultationVersion) return;
            acceptMetadata(data);
            text = data.response || '';
            oracleStreamText.innerHTML = renderMarkdown(text);
            done = true;
        }
        if (!done || !text || !currentReadingData) throw new Error('Your reading was interrupted. You can try again for a new draw.');
        readingComplete = true;
        saveReadingToJournal(question || 'General guidance', currentReadingData, text, tradition);
        document.getElementById('reading-share-btn').disabled = false;
    } catch (error) {
        if (version !== consultationVersion) return;
        document.getElementById('reading-error-message').textContent = error.name === 'AbortError' ? 'This reading is taking too long. Please try again for a new draw.' : error.message || 'The reading could not be completed.';
        document.getElementById('reading-error').hidden = false;
    } finally {
        clearTimeout(timeout);
        if (version === consultationVersion) {
            isConsulting = false;
            consultationController = null;
            consultBtn.disabled = false;
            thinkingIndicator.style.display = 'none';
            thinkingIndicator.querySelector('span').textContent = 'Preparing your reading…';
            oracleStreamText.setAttribute('aria-busy', 'false');
            document.getElementById('resume-reading').hidden = !currentReadingData;
        }
    }
}
function retryConsultation() { executeConsultation(); }
function startNewConsultation() {
    cancelConsultation();
    currentReadingData = null;
    readingComplete = false;
    userInquiry.value = '';
    navigateOracle('read');
}
function getHistory() {
    try { const value = JSON.parse(localStorage.getItem('oracle_reading_history') || '[]'); return Array.isArray(value) ? value.filter(item => item && item.readingData && typeof item.text === 'string').slice(0,25) : []; }
    catch (_) { return []; }
}
function saveReadingToJournal(question, readingData, responseText, tradition = currentTradition) {
    if (!readingData || !responseText) return;
    const entries = getHistory();
    entries.unshift({id:'reading_' + Date.now(), timestamp:new Date().toLocaleDateString(undefined,{month:'short',day:'numeric',hour:'2-digit',minute:'2-digit'}), question, tradition, type:readingData.type || tradition, readingData, text:responseText});
    try {
        localStorage.setItem('oracle_reading_history', JSON.stringify(entries.slice(0,25)));
        document.getElementById('reading-save-status').textContent = 'Saved to Journal';
    } catch (_) { document.getElementById('reading-save-status').textContent = 'Could not save on this device'; }
    if (oracleRoute === 'journal') renderHistoryDrawer();
}
function renderHistoryDrawer() {
    const entries = getHistory();
    document.getElementById('clear-journal-btn').hidden = !entries.length;
    historyList.innerHTML = entries.length ? '' : '<div class="empty-journal"><span aria-hidden="true">✧</span><h2>Your story starts here.</h2><p>When you finish a reading, it will be waiting here for you to revisit.</p><a href="#read" class="primary-button">Begin a reading <span aria-hidden="true">→</span></a></div>';
    entries.forEach(item => {
        const tradition = item.tradition || getReadingTradition(item.readingData);
        const button = document.createElement('button');
        button.type = 'button';
        button.className = 'journal-entry';
        button.innerHTML = `<span class="journal-entry-emblem" aria-hidden="true">${getTraditionEmblemSvg(tradition)}</span><span class="journal-entry-copy"><span class="history-meta"><strong>${escapeText(TRADITION_INFO[tradition]?.name || 'Reading')}</strong><span>${escapeText(item.timestamp)}</span></span><span class="journal-question">${escapeText(item.question)}</span><span class="history-preview">${escapeText(item.text.replace(/[#*_]/g,'').slice(0,160))}</span></span><span aria-hidden="true">↗</span>`;
        button.onclick = () => loadHistoryItem(item);
        historyList.appendChild(button);
    });
}
function loadHistoryItem(item) {
    cancelConsultation();
    currentTradition = item.tradition || getReadingTradition(item.readingData);
    currentReadingData = item.readingData;
    describeReading(item.readingData);
    currentSpreadType = item.readingData.spread_type || chosenSpreads[currentTradition];
    activeReadingBadge.textContent = TRADITION_SPREADS[currentTradition]?.badgeTitle || 'Your reading';
    seekerInquiryDisplay.textContent = item.question;
    visualStageCard.hidden = false;
    renderVisualStage(item.readingData);
    oracleStreamText.innerHTML = renderMarkdown(item.text);
    document.getElementById('reading-error').hidden = true;
    document.getElementById('reading-save-status').textContent = 'Saved to Journal';
    document.getElementById('reading-share-btn').disabled = false;
    readingComplete = true;
    navigateOracle('reading');
}
function clearAllHistory() {
    if (!confirm('Clear the readings saved in this browser? This cannot be undone.')) return;
    try { localStorage.removeItem('oracle_reading_history'); } catch (_) { return; }
    document.getElementById('reading-save-status').textContent = '';
    renderHistoryDrawer();
}
function toggleHistory() { navigateOracle('journal'); }
function toggleSharePreview() {
    const wrapper = document.querySelector('.social-preview-wrapper');
    const expanded = wrapper.classList.toggle('preview-expanded');
    const button = document.getElementById('preview-size-btn');
    button.setAttribute('aria-expanded', String(expanded));
    button.textContent = expanded ? 'Reduce preview' : 'Enlarge preview';
}
function enableSwipe(dialog, previous, next) {
    let start = null;
    dialog.addEventListener('touchstart', e => { if (e.touches.length === 1) start = {x:e.touches[0].clientX,y:e.touches[0].clientY}; }, {passive:true});
    dialog.addEventListener('touchend', e => {
        if (!start || !e.changedTouches.length) return;
        const dx = e.changedTouches[0].clientX - start.x;
        const dy = e.changedTouches[0].clientY - start.y;
        start = null;
        if (Math.abs(dx) > 50 && Math.abs(dx) > Math.abs(dy) * 1.5) {
            (dx > 0 ? previous : next)?.click();
            // Avoid the synthetic click flipping the newly navigated card.
            const swallow = event => { event.preventDefault(); event.stopImmediatePropagation(); };
            dialog.addEventListener('click', swallow, {capture:true,once:true});
            setTimeout(() => dialog.removeEventListener('click', swallow, true), 350);
        }
    }, {passive:true});
}
function syncVisibleViewport() {
    document.documentElement.style.setProperty('--visible-height', `${window.visualViewport?.height || window.innerHeight}px`);
    document.documentElement.style.setProperty('--viewport-offset', `${window.visualViewport?.offsetTop || 0}px`);
}
window.visualViewport?.addEventListener('resize', syncVisibleViewport);
window.visualViewport?.addEventListener('scroll', syncVisibleViewport);
window.addEventListener('resize', syncVisibleViewport);
syncVisibleViewport();
document.addEventListener('click', event => {
    const link = event.target.closest('a[href^="#"]');
    if (!link || link.hash === '#main-content' || event.defaultPrevented || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
    event.preventDefault();
    if (link.dataset.learnSpread) chosenSpreads[link.dataset.tradition] = link.dataset.learnSpread;
    const route = link.dataset.nav === 'read' ? lastReadRoute : link.hash.slice(1);
    navigateOracle(route, {restore: Boolean(link.dataset.nav)});
});
window.addEventListener('popstate', () => navigateOracle(location.hash.slice(1) || 'read', {replace:true,restore:true}));
window.addEventListener('DOMContentLoaded', () => {
    document.querySelectorAll('[data-emblem]').forEach(el => { el.innerHTML = getTraditionEmblemSvg(el.dataset.emblem); });
    themeBtn.checked = localStorage.getItem('theme') === 'light';
    soundBtn.checked = soundEnabled;
    musicBtn.checked = musicEnabled;
    toggleTheme();
    enableSwipe(cardZoomDialog, cardZoomPrev, cardZoomNext);
    enableSwipe(runeZoomDialog, runeZoomPrev, runeZoomNext);
    document.querySelectorAll('dialog').forEach(dialog => {
        dialog.addEventListener('close', () => { document.body.classList.remove('dialog-open'); });
        new MutationObserver(() => { document.body.classList.toggle('dialog-open', Boolean(document.querySelector('dialog[open]'))); }).observe(dialog, {attributes:true,attributeFilter:['open']});
    });
    const demo = new URLSearchParams(location.search).get('demo');
    if (demo && currentReadingData) {
        describeReading(currentReadingData);
        readingComplete = true;
        document.getElementById('reading-share-btn').disabled = false;
        visualStageCard.hidden = false;
        navigateOracle('reading', {replace:true,focus:false});
    } else navigateOracle(location.hash.slice(1) || 'read', {replace:true,focus:false});
});
