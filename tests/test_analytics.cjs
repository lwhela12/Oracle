const fs = require('node:fs');
const vm = require('node:vm');
const assert = require('node:assert/strict');
const source = fs.readFileSync('static/analytics.js', 'utf8');
const visitor = 'd454a247-0ec3-4bce-a499-d119d3367088';
async function create(store = new Map(), opts = {}) {
    const requests = [];
    const sandbox = {window: {crypto: {randomUUID: () => visitor}}, navigator: opts.navigator || {},
        localStorage: {getItem: k => store.get(k), setItem: (k,v) => store.set(k,v), removeItem: k => store.delete(k)},
        AbortSignal, fetch: async (url, args) => { requests.push({url, args}); return {ok:true, json: async () => ({enabled:true})}; }};
    vm.runInNewContext(source, sandbox);
    await new Promise(resolve => setImmediate(resolve));
    return {analytics:sandbox.window.OracleAnalytics, requests, store};
}
(async () => {
    const first = await create();
    assert.equal(first.analytics.readingContext().visitor_id, visitor);
    assert.equal(first.requests.length, 2);
    assert.deepEqual(Object.keys(JSON.parse(first.requests[1].args.body)), ['visitor_id']);
    const reload = await create(first.store);
    assert.equal(reload.analytics.readingContext().visitor_id, visitor);
    const blocked = await create(new Map(), {navigator:{doNotTrack:'1'}});
    assert.equal(blocked.requests.length, 0);
    assert.equal(blocked.analytics.readingContext().visitor_id, null);
    first.analytics.toggle({});
    assert.equal(first.analytics.readingContext().visitor_id, null);
    assert.equal(first.store.has('oracle_anonymous_visitor'), false);
    assert.equal((await create(first.store)).requests.length, 0);
    console.log('Anonymous analytics checks passed');
})().catch(error => { console.error(error); process.exitCode = 1; });
