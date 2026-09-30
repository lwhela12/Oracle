// Exercise the actual local-journal functions with an existing legacy entry.
const fs = require('node:fs');
const vm = require('node:vm');
const assert = require('node:assert/strict');
const source = fs.readFileSync('static/ui.js', 'utf8');
const functions = source.slice(source.indexOf('function getHistory()'), source.indexOf('function renderHistoryDrawer()'));
const legacy = {id:'reading_123', timestamp:'Sep 1', readingData:{type:'tarot'}, text:'legacy'};
const storage = new Map([['oracle_reading_history', JSON.stringify([legacy])]]);
const status = {};
const context = vm.createContext({localStorage:{getItem:k=>storage.get(k), setItem:(k,v)=>storage.set(k,v)},
  document:{getElementById:()=>status}, currentTradition:'tarot', oracleRoute:'reading', Date});
vm.runInContext(functions, context);
const metadata = {type:'tarot', cards:[{name:'fixture'}], canonical_reading_id:'61696c9e-041d-40f8-a277-28c81f80b272',
  created_at:'2026-09-29T12:00:00+00:00', content_format_version:1};
context.saveReadingToJournal('question', metadata, 'answer');
context.saveReadingToJournal('question', metadata, 'answer');
let entries = JSON.parse(storage.get('oracle_reading_history'));
assert.equal(entries.length, 2);
assert.equal(entries[0].id, metadata.canonical_reading_id);
assert.equal(entries[0].created_at, metadata.created_at);
assert.equal(entries[0].readingData.cards[0].name, 'fixture');
assert.deepEqual(entries[1], legacy);
context.localStorage.setItem = () => { throw new Error('storage full'); };
context.saveReadingToJournal('question', metadata, 'answer');
assert.equal(status.textContent, 'Could not save on this device');
console.log('Journal identity and legacy preservation checks passed');
