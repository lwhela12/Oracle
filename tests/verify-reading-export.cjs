/* Local fixture checks: no model calls, no external shares. */
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const {chromium} = require(process.env.PLAYWRIGHT_MODULE || 'playwright');
const output = path.resolve('scratch/ui-verification');
(async () => {
 fs.mkdirSync(output,{recursive:true});
 const browser = await chromium.launch({channel:'chrome',headless:true});
 try {
  const context = await browser.newContext({viewport:{width:390,height:844},acceptDownloads:true});
  const page = await context.newPage();
  const errors=[];page.on('pageerror',error=>errors.push(error.message));
  let workers=0;page.on('worker',()=>workers++);
  await page.route('**/reading-pdf-worker.js*', async route=>{await new Promise(resolve=>setTimeout(resolve,300));await route.continue();});
  await page.route('**/chat**',route=>route.abort());
  await page.goto((process.env.ORACLE_TEST_URL || 'http://127.0.0.1:8877')+'/?demo=tarot');
  await page.evaluate(() => {
   const paragraph='Take a steady breath. Your next step can be small, deliberate, and your own. “Courage” does not require certainty — it asks for attention.';
   renderReadingLayers('[[HEART]]\nA quiet beginning.\n[[DEPTH]]\n## Look ahead\n\n'+Array.from({length:40},(_,i)=>`Passage ${i+1}. ${paragraph}`).join('\n\n')+'\n[[SYMBOL:1:BRIEF]]\nYour tools are ready.\n[[SYMBOL:1:DEPTH]]\nMake one clear choice.\n[[SYMBOL:2:BRIEF]]\nListen closely.\n[[SYMBOL:2:DEPTH]]\nTrust the pause.\n[[QUOTE]]\nA quiet beginning.');
   seekerInquiryDisplay.textContent='PRIVATE QUESTION TEST';
   Object.defineProperty(navigator,'clipboard',{configurable:true,value:{writeText:async text=>{window.copiedReading=text;}}});
  });
  await page.locator('#reading-share-btn').click();
  await page.locator('#copyReadingBtn').click();
  let copied=await page.evaluate(()=>window.copiedReading);
  for(const text of ['A quiet beginning.','Passage 40.','Your tools are ready.','Make one clear choice.','The Magician','Trust the pause.']) assert(copied.includes(text),text);
  assert(!copied.includes('PRIVATE QUESTION TEST'));
  assert(!copied.includes('[[HEART]]'));
  assert.equal(await page.locator('#exportIncludeQuestion').count(),0,'Question checkbox is removed');
  for(const [width,height] of [[320,568],[390,844],[667,375]]) {
   await page.setViewportSize({width,height});
   for(const selector of ['#copyReadingBtn','#downloadReadingPdfBtn','#socialExportModal .lore-close-btn']) {
    const r=await page.locator(selector).boundingBox(); assert(r.y>=0 && r.y+r.height<=height+1 && r.x>=0 && r.x+r.width<=width+1,`${selector} visible at ${width}x${height}`);
   }
  }
  await page.setViewportSize({width:390,height:844});
  await page.waitForFunction(()=>!document.getElementById('socialDownloadBtn').disabled);
  assert(await page.evaluate(()=>readingPdfSpread(talismanSnapshot).startsWith('data:image/jpeg;base64,')),'PDF includes the actual spread image');
  await page.screenshot({path:path.join(output,'share-full-reading.png')});
  await page.evaluate(()=>{document.getElementById('socialShareFeedback').textContent='';window.pdfTicks=0;window.pdfHeartbeat=setInterval(()=>window.pdfTicks++,20);});
  const before=await page.locator('#downloadReadingPdfBtn').boundingBox();
  const pending=page.waitForEvent('download');await page.locator('#downloadReadingPdfBtn').click();
  assert.equal(await page.locator('#downloadReadingPdfBtn').getAttribute('aria-busy'),'true');
  assert.equal(await page.locator('.pdf-button-label').textContent(),'Preparing…');
  assert.equal(await page.locator('#downloadReadingPdfBtn').evaluate(el=>getComputedStyle(el).opacity),'1','Busy button does not flash dim');
  const during=await page.locator('#downloadReadingPdfBtn').boundingBox();
  assert(Math.abs(before.y-during.y)<1,'Footer stays still while preparing');
  await page.evaluate(()=>downloadReadingPdf()); // Duplicate requests are ignored while busy.
  await page.screenshot({path:path.join(output,'pdf-preparing.png')});
  await (await pending).saveAs(path.join(output,'full-reading.pdf'));
  assert.equal(workers,1,'A single background worker generates the PDF');
  assert(await page.evaluate(()=>{clearInterval(window.pdfHeartbeat);return window.pdfTicks>5 && typeof pdfMake==='undefined';}),'UI keeps responding while PDF library runs in worker');
  const after=await page.locator('#downloadReadingPdfBtn').boundingBox();
  assert(Math.abs(before.y-after.y)<1,'Footer stays still after download');
  assert.equal(await page.locator('.pdf-button-label').textContent(),'Download PDF');
  await page.unroute('**/reading-pdf-worker.js*');
  await page.route('**/reading-pdf-worker.js*',route=>route.abort());
  await page.locator('#downloadReadingPdfBtn').click();
  await page.waitForFunction(()=>!document.getElementById('downloadReadingPdfBtn').disabled);
  assert((await page.locator('#socialShareFeedback').textContent()).includes('could not be prepared'),'Worker failure restores a usable button');
  await page.evaluate(()=>Object.defineProperty(navigator,'clipboard',{configurable:true,value:{writeText:async()=>{throw new Error('blocked');}}}));
  await page.locator('#copyReadingBtn').click();assert((await page.locator('#socialShareFeedback').textContent()).includes('blocked'));
  await page.evaluate(()=>{currentReadingLayers=ReadingLayers.parse('## Legacy reading\n\nThe entire older reading remains available.');});
  assert((await page.evaluate(()=>fullReadingText())).includes('The entire older reading remains available.'));
  assert.deepEqual(errors,[]);
  console.log('PASS: complete layered and legacy content, question excluded, clipboard success/failure, full PDF download, mobile actions, no browser exceptions');
 } finally {await browser.close();}
})().catch(error=>{console.error(error);process.exitCode=1;});
