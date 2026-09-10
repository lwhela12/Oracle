const assert=require('node:assert/strict');
const {chromium}=require(process.env.PLAYWRIGHT_MODULE||'playwright');
const L=require('../static/reading-layers.js');
const origin=process.env.ORACLE_TEST_URL||'http://127.0.0.1:8876';
const heart='You are ready to choose your own path. Your patience has become a strength you can trust.';
const depth='## A place to begin\n\nThe full interpretation explores your choices in detail. '+('Your past effort makes room for a thoughtful new beginning. '.repeat(30));
const text=`[[HEART]]\n${heart}\n[[DEPTH]]\n${depth}\n[[SYMBOL:1:BRIEF]]\nYou carry a quiet courage into this beginning.\n[[SYMBOL:1:DEPTH]]\n${'In this first position, your symbol connects your question to the roots of change. '.repeat(20)}\n[[SYMBOL:2:BRIEF]]\nYour second symbol invites you to pause.\n[[SYMBOL:2:DEPTH]]\nThe second position concerns your next choice.\n[[SYMBOL:3:BRIEF]]\nYour third symbol opens a new perspective.\n[[SYMBOL:3:DEPTH]]\nThe third position joins the first two themes.\n[[QUOTE]]\nYou are ready to choose your own path.`;
assert.equal(L.parse('A saved old reading.').depth,'A saved old reading.');
assert.equal(L.quotes(L.parse(text))[0],'You are ready to choose your own path.');
assert(!L.quotes(L.parse(text.replace('[[QUOTE]]\nYou are ready to choose your own path.','[[QUOTE]]\nYou will win a million dollars tomorrow.'))).includes('You will win a million dollars tomorrow.'));
for(let i=1;i<text.length;i++) assert(!JSON.stringify(L.parse(text.slice(0,i))).includes('[['),'Partial delimiters stay hidden');
(async()=>{
 const browser=await chromium.launch({channel:'chrome',headless:true});
 try {
  const page=await browser.newPage({viewport:{width:390,height:844},hasTouch:true});
  const errors=[];page.on('pageerror',e=>errors.push(e.message));
  let calls=0, legacy=false;
  await page.route('**/chat/stream',async route=>{
   calls++;
   const mode=route.request().postDataJSON().mode;
   const metadata=mode==='runes'?{type:'runes',spread_type:'norns',runes:['Fehu','Uruz','Thurisaz'].map(name=>({name,key:name.toLowerCase(),symbol:'ᚠ',meaning:'Traditional meaning',keywords:'Reflection'})),positions:['Past','Present','Future']}:{type:'tarot',spread_type:'3-card',cards:['The Fool','The Magician','The Hermit'].map(name=>({name,arcana:'major'})),positions:['Past','Present','Future']};
   const event=(kind,data)=>`event: ${kind}\ndata: ${JSON.stringify(data)}\n\n`;
   const response=legacy?'An older reading remains available in full.':text;
   let body=event('metadata',metadata);
   for(let i=0;i<response.length;i+=7) body+=event('token',{token:response.slice(i,i+7)});
   body+=event('done',{done:true});
   await route.fulfill({contentType:'text/event-stream',body});
  });
  await page.goto(origin);
  for(const mode of ['tarot','runes']) {
   await page.evaluate(mode=>navigateOracle('read/'+mode),mode);
   await page.locator('#consult-btn').tap();
   await page.waitForFunction(()=>readingComplete&&!isConsulting);
   assert.equal(await page.locator('#reading-heart-text').innerText(),heart);
   assert.equal(await page.locator('#reading-depth').getAttribute('open'),null);
   assert(await page.locator('#visual-stage-card').isVisible());
   await page.locator('#reading-depth>summary').click();
   assert((await page.locator('#oracle-stream-text').innerText()).includes('The full interpretation'));
   const rune=mode==='runes',prefix=rune?'rune':'card',dialog=rune?'#runeZoomDialog':'#cardZoomDialog';
   await page.evaluate(rune=>rune?openRuneZoom(0):openCardZoom(0),rune);
   assert((await page.locator('#'+prefix+'-personal-reading .symbol-brief').innerText()).includes('quiet courage'));
   assert.equal(await page.locator('#'+prefix+'-personal-reading').evaluate(el=>getComputedStyle(el).color),'rgb(242, 238, 230)','Personal interpretation uses readable dark-theme text');
   await page.screenshot({path:'scratch/ui-verification/'+prefix+'-personal-reading.png',animations:'disabled'});
   await page.locator('#'+prefix+'-personal-reading summary').click();
   const before=calls;
   await page.locator('#'+prefix+'ZoomNext').click();
   assert((await page.locator('#'+prefix+'-personal-reading .symbol-brief').innerText()).includes('second symbol'));
   assert.equal(await page.locator('#'+prefix+'-personal-reading details').getAttribute('open'),null);
   assert.equal(calls,before,'Viewer never calls the model');
   await page.locator('#'+prefix+'ZoomPrev').click();
   await page.locator('#'+prefix+'-personal-reading summary').click();
   for(const [width,height] of [[390,844],[320,568],[667,375]]) {
    await page.setViewportSize({width,height});
    await page.locator(dialog).evaluate(el=>el.scrollTop=el.scrollHeight);
    await page.waitForTimeout(350);
    const close=await page.locator('#'+prefix+'ZoomClose').boundingBox();
    assert(close.y>=0&&close.y+close.height<=height,'Close remains visible after scrolling long symbol interpretation: '+JSON.stringify(close));
   }
   await page.locator('#'+prefix+'ZoomClose').click();
   await page.setViewportSize({width:390,height:844});
   await page.evaluate(()=>navigateOracle('journal'));
   await page.locator('.journal-entry').first().click();
   assert.equal(await page.locator('#reading-depth').getAttribute('open'),null,'Journal restores collapsed depth');
   assert.equal(await page.locator('#reading-heart-text').innerText(),heart);
   await page.evaluate(rune=>rune?openRuneZoom(0):openCardZoom(0),rune);
   assert((await page.locator('#'+prefix+'-personal-reading .symbol-brief').innerText()).includes('quiet courage'));
   await page.locator('#'+prefix+'ZoomClose').click();
  }
  await page.locator('#reading-share-btn').click();
  assert.equal(await page.locator('#socialQuoteInput').inputValue(),'You are ready to choose your own path.');
  await page.getByRole('button',{name:'Close share dialog'}).click();
  await page.screenshot({path:'scratch/ui-verification/layered-reading.png',fullPage:true});
  legacy=true;
  await page.evaluate(()=>navigateOracle('read/tarot'));
  await page.locator('#consult-btn').tap();
  await page.waitForFunction(()=>readingComplete&&!isConsulting);
  assert(await page.locator('#reading-heart').isHidden());
  assert(await page.locator('#oracle-stream-text').isVisible());
  assert.equal(errors.length,0,errors.join('\n'));
  console.log('PASS: layered streaming, disclosure, per-symbol mapping, long-dialog scrolling, journal, exact share quote, legacy fallback; no model calls');
 } finally {await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
