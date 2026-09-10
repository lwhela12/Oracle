/* Safe-area geometry checks; synthetic insets do not emulate the iOS home-screen shell. */
const assert = require('node:assert/strict');
const {chromium} = require(process.env.PLAYWRIGHT_MODULE || 'playwright');
const origin = process.env.ORACLE_TEST_URL || 'http://127.0.0.1:8876';
(async () => {
    for (const engine of [chromium]) {
        const browser = await engine.launch({channel:'chrome',headless:true});
        try {
            const page = await browser.newPage({viewport:{width:390,height:844},hasTouch:true});
            await page.route('**/chat**', route => route.abort());
            await page.goto(origin);
            await page.waitForFunction(() => typeof navigateOracle === 'function');
            assert.equal(await page.locator('meta[name="apple-mobile-web-app-status-bar-style"]').getAttribute('content'), 'default');
            for (const [width,height,top,bottom] of [[390,844,0,0],[390,844,59,34],[375,667,20,0],[320,568,20,0],[667,375,0,21]]) {
                await page.setViewportSize({width,height});
                await page.evaluate(({top,bottom}) => {
                    document.documentElement.style.setProperty('--safe-top', top+'px');
                    document.documentElement.style.setProperty('--safe-bottom', bottom+'px');
                    navigateOracle('read');
                    syncVisibleViewport();
                }, {top,bottom});
                const header = await page.locator('.app-header').boundingBox();
                assert.equal(Math.round(header.height),64+top,'Header reserves status bar space');
                await page.getByRole('button',{name:'Settings',exact:true}).click();
                const close = await page.getByRole('button',{name:'Close settings'}).boundingBox();
                assert(close.y>=top && close.y+close.height<=height-bottom,'Close stays in safe area');
                await page.getByRole('button',{name:'Close settings'}).click();
                await page.evaluate(() => navigateOracle('learn/tarot'));
                await page.evaluate(() => window.scrollTo(0,document.documentElement.scrollHeight));
                assert(await page.evaluate(() => scrollY>0),'Long guide scrolls');
                await page.locator('[data-nav="read"]').click();
                assert.equal(await page.evaluate(() => scrollY),0,'Read returns to top');
                assert(await page.evaluate(() => document.documentElement.scrollWidth<=innerWidth),'No horizontal overflow');
            }
            console.log(`PASS: ${engine.name()} safe-area header, dialog close, scrolling and navigation at five viewport/inset combinations`);
        } finally { await browser.close(); }
    }
})().catch(error => {console.error(error);process.exitCode=1;});
