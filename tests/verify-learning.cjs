/* Learn regression: no generation requests or live model calls. */
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const {chromium} = require(process.env.PLAYWRIGHT_MODULE || 'playwright');
const origin = process.env.ORACLE_TEST_URL || 'http://127.0.0.1:8876';
const output = path.resolve('scratch/ui-verification');
fs.mkdirSync(output, {recursive:true});
(async () => {
    const browser = await chromium.launch({channel:'chrome',headless:true});
    const page = await browser.newPage({viewport:{width:390,height:844}});
    const errors = [], requests = [];
    page.on('pageerror', error => errors.push(error.message));
    await page.route('**/chat**', route => { requests.push(route.request().url()); return route.abort(); });
    const navigate = route => page.evaluate(route => navigateOracle(route), route);
    const overflow = async label => assert(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1), label);
    try {
        await page.goto(origin + '/#learn/tarot');
        await page.locator('#learning-topic').waitFor();
        const expected = {
            tarot: ['22 Major Arcana', '56 Minor Arcana', 'Wands (Fire)', 'Hopes/Fears', 'The Fool'],
            runes: ['Three Ættir', 'Merkstave', 'blank rune', 'Yggdrasil', 'Grip'],
            iching: ['64 Hexagrams', 'Old Yin', 'Old Yang', '☰ Heaven', 'unchanging cast'],
            number: ['Digital Reduction', 'Master Number', '247', '11, 22, and 33'],
            how: ['pseudo-random', 'quantum', '2.5-second', 'Pauli', 'synchronicity', '25 completed readings', 'The draw comes first']
        };
        for (const [key, phrases] of Object.entries(expected)) {
            await navigate('learn/' + key);
            const text = await page.locator('#learn-content').textContent();
            for (const phrase of phrases) assert(text.includes(phrase), key + ' missing restored topic ' + phrase);
            assert(await page.locator('[data-chapter]').count() >= 8, key + ' has substantial chapters');
            await page.getByRole('button', {name:'Expand all',exact:true}).click();
            assert.equal(await page.locator('[data-chapter]:not([open])').count(), 0);
            for (const width of [320,390,768,1365]) {
                await page.setViewportSize({width,height:844});
                await overflow(key + ' expanded at ' + width);
            }
            await page.setViewportSize({width:390,height:844});
            await page.getByRole('button', {name:'Collapse all',exact:true}).click();
            assert.equal(await page.locator('[data-chapter][open]').count(), 0);
            const target = key === 'how' ? 'synchronicity' : 'history';
            await page.getByLabel('In this guide').selectOption(target);
            assert(await page.locator(`[data-chapter="${target}"]`).evaluate(el => el.open));
            assert(await page.locator(`[data-chapter="${target}"] summary`).evaluate(el => el === document.activeElement));
            const top = await page.locator(`[data-chapter="${target}"]`).evaluate(el => el.getBoundingClientRect().top);
            assert(top >= 60 && top < 300, key + ' chapter jump clears fixed header');
            await page.screenshot({path:path.join(output,`learn-${key}-chapter.png`),animations:'disabled'});
            await page.keyboard.press('Enter');
            await page.waitForFunction(target => !document.querySelector(`[data-chapter="${target}"]`).open, target);
        }
        console.log('PASS: restored topics, expand/collapse, keyboard and chapter jumps; five guides at four widths');

        await navigate('read/tarot');
        await page.getByLabel('Your question').fill('What deserves my attention?');
        const spreads = await page.evaluate(() => Object.fromEntries(Object.entries(TRADITION_SPREADS).map(([key,value]) => [key,value.options.map(option => option.id)])));
        for (const [key, ids] of Object.entries(spreads)) {
            for (const id of ids) {
                await navigate('learn/' + key);
                await page.getByLabel('In this guide').selectOption('spreads');
                await page.locator(`[data-learn-spread="${id}"]`).click();
                assert.equal(new URL(page.url()).hash, '#read/' + key);
                assert.equal(await page.evaluate(() => currentSpreadType), id);
                assert.equal(await page.getByLabel('Your question').inputValue(), 'What deserves my attention?');
                await page.goBack();
                assert.equal(new URL(page.url()).hash, '#learn/' + key);
                assert(await page.locator('[data-chapter="spreads"]').evaluate(el => el.open));
            }
        }
        console.log('PASS: all 11 Learn-to-reading links choose correct spread, retain question and restore open chapter');
        await navigate('read/tarot');
        await navigate('learn/tarot');
        await page.getByLabel('In this guide').selectOption('interpretation');
        await navigate('learn/how');
        await page.getByRole('button', {name:/Back to your question/}).click();
        assert.equal(new URL(page.url()).hash, '#read/tarot');
        await navigate('learn/tarot');
        assert(await page.locator('[data-chapter="interpretation"]').evaluate(el => el.open));
        await page.getByRole('button', {name:'Expand all',exact:true}).click();
        for (const theme of ['dark','light']) {
            await page.evaluate(theme => {document.body.dataset.theme=theme;window.scrollTo(0,0);}, theme);
            await page.screenshot({path:path.join(output,`learn-tarot-${theme}.png`),animations:'disabled'});
            await overflow(theme);
        }
        assert.deepEqual(errors, []);
        assert.deepEqual(requests, []);
        fs.writeFileSync(path.join(output,'learning-result.json'),JSON.stringify({passed:true,guides:5,spreadLinks:11,liveModelCalls:0,pageErrors:errors},null,2));
        console.log('PASS: nested Learn return, preserved chapters, both themes, zero exceptions and no generation calls');
    } finally { await browser.close(); }
})().catch(error => {console.error(error);process.exit(1);});
