/* Browser regression checks. Every reading API request is intercepted; no model calls are made. */
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const {chromium} = require(process.env.PLAYWRIGHT_MODULE || 'playwright');
const origin = process.env.ORACLE_TEST_URL || 'http://127.0.0.1:8876';
const output = path.resolve('scratch/ui-verification');
fs.mkdirSync(output,{recursive:true});
const cardNames = ['The Fool','The Magician','The High Priestess','The Empress','The Emperor','The Hierophant','The Lovers','The Chariot','Strength','The Hermit'];
const runeNames = ['Fehu','Uruz','Thurisaz','Ansuz','Raidho','Kenaz','Gebo','Wunjo','Hagalaz'];
const counts = {'3-card':3,'yes-no':1,'5-card':5,celtic:10,norns:3,single:1,'five-cross':5,'thor-hammer':5,'nine-worlds':9};
const readingText = '## A fresh perspective\n\nPause before you choose your next step. **Give your attention to what matters**, and allow yourself room to change.\n\n## Something to carry with you\n\nThere is no need to solve everything at once. Notice one small action you can take today.';
function fixture(body, changing = true) {
    if (body.mode === 'tarot') return {type:'tarot',spread_type:body.spread_type,cards:cardNames.slice(0,counts[body.spread_type]).map(name=>({name,arcana:'major',suit:null})),positions:Array.from({length:counts[body.spread_type]},(_,i)=>'Position '+(i+1))};
    if (body.mode === 'runes') return {type:'runes',spread_type:body.spread_type,spread_name:body.spread_type,runes:runeNames.slice(0,counts[body.spread_type]).map((name,i)=>({name,key:name.toLowerCase(),symbol:['ᚠ','ᚢ','ᚦ','ᚨ','ᚱ','ᚲ','ᚷ','ᚹ','ᚺ'][i],meaning:'A fresh perspective',keywords:'Reflection, patience',is_reversed:body.allow_reversals && i===0})),positions:Array.from({length:counts[body.spread_type]},(_,i)=>'Position '+(i+1))};
    if (body.mode === 'number') return {type:'number',quantum_number:247};
    const hex = {number:1,name:'The Creative',chinese:'乾',meaning:'Heaven over Heaven',symbol:'☰☰',upper_trigram:{name:'Heaven',symbol:'☰'},lower_trigram:{name:'Heaven',symbol:'☰'},lines:[7,7,7,7,7,7],changing_lines:[]};
    if(changing) { hex.changing_lines=[2];hex.lines[1]=9;hex.transformed={...hex,number:13,name:'Fellowship',lines:[7,8,7,7,7,7],changing_lines:[]}; }
    return {type:'iching',hexagram:hex};
}
function event(type,data) { return `event: ${type}\ndata: ${JSON.stringify(data)}\n\n`; }
(async()=>{
    const browser=await chromium.launch({channel:'chrome',headless:true});
    const context=await browser.newContext({viewport:{width:390,height:844},hasTouch:true,acceptDownloads:true});
    const page=await context.newPage();
    const errors=[];page.on('pageerror',error=>errors.push(error.message));
    let scenario='success',requests=[],releaseDelayed;
    await context.route(url=>new URL(url).pathname.startsWith('/chat'),async route=>{
        const body=route.request().postDataJSON();requests.push({path:new URL(route.request().url()).pathname,body});
        const metadata=fixture(body,scenario!=='unchanging');
        fs.appendFileSync(path.join(output,'mock-api-log.jsonl'),JSON.stringify({kind:'test fixture — no LLM call',request:body,response:metadata})+'\n');
        if(scenario==='delayed') await new Promise(resolve=>{releaseDelayed=resolve;});
        if(scenario==='error') return route.fulfill({status:200,contentType:'text/event-stream',body:event('error',{error:'simulated server error'})});
        if(scenario==='fallback' && route.request().url().endsWith('/stream')) return route.fulfill({status:404,body:'Unavailable'});
        if(route.request().url().endsWith('/chat')) return route.fulfill({status:200,contentType:'application/json',body:JSON.stringify({...metadata,response:readingText})});
        const bodyText=event('metadata',metadata)+event('token',{token:readingText})+(scenario==='interrupted'?'':event('done',{done:true}));
        return route.fulfill({status:200,contentType:'text/event-stream',body:bodyText});
    });
    const go=async hash=>{ await page.goto(origin+'/#'+hash);await page.waitForFunction(()=>document.querySelectorAll('.app-page:not([hidden])').length===1); };
    const navigate=async route=>{await page.evaluate(route=>navigateOracle(route),route);};
    const clickDraw=async()=>{await page.locator('#consult-btn').click();await page.waitForFunction(()=>!isConsulting);};
    const checkNoOverflow=async label=>{
        const sizes=await page.evaluate(()=>({w:innerWidth,scroll:document.documentElement.scrollWidth}));
        assert(sizes.scroll<=sizes.w+1,`${label}: horizontal page overflow ${JSON.stringify(sizes)}`);
    };
    try {
        await go('read');await page.evaluate(()=>localStorage.removeItem('oracle_reading_history'));
        for(const [width,height] of [[320,568],[375,667],[390,844],[430,932],[768,1024],[1365,950]]){
            await page.setViewportSize({width,height});await navigate('read');await checkNoOverflow('home '+width);
            if(width>=375 && width<=430){
                const fit=await page.evaluate(()=>document.querySelector('.tradition-choice:last-child').getBoundingClientRect().bottom<=document.querySelector('.primary-nav').getBoundingClientRect().top);
                assert(fit,'All traditions visible at '+width);
            }
            await page.screenshot({path:path.join(output,`home-${width}.png`),animations:'disabled'});
        }
        console.log('PASS: home at six viewport sizes; all traditions visible on target phones');
        await page.setViewportSize({width:390,height:844});
        await navigate('read/tarot');
        await page.getByRole('radio',{name:/Celtic Cross/}).check();
        await page.getByLabel('Your question').fill('How can I make space for change?');
        await page.locator('.about-reading summary').click();
        await page.getByRole('button',{name:'Explore this tradition'}).click();
        await page.getByRole('button',{name:'Back to your question'}).click();
        assert.equal(await page.getByLabel('Your question').inputValue(),'How can I make space for change?');
        assert(await page.getByRole('radio',{name:/Celtic Cross/}).isChecked());
        await page.goBack();assert.equal(new URL(page.url()).hash,'#learn/tarot');
        await page.goForward();assert.equal(new URL(page.url()).hash,'#read/tarot');
        console.log('PASS: Learn and browser navigation preserve the draft and selected spread');
        for(const [tradition,spreads] of Object.entries({tarot:['3-card','yes-no','5-card','celtic'],runes:['norns','single','five-cross','thor-hammer','nine-worlds'],iching:['iching'],number:['number']})){
            for(const spread of spreads){
                await navigate('read/'+tradition);
                if(spreads.length>1) await page.locator(`input[name="spread"][value="${spread}"]`).check();
                if(tradition==='runes'){
                    const details=page.locator('#tradition-modifiers');
                    if(await details.getAttribute('open') === null) await details.locator('summary').click();
                    await page.locator('#rune-reversals').uncheck();await page.locator('#rune-set').selectOption('25');
                }
                const before=requests.length;await clickDraw();
                assert.equal(requests.length-before,1,'One request per reading');
                assert.equal(requests.at(-1).body.mode,tradition);assert.equal(requests.at(-1).body.spread_type,spread);
                if(tradition==='runes'){assert.equal(requests.at(-1).body.allow_reversals,false);assert.equal(requests.at(-1).body.include_wyrd,true);}
                assert.equal(await page.locator('#reading-save-status').textContent(),'Saved to Journal');
                assert(await page.locator('#reading-share-btn').isEnabled());
                if(counts[spread]) assert.equal(await page.locator(tradition==='tarot'?'.tarot-card-wrapper':'.rune-stone-wrapper').count(),counts[spread]);
                await checkNoOverflow(tradition+'/'+spread);
                for(const width of [320,375,430]) {
                    await page.setViewportSize({width,height:844});
                    const clipped=await page.locator('#visual-stage-card').evaluate(stage=>{
                        const bounds=stage.getBoundingClientRect();
                        return [...stage.querySelectorAll('.tarot-card-wrapper,.rune-stone-wrapper,.hex-pillar')].filter(el=>{const box=el.getBoundingClientRect();return box.left<bounds.left-1||box.right>bounds.right+1;}).map(el=>el.className);
                    });
                    assert.deepEqual(clipped,[],`Artwork stays inside the screen at ${width}: ${tradition}/${spread}`);
                }
                await page.setViewportSize({width:390,height:844});
                if(['celtic','nine-worlds','iching','number'].includes(spread)) { await page.waitForFunction(()=>[...document.querySelectorAll('.tarot-card')].every(card=>card.classList.contains('flipped'))); await page.screenshot({path:path.join(output,`reading-${spread}.png`),fullPage:true,animations:'disabled'}); }
            }
        }
        console.log('PASS: all 11 reading configurations; rune modifiers; completion and journal saving');
        scenario='unchanging';await navigate('read/iching');await clickDraw();assert.equal(await page.locator('.hex-pillar').count(),1);scenario='success';
        await navigate('journal');assert.equal(await page.locator('.journal-entry').count(),12);
        await page.locator('.journal-entry').filter({hasText:'Tarot'}).first().click();
        assert.equal(await page.locator('.tarot-card-wrapper').count(),10);
        assert.match(await page.locator('#active-reading-badge').textContent(),/Tarot/);
        await page.locator('.tarot-card-wrapper').first().press('Enter');
        assert(await page.locator('#cardZoomDialog').isVisible());
        // Centering must survive the artwork's open/starting/reduced-motion transforms.
        for (const reducedMotion of ['no-preference','reduce']) {
            await page.emulateMedia({reducedMotion});
            for (const [width,height,top,bottom] of [[390,844,0,0],[390,844,59,34],[375,667,20,0],[667,375,0,21]]) {
                await page.setViewportSize({width,height});
                await page.evaluate(({top,bottom})=>{
                    document.documentElement.style.setProperty('--safe-top',top+'px');
                    document.documentElement.style.setProperty('--safe-bottom',bottom+'px');
                    syncVisibleViewport();
                },{top,bottom});
                await page.waitForTimeout(350); // Let the actual opening/resize transition settle.
                const box=await page.locator('#cardZoomDialog').boundingBox();
                assert(box.y>=top && box.y+box.height<=height-bottom+1,'Card viewer stays within safe viewport: '+JSON.stringify(box));
                assert(Math.abs(box.y+box.height/2-(top+(height-top-bottom)/2))<2,'Card viewer is vertically centered');
                const close=await page.locator('#cardZoomClose').boundingBox();
                assert(close.y>=top && close.y+close.height<=height-bottom,'Card close stays reachable');
            }
        }
        await page.evaluate(()=>{document.documentElement.style.removeProperty('--safe-top');document.documentElement.style.removeProperty('--safe-bottom');});
        await page.setViewportSize({width:390,height:844});
        await page.emulateMedia({reducedMotion:'no-preference'});
        const initial=await page.locator('#zoomCardCounter').textContent();
        await page.getByRole('button',{name:'Next card'}).click();assert.notEqual(await page.locator('#zoomCardCounter').textContent(),initial);
        await page.locator('#cardZoomDialog').dispatchEvent('touchstart',{touches:[{identifier:1,clientX:260,clientY:240}]});
        await page.locator('#cardZoomDialog').dispatchEvent('touchend',{changedTouches:[{identifier:1,clientX:90,clientY:245}]});
        assert.equal(Number((await page.locator('#zoomCardCounter').textContent()).match(/\d+/)[0]), (Number(initial.match(/\d+/)[0]) + 1) % 10 + 1);
        await page.keyboard.press('Escape');await page.locator('#cardZoomDialog').waitFor({state:'hidden'});
        console.log('PASS: changing/unchanging I Ching, journal restore, keyboard and swipe card inspection');
        await page.locator('#reading-share-btn').click();await page.waitForFunction(()=>!document.getElementById('socialDownloadBtn').disabled,{},{timeout:30000});
        for(const [width,height] of [[320,568],[375,667],[390,844],[430,932],[667,375],[390,430]]){
            await page.setViewportSize({width,height});
            const boxes=await page.locator('#socialExportModal').evaluate(dialog=>['.lore-close-btn','#socialNativeShareBtn','#socialDownloadBtn'].map(selector=>{const r=dialog.querySelector(selector).getBoundingClientRect();return {selector,top:r.top,bottom:r.bottom,left:r.left,right:r.right,height:innerHeight,width:innerWidth};}));
            for(const box of boxes) assert(box.top>=0&&box.bottom<=box.height+1&&box.left>=0&&box.right<=box.width+1,'Share controls reachable: '+JSON.stringify(box));
        }
        await page.setViewportSize({width:390,height:844});await page.screenshot({path:path.join(output,'share-mobile.png'),animations:'disabled'});
        // Simulate a phone keyboard shrinking the visual viewport while layout stays tall.
        await page.locator('#socialQuoteInput').focus();
        await page.evaluate(()=>{document.documentElement.style.setProperty('--visible-height','400px');document.documentElement.style.setProperty('--viewport-offset','0px');});
        const keyboardBox=await page.locator('#socialDownloadBtn').boundingBox();
        assert(keyboardBox.y+keyboardBox.height<=400,'Download remains above the simulated keyboard');
        const keyboardClose=await page.locator('#socialExportModal .lore-close-btn').boundingBox();
        assert(keyboardClose.y>=0&&keyboardClose.y+keyboardClose.height<=400,'Close remains above the simulated keyboard');
        await page.evaluate(()=>syncVisibleViewport());
        await page.locator('#formatBtnPost').click();
        const downloadPromise=page.waitForEvent('download');await page.locator('#socialDownloadBtn').click();
        const download=await downloadPromise;await download.saveAs(path.join(output,'share-export.png'));assert(fs.statSync(path.join(output,'share-export.png')).size>10000);
        await page.evaluate(()=>{Object.defineProperty(navigator,'canShare',{configurable:true,value:()=>true});Object.defineProperty(navigator,'share',{configurable:true,value:async()=>{throw new DOMException('Cancelled','AbortError');}});});
        await page.locator('#socialNativeShareBtn').click();
        await page.waitForFunction(()=>!document.getElementById('socialNativeShareBtn').disabled);
        assert.equal(await page.locator('#socialShareFeedback').textContent(),'');
        assert(await page.locator('#socialExportModal').isVisible());
        await page.getByRole('button',{name:'Close share dialog'}).click();assert.equal(new URL(page.url()).hash,'#reading');
        await page.getByRole('button',{name:'About this tradition'}).click();assert.equal(new URL(page.url()).hash,'#learn/tarot');await page.getByRole('button',{name:'Back to your reading'}).click();
        console.log('PASS: share controls at six sizes including short landscape; PNG download; return to reading');
        await page.getByRole('button',{name:'Settings',exact:true}).click();await page.getByRole('switch',{name:/Light appearance/}).check();
        await page.getByRole('button',{name:'Close settings'}).click();await navigate('read');await page.screenshot({path:path.join(output,'home-light.png'),animations:'disabled'});
        assert.equal(await page.locator('body').getAttribute('data-theme'),'light');
        await page.reload();assert.equal(await page.locator('body').getAttribute('data-theme'),'light');
        console.log('PASS: light appearance and persistence');
        scenario='error';await navigate('read/tarot');const countBefore=await page.evaluate(()=>getHistory().length);await clickDraw();
        assert(await page.locator('#reading-error').isVisible());assert(await page.locator('#reading-share-btn').isDisabled());assert.equal(await page.evaluate(()=>getHistory().length),countBefore);
        scenario='success';await page.getByRole('button',{name:'Try again',exact:true}).click();await page.waitForFunction(()=>!isConsulting);assert(await page.locator('#reading-error').isHidden());
        scenario='interrupted';await navigate('read/tarot');const beforeInterrupted=requests.length;await clickDraw();assert.equal(requests.length-beforeInterrupted,1);assert(await page.locator('#reading-error').isVisible());
        scenario='fallback';await navigate('read/tarot');const beforeFallback=requests.length;await clickDraw();assert.equal(requests.length-beforeFallback,2);assert(await page.locator('#reading-share-btn').isEnabled());
        console.log('PASS: errors, explicit retry, interrupted stream without silent redraw, non-streaming fallback');
        scenario='delayed';await navigate('read/runes');await page.locator('#consult-btn').click();await page.waitForFunction(()=>isConsulting);await page.locator('[data-nav="learn"]').click();await page.locator('[data-nav="read"]').click();assert.equal(new URL(page.url()).hash,'#reading');
        await page.getByRole('button',{name:'New reading',exact:true}).click();releaseDelayed();scenario='success';await page.waitForTimeout(200);assert.equal(new URL(page.url()).hash,'#read');assert(!await page.locator('#home-page').getAttribute('hidden'));
        await page.emulateMedia({reducedMotion:'reduce'});await navigate('read/number');await clickDraw();
        assert.equal(errors.length,0,'No page errors: '+errors.join('\n'));
        console.log('PASS: navigation during loading, cancellation, reduced motion, no browser exceptions');
        fs.writeFileSync(path.join(output,'result.json'),JSON.stringify({passed:true,readingRequestsIntercepted:requests.length,liveModelCalls:0,pageErrors:errors},null,2));
    } finally { await browser.close(); }
})().catch(error=>{console.error(error);process.exitCode=1;});
