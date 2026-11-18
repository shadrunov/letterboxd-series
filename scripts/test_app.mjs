// Rendering and interaction logic checks. This is not a browser/layout test.
import { readFile } from 'node:fs/promises';
import vm from 'node:vm';
import assert from 'node:assert/strict';

const source = await readFile(new URL('../app.js', import.meta.url), 'utf8');
const page = await readFile(new URL('../index.html', import.meta.url), 'utf8');
const fixture = {
  years: ['2024', '2025', '2026'],
  entries: [
    { id: 'one', showId: 'royals', title: 'Young Royals', watched: '2025-10', seasons: [1, 2, 3], watch: 'watch', status: 'watched', tags: ['queer'], notes: '' },
    { id: 'two', showId: 'royals', title: 'Young Royals', watched: '2026-01', seasons: [2, 3], watch: 'rewatch', status: 'watched', tags: ['queer', 'w/ alena ❤️'], notes: 'A repeat.', url:'https://www.themoviedb.org/tv/125910', letterboxd:'https://letterboxd.com/film/fixture/', mediaType:'tv', numberOfSeasons:3, numberOfEpisodes:18, showStatus:'Ended', seasonDetails:[
      {number:0,name:'Specials',airDate:null,episodeCount:1},
      {number:3,name:'Season 3',airDate:'2024-03-11',episodeCount:6,overview:'The final season.'},
      {number:1,name:'Season 1',airDate:'2021-07-01',episodeCount:6},
      {number:4,name:'Season 4',airDate:null,episodeCount:null},
    ] },
    { id: 'three', showId: 'royals', title: 'Young Royals', watched: '2026-01', seasons: [], allSeasons: true, watch: 'rewatch', status: 'unfinished', tags: ['queer'], notes: '' },
    { id: 'four', showId: 'new', title: 'A <New> Series', watched: '2026', seasons: [1], watch: 'watch', status: 'watched', tags: ['deutsch'], notes: '<b>personal</b>' },
  ],
};
async function createHarness(search = '', {inline = false, failFetch = false, data = fixture} = {}) {
  const markup = inline ? page.replace('<!-- DIARY_DATA -->', '<script id="diary-data" type="application/json"></script>') : page;
  const ids = new Set([...markup.matchAll(/\bid="([^"]+)"/g)].map(match => match[1]));
  const requests = [];
  const errors = [];
  const elements = new Map();
  const get = key => {
    if (key.startsWith('#') && !ids.has(key.slice(1))) return null;
    if (!elements.has(key)) elements.set(key, {
      value: key === '#sort' ? 'newest' : ['#year','#status','#watch'].includes(key) ? 'all' : '',
      options: [{value:'all'}, {value:'watched'}, {value:'unfinished'}, {value:'watch'}, {value:'rewatch'}, {value:'newest'}, {value:'oldest'}, {value:'title'}],
      innerHTML: '', textContent: key === '#diary-data' ? JSON.stringify(data) : '', hidden: key === '#load-error', open: false,
      addEventListener() {}, append(option) { this.options.push(option); }, setAttribute() {},
      showModal() { this.open = true; }, close() { this.open = false; },
    });
    return elements.get(key);
  };
  const context = vm.createContext({
    document: {querySelector:get, querySelectorAll:()=>[], createElement:()=>({})},
    fetch: async (...args) => { requests.push(args); if (failFetch) throw new Error('Network unavailable'); return {ok:true, json:async()=>structuredClone(data)}; },
    history: {replaceState(_a,_b,url) { context.lastURL = url; }},
    URLSearchParams, location: {pathname:'/letterboxd-series/', search, hash:''}, console:{log:console.log,error:(...args)=>errors.push(args)},
  });
  vm.runInContext(source.replace(/init\(\);\s*$/, ''), context);
  await vm.runInContext('init()', context);
  return { get, run: script => vm.runInContext(script, context), context, requests, errors };
}
const {get, run, context, requests} = await createHarness();
assert.equal(get('#load-error').hidden, true);
assert.equal(get('#diary-count'), null); // Removed IDs must never be fabricated by the mock.
assert.equal(requests[0][1].cache, 'no-store');
const embedded = await createHarness('', {inline:true, failFetch:true});
assert.equal(embedded.requests.length, 0);
assert.equal(embedded.get('#load-error').hidden, true);
assert.equal(embedded.get('#total-viewings').textContent, 4);
assert.ok(embedded.get('#entries').innerHTML.includes('Young Royals'));
const unavailable = await createHarness('', {failFetch:true});
assert.equal(unavailable.get('#load-error').hidden, false);
assert.equal(unavailable.errors.length, 1);
assert.equal(get('#total-series').textContent, 2);
assert.equal(get('#total-viewings').textContent, 4);
assert.equal(get('#total-rewatches').textContent, 2);
assert.equal(get('#this-year-stat').href, `?year=${new Date().getFullYear()}`);
assert.match(page, /href="\?section=watched"><strong id="total-series"/);
assert.match(page, /href="\?"><strong id="total-viewings"/);
assert.match(page, /href="\?watch=rewatch"><strong id="total-rewatches"/);
assert.equal(run('countThisYear(state.entries, 2026)'), 3);
assert.equal(run('countThisYear(state.entries, 2025)'), 1);
assert.equal(run('countThisYear(state.entries, 2024)'), 0);
assert.equal(get('#total-this-year').textContent, fixture.entries.filter(entry=>entry.watched.startsWith(String(new Date().getFullYear()))).length);
let html = get('#entries').innerHTML;
assert.ok(html.indexOf('heading-2026') < html.indexOf('heading-2025'));
assert.ok(html.indexOf('heading-2025') < html.indexOf('heading-2024'));
assert.ok(html.includes('No viewings recorded yet.'));
assert.ok(html.includes('A &lt;New&gt; Series'));
assert.ok(!html.includes('<b>personal</b>'));
assert.ok(html.includes('All seasons'));
assert.ok(html.includes('diary-table'));
assert.ok(html.includes('calendar-month calendar-year'));
assert.ok(html.includes('<strong>2026</strong>'));
assert.ok(html.includes('<td class="month-cell">Jan</td>'));
assert.ok(html.includes('<th scope="col">Year</th><th scope="col">Month</th>'));
assert.ok(!html.includes('<strong>Jan</strong>'));
assert.ok(html.includes('data-year="2026"'));
run("setYearFilter('2025')");
assert.equal(get('#year').value, '2025');
assert.equal(run('matchingEntries().length'), 1);
assert.equal(new URLSearchParams(context.lastURL.split('?')[1]).get('year'), '2025');
run("setYearFilter('1900')");
assert.equal(get('#year').value, '2025');
run("$('#year').value = 'all'; render()");
assert.ok(!/<th[^>]*>(Day|Rating|Review)<\/th>/.test(html));
assert.ok(html.includes('https://github.com/shadrunov/letterboxd-series/edit/main/diary/'));
run("$('#watch').value = 'rewatch'; render()");
assert.equal(run('matchingEntries().length'), 2);
run("$('#watch').value = 'all'; toggleTag('queer'); toggleTag('w/ alena ❤️')");
assert.equal(run('matchingEntries().length'), 1);
assert.equal(JSON.stringify(new URLSearchParams(context.lastURL.split('?')[1]).getAll('tag')), JSON.stringify(['queer', 'w/ alena ❤️']));
run("state.tags.clear(); $('#search').value = 'DEUTSCH'; state.view = 'list'; render()");
assert.equal(run('matchingEntries().length'), 1);
assert.equal(get('#entries').className, 'year-groups view-list');
run("$('#search').value = ''; $('#status').value = 'unfinished'; render()");
assert.equal(run('matchingEntries().length'), 1);
run("openDetail('two')");
assert.ok(get('#detail').open);
assert.ok(get('#detail-content').innerHTML.includes('Oct 2025'));
assert.ok(get('#detail-content').innerHTML.includes('All seasons'));
assert.ok(get('#detail-content').innerHTML.includes('TMDB ↗'));
assert.ok(get('#detail-content').innerHTML.includes('Letterboxd ↗'));
assert.ok(!get('#detail-content').innerHTML.includes('TVmaze'));
const detailsHTML = get('#detail-content').innerHTML;
assert.ok(detailsHTML.includes('3 seasons · 18 episodes · Ended'));
assert.ok(detailsHTML.includes('class="season-year-cell">2024</td>'));
assert.ok(detailsHTML.includes('class="season-episodes-cell">6</td>'));
assert.ok(detailsHTML.includes('class="season-table"'));
assert.ok(detailsHTML.includes('Release date TBA'));
assert.ok(detailsHTML.includes('Episode count unavailable'));
assert.ok(detailsHTML.indexOf('Season 1') < detailsHTML.indexOf('Season 3'));
assert.ok(detailsHTML.indexOf('Season 3') < detailsHTML.indexOf('Specials'));
assert.ok(detailsHTML.indexOf('detail-credit') > detailsHTML.indexOf('seasons-section'));
assert.equal((detailsHTML.match(/class="history-entry"/g) || []).length, 2);
run("openDetail('four')");
assert.ok(!get('#detail-content').innerHTML.includes('Viewing history'));
run("openDetail('two')");
assert.ok(detailsHTML.includes('aria-label="Watched 2 times"'));
assert.ok(detailsHTML.includes('class="season-watch-count" aria-hidden="true">2</span>'));
assert.equal(run("seasonWatchCount(state.entries[1], {number:1,airDate:'2021-07-01'})"), 1);
assert.equal(run("seasonWatchCount(state.entries[1], {number:3,airDate:'2024-03-11'})"), 2);
assert.equal(run("seasonWatchCount(state.entries[1], {number:4,airDate:'2027-01-01'})"), 0);
assert.equal(run('watchedEye(0)'), '');
assert.ok(!run('watchedEye(1)').includes('season-watch-count'));
// A completed full-series rewatch counts existing seasons, never later releases.
run("state.entries.push({id:'all-fixture',showId:'royals',watch:'rewatch',status:'watched',seasons:[],allSeasons:true,watched:'2026-02'})");
assert.equal(run("seasonWatchCount(state.entries[1], {number:3,airDate:'2024-03-11'})"), 3);
assert.equal(run("seasonWatchCount(state.entries[1], {number:4,airDate:'2027-01-01'})"), 0);
assert.equal(run("seasonWatchCount(state.entries[1], {number:0,airDate:'2022-01-01'})"), 0);
assert.equal(run("seasonWatchCount(state.entries[1], {number:5,airDate:null})"), 0);
run('state.entries.pop()');
assert.equal(run("seasonsHTML({mediaType:'movie'})"), '');
run("$('#status').value = 'all'; $('#search').value = 'nothing-here'; render()");
assert.equal(get('#empty-state').hidden, false);
run("$('#search').value = ''; $('#sort').value = 'oldest'; render()");
html = get('#entries').innerHTML;
assert.ok(html.indexOf('data-id="two"') < html.indexOf('data-id="four"')); // Unknown month last.
const restored = await createHarness('?view=list&tag=queer&tag=w%2F+alena+%E2%9D%A4%EF%B8%8F');
assert.equal(restored.run('matchingEntries().length'), 1);
assert.equal(restored.get('#entries').className, 'year-groups view-list');
run("$('#sort').value = 'newest'; setSection('watched')");
html = get('#entries').innerHTML;
assert.equal(get('#entries').className, 'watched-collection view-large');
assert.equal((html.match(/class="viewing /g) || []).length, 2);
assert.ok(!html.includes('heading-2026'));
assert.ok(!html.includes('diary-table'));
assert.ok(html.includes('2 viewings'));
assert.ok(html.includes('S1 · S2 · S3'));
run("state.view = 'small'; state.views.watched = 'small'; render()");
assert.equal(get('#entries').className, 'watched-collection view-small');
run("setSection('diary')");
assert.equal(get('#entries').className, 'year-groups view-list');
run("state.view = 'large'; render()");
assert.equal(get('#entries').className, 'year-groups view-large');
run("state.view = 'small'; render()");
assert.equal(get('#entries').className, 'year-groups view-small');
const watchedListURL = await createHarness('?section=watched&view=list');
assert.equal(watchedListURL.get('#entries').className, 'watched-collection view-large');
// Separate season logs merge across years, while rewatches retain their own row.
const seasonRecord = (id, date, seasons, tags, extra={}) => ({...fixture.entries[1], id, watched:date.slice(0,7), watchDate:date, seasons, tags, watch:'watch', status:'watched', notes:'', ...extra});
const seasonFixture = {years:['2024','2025','2026'], entries:[
  seasonRecord('season-one','2024-06-01',[1],['w/ alena ❤️'],{notes:'First season note'}),
  seasonRecord('season-two','2025-07-12',[2],['in dublin']),
  seasonRecord('season-three','2026-02-28',[3],['queer']),
  seasonRecord('repeat-one','2026-03-03',[1],['rewatch tag'],{watch:'rewatch'}),
]};
const combined = await createHarness('', {data:seasonFixture});
assert.equal(combined.run('matchingEntries().length'), 2);
assert.equal(combined.get('#total-viewings').textContent, 2);
let combinedHTML = combined.get('#entries').innerHTML;
assert.ok(combinedHTML.includes('class="tags-heading">Tags</th><th scope="col">Released'));
assert.ok(combinedHTML.includes('S1 · S2 · S3'));
assert.ok(!combinedHTML.includes('heading-2024'));
assert.ok(!combinedHTML.includes('heading-2025'));
assert.ok(!combinedHTML.match(/<td class="series-cell">([\s\S]*?)<\/td>/)[1].includes('entry-tags'));
assert.equal(combined.run("matchingEntries().find(entry=>entry.watch==='watch').watched"), '2026-02');
assert.equal(combined.run("matchingEntries().find(entry=>entry.watch==='watch').watchDate"), '2026-02-28');
combined.run("toggleTag('w/ alena ❤️'); toggleTag('in dublin')");
assert.equal(combined.run('matchingEntries().length'), 1);
combined.run("openDetail('season-three')");
assert.ok(combined.get('#detail-content').innerHTML.includes('First season note'));
assert.ok(combined.get('#detail-content').innerHTML.includes('history-entry'));
assert.equal(combined.run("seasonTags(state.entries[0], {number:2}).join(',')"), 'in dublin');
assert.ok(!combined.run("seasonTags(state.entries[0], {number:2}).includes('w/ alena ❤️')"));
assert.equal(combined.run("seasonWatchCount(state.entries[0], {number:1})"), 2);
assert.equal(combined.run("seasonWatchCount(state.entries[0], {number:2})"), 1);
combined.run("state.tags.clear(); toggleTag('w/ alena ❤️'); toggleTag('rewatch tag')");
assert.equal(combined.run('matchingEntries().length'), 0);
combined.run("state.tags.clear(); setYearFilter('2024')");
assert.equal(combined.run('matchingEntries().length'), 0);
assert.equal(combined.get('#empty-state').hidden, false);
assert.equal(combined.run("latestEntry([{watchDate:'2026-03-20'},{watchDate:'2026-03-01'}]).watchDate"), '2026-03-20');
assert.equal(combined.run('JSON.stringify(state.entries)'), JSON.stringify(seasonFixture.entries));
console.log('Passed app checks: year groups, compact views, unique/viewing/rewatch totals, tags, filters, URL restoration, escaping, repeat history, unknown months.');

assert.ok(!run('cardHTML(state.entries[0], true)').includes('entry-tags'));
assert.ok(run('cardHTML(state.entries[0], false)').includes('entry-tags'));

const heartstopperDiary = await createHarness('', {data:{years:['2024','2026'], entries:[
  seasonRecord('heartstopper-2026','2026-07',[3],['w/ andrei'],{title:'Heartstopper',watch:'rewatch'}),
  seasonRecord('heartstopper-s3','2024-10',[3],['queer'],{title:'Heartstopper'}),
  seasonRecord('heartstopper-s12','2024-09',[1,2],['queer'],{title:'Heartstopper'}),
]}});
assert.equal(heartstopperDiary.run('state.displayEntries.length'), 2);
assert.equal(heartstopperDiary.run("state.displayEntries.find(e=>e.watch==='watch').watched"), '2024-10');
assert.deepEqual(Array.from(heartstopperDiary.run("state.displayEntries.find(e=>e.watch==='watch').seasons")), [1,2,3]);
assert.deepEqual(Array.from(heartstopperDiary.run("state.displayEntries.find(e=>e.watch==='rewatch').seasons")), [3]);
const splitRecordDiary = await createHarness('', {data:{years:['2026'],entries:[
  seasonRecord('source-watch','2026-07',[2],[],{sourceId:'one-yaml-record'}),
  seasonRecord('source-rewatch','2026-07',[1],[],{sourceId:'one-yaml-record',watch:'rewatch'}),
]}});
assert.equal(splitRecordDiary.get('#total-viewings').textContent, 1);
assert.equal(splitRecordDiary.run('countThisYear(state.entries, 2026)'), 1);
assert.equal(splitRecordDiary.get('#total-rewatches').textContent, 1);
assert.equal(splitRecordDiary.run('watchedEntries(state.entries)[0].viewingCount'), 1);

const roundData = {years:['2026'],entries:[
  seasonRecord('round1-s1','2026-11',[1],['in dublin'],{viewingId:'royals:1',viewingNumber:1,viewingStatus:'watched'}),
  seasonRecord('round1-s23','2026-11',[2,3],['queer'],{viewingId:'royals:1',viewingNumber:1,viewingStatus:'watched'}),
]};
const oneRound = await createHarness('', {data:roundData});
assert.equal(oneRound.get('#total-viewings').textContent, 1);
assert.equal(oneRound.run('watchedEntries(state.entries)[0].viewingCount'), 1);
oneRound.run("openDetail('round1-s23')");
assert.ok(!oneRound.get('#detail-content').innerHTML.includes('Viewing history'));
assert.equal(oneRound.run("seasonTags(state.displayEntries[0], {number:1}).join(',')"), 'in dublin');
roundData.entries.push(
  seasonRecord('round2-s1','2026-11',[1],['again'],{watch:'rewatch',viewingId:'royals:2',viewingNumber:2,viewingStatus:'watched'}),
  seasonRecord('round2-s23','2026-11',[2,3],['again'],{watch:'rewatch',viewingId:'royals:2',viewingNumber:2,viewingStatus:'watched'}),
);
const twoRounds = await createHarness('', {data:roundData});
assert.equal(twoRounds.get('#total-viewings').textContent, 2);
assert.equal(twoRounds.get('#total-rewatches').textContent, 1);
assert.equal(twoRounds.run('state.displayEntries.length'), 2);
assert.equal(twoRounds.run('sortEntries([...state.displayEntries])[0].viewingNumber'), 2);
assert.equal(twoRounds.run('watchedEntries(state.entries)[0].viewingCount'), 2);
twoRounds.run("openDetail('round2-s23')");
assert.equal((twoRounds.get('#detail-content').innerHTML.match(/class="history-entry"/g) || []).length, 1);
assert.equal(twoRounds.run("seasonWatchCount(state.entries[0], {number:1})"), 2);
assert.equal(twoRounds.run('countThisYear(state.entries,2026)'), 2);
