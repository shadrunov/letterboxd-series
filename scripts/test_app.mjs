// Rendering and interaction logic checks. This is not a browser/layout test.
import { readFile } from 'node:fs/promises';
import vm from 'node:vm';
import assert from 'node:assert/strict';

const source = await readFile(new URL('../app.js', import.meta.url), 'utf8');
const fixture = {
  years: ['2024', '2025', '2026'],
  entries: [
    { id: 'one', showId: 'royals', title: 'Young Royals', watched: '2025-10', seasons: [1, 2, 3], watch: 'watch', status: 'watched', tags: ['queer'], notes: '' },
    { id: 'two', showId: 'royals', title: 'Young Royals', watched: '2026-01', seasons: [2, 3], watch: 'rewatch', status: 'watched', tags: ['queer', 'w/ alena ❤️'], notes: 'A repeat.' },
    { id: 'three', showId: 'royals', title: 'Young Royals', watched: '2026-01', seasons: [], allSeasons: true, watch: 'rewatch', status: 'unfinished', tags: ['queer'], notes: '' },
    { id: 'four', showId: 'new', title: 'A <New> Series', watched: '2026', seasons: [1], watch: 'watch', status: 'watched', tags: ['deutsch'], notes: '<b>personal</b>' },
  ],
};
async function createHarness(search = '') {
  const elements = new Map();
  const get = key => {
    if (!elements.has(key)) elements.set(key, {
      value: key === '#sort' ? 'newest' : ['#year','#status','#watch'].includes(key) ? 'all' : '',
      options: [{value:'all'}, {value:'watched'}, {value:'unfinished'}, {value:'watch'}, {value:'rewatch'}, {value:'newest'}, {value:'oldest'}, {value:'title'}],
      innerHTML: '', textContent: '', hidden: false, open: false,
      addEventListener() {}, append(option) { this.options.push(option); }, setAttribute() {},
      showModal() { this.open = true; }, close() { this.open = false; },
    });
    return elements.get(key);
  };
  const context = vm.createContext({
    document: {querySelector:get, querySelectorAll:()=>[], createElement:()=>({})},
    fetch: async () => ({ok:true, json:async()=>structuredClone(fixture)}),
    history: {replaceState(_a,_b,url) { context.lastURL = url; }},
    URLSearchParams, location: {pathname:'/letterboxd-series/', search, hash:''}, console,
  });
  vm.runInContext(source.replace(/init\(\);\s*$/, ''), context);
  await vm.runInContext('init()', context);
  return { get, run: script => vm.runInContext(script, context), context };
}
const {get, run, context} = await createHarness();
assert.equal(get('#total-series').textContent, 2);
assert.equal(get('#total-viewings').textContent, 4);
assert.equal(get('#total-rewatches').textContent, 2);
let html = get('#entries').innerHTML;
assert.ok(html.indexOf('heading-2026') < html.indexOf('heading-2025'));
assert.ok(html.indexOf('heading-2025') < html.indexOf('heading-2024'));
assert.ok(html.includes('No viewings recorded yet.'));
assert.ok(html.includes('A &lt;New&gt; Series'));
assert.ok(!html.includes('<b>personal</b>'));
assert.ok(html.includes('All seasons'));
run("$('#watch').value = 'rewatch'; render()");
assert.equal(get('#collection-count').textContent, 2);
run("$('#watch').value = 'all'; toggleTag('queer'); toggleTag('w/ alena ❤️')");
assert.equal(get('#collection-count').textContent, 1);
assert.equal(JSON.stringify(new URLSearchParams(context.lastURL.split('?')[1]).getAll('tag')), JSON.stringify(['queer', 'w/ alena ❤️']));
run("state.tags.clear(); $('#search').value = 'DEUTSCH'; state.view = 'list'; render()");
assert.equal(get('#collection-count').textContent, 1);
assert.equal(get('#entries').className, 'year-groups view-list');
run("$('#search').value = ''; $('#status').value = 'unfinished'; render()");
assert.equal(get('#collection-count').textContent, 1);
run("openDetail('two')");
assert.ok(get('#detail').open);
assert.ok(get('#detail-content').innerHTML.includes('Oct 2025'));
assert.ok(get('#detail-content').innerHTML.includes('All seasons'));
run("$('#status').value = 'all'; $('#search').value = 'nothing-here'; render()");
assert.equal(get('#empty-state').hidden, false);
run("$('#search').value = ''; $('#sort').value = 'oldest'; render()");
html = get('#entries').innerHTML;
assert.ok(html.indexOf('data-id="two"') < html.indexOf('data-id="four"')); // Unknown month last.
const restored = await createHarness('?view=list&tag=queer&tag=w%2F+alena+%E2%9D%A4%EF%B8%8F');
assert.equal(restored.get('#collection-count').textContent, 1);
assert.equal(restored.get('#entries').className, 'year-groups view-list');
console.log('Passed app checks: year groups, compact views, unique/viewing/rewatch totals, tags, filters, URL restoration, escaping, repeat history, unknown months.');
