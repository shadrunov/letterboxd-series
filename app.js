'use strict';
const $ = (selector) => document.querySelector(selector);
const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
const state = { entries: [], view: 'grid' };
const escapeHTML = (value) => String(value).replace(/[&<>"']/g, c => ({'&':'&amp;', '<':'&lt;', '>':'&gt;', '"':'&quot;', "'":'&#39;'}[c]));
const seasonLabel = (entry) => entry.seasons.map(n => `S${n}`).join(' · ');
const watchLabel = (entry) => `${months[Number(entry.watched.slice(5)) - 1]} ${entry.watched.slice(0, 4)}`;
function render() {
  const query = $('#search').value.trim().toLocaleLowerCase();
  const year = $('#year').value;
  const status = $('#status').value;
  const sort = $('#sort').value;
  const entries = state.entries.filter(entry => (year === 'all' || entry.watched.startsWith(year)) && (status === 'all' || entry.status === status) && entry.title.toLocaleLowerCase().includes(query));
  entries.sort((a, b) => sort === 'title' ? a.title.localeCompare(b.title) : sort === 'oldest' ? a.watched.localeCompare(b.watched) : b.watched.localeCompare(a.watched));
  $('#entries').className = state.view === 'grid' ? 'poster-grid' : 'diary-list';
  $('#entries').innerHTML = entries.map(entry => {
    const title = escapeHTML(entry.title);
    const unfinished = entry.status === 'unfinished';
    const marker = unfinished ? 'Ⅱ' : '✓';
    if (state.view === 'diary') {
      return `<article class="diary-row"><div class="diary-date"><strong>${months[Number(entry.watched.slice(5)) - 1]}</strong>${entry.watched.slice(0,4)}</div><img class="diary-poster" src="${entry.poster}" alt="" loading="lazy"><div><button class="card-title" type="button" data-id="${entry.id}">${title}</button><div class="card-meta">${entry.year}</div></div><div class="diary-seasons">${seasonLabel(entry)}<div class="diary-status ${unfinished ? 'unfinished' : ''}">${marker} ${unfinished ? 'Unfinished' : 'Watched'}</div></div></article>`;
    }
    return `<article class="series-card"><button class="poster-button" type="button" data-id="${entry.id}" aria-label="View ${title}, ${seasonLabel(entry)}, ${unfinished ? 'unfinished' : 'watched'} ${watchLabel(entry)}"><img src="${entry.poster}" alt="${title} poster" loading="lazy" width="200" height="300"><span class="status-marker ${unfinished ? 'unfinished' : ''}" aria-hidden="true">${marker}</span><span class="hover-label" aria-hidden="true">View series ↗</span></button><button class="card-title" type="button" data-id="${entry.id}">${title}</button><div class="card-meta"><span>${seasonLabel(entry)}</span><span>${watchLabel(entry)}</span></div>${unfinished ? '<div class="unfinished-label">Unfinished</div>' : ''}</article>`;
  }).join('');
  $('#collection-count').textContent = entries.length;
  $('#results-label').textContent = `${entries.length} ${entries.length === 1 ? 'series' : 'series'} · ${year === 'all' ? 'All years' : year} · ${sort === 'title' ? 'Alphabetically' : sort === 'oldest' ? 'First watched → latest' : 'Latest watched → first'}`;
  $('#empty-state').hidden = entries.length !== 0;
  document.querySelectorAll('[data-view]').forEach(button => button.setAttribute('aria-pressed', String(button.dataset.view === state.view)));
  const params = new URLSearchParams();
  if (year !== 'all') params.set('year', year);
  if (status !== 'all') params.set('status', status);
  if (query) params.set('q', $('#search').value.trim());
  if (sort !== 'newest') params.set('sort', sort);
  if (state.view !== 'grid') params.set('view', state.view);
  history.replaceState(null, '', `${location.pathname}${params.size ? '?' + params.toString() : ''}${location.hash}`);
  renderChart(year === 'all' ? [...new Set(state.entries.map(e => e.watched.slice(0,4)))].sort().at(-1) : year);
}
function renderChart(year) {
  const counts = months.map((_, index) => state.entries.filter(e => e.watched === `${year}-${String(index + 1).padStart(2,'0')}`).length);
  const max = Math.max(...counts, 1);
  $('#year-chart').innerHTML = counts.map((count, i) => `<div class="month-column ${count ? 'active' : ''}" title="${months[i]} ${year}: ${count} ${count === 1 ? 'series' : 'series'}"><span class="month-bar" style="height:${count ? 20 + count / max * 45 : 3}px" aria-hidden="true"></span><span>${months[i].slice(0,1)}</span><span class="sr-only">${months[i]} ${year}: ${count} series</span></div>`).join('');
  $('#year-chart').setAttribute('aria-label', `Series logged by month in ${year}`);
  $('#year-heading').textContent = `${year}. Every month, a different story.`;
}
function openDetail(id) {
  const entry = state.entries.find(entry => entry.id === id);
  if (!entry) return;
  // Render external metadata as text; never insert third-party HTML into the page.
  const summary = new DOMParser().parseFromString(entry.summary || '', 'text/html').body.textContent;
  $('#detail-content').innerHTML = `<div class="detail-layout"><img src="${entry.poster}" alt="${escapeHTML(entry.title)} poster"><div class="detail-copy"><span class="detail-year">${entry.year} · ${entry.genres.map(escapeHTML).join(' / ')}</span><h2>${escapeHTML(entry.title)}</h2><p class="detail-watch">${seasonLabel(entry)} · ${entry.status === 'unfinished' ? 'Unfinished' : 'Watched'}<br>Logged ${watchLabel(entry)}</p><p class="detail-summary">${escapeHTML(summary)}</p><a class="detail-link" href="${entry.url}" target="_blank" rel="noopener noreferrer">More on TVmaze ↗</a><p class="detail-credit">Summary &amp; poster via TVmaze.</p></div></div>`;
  $('#detail').showModal();
}
$('#entries').addEventListener('click', event => {
  const button = event.target.closest('[data-id]');
  if (button) openDetail(button.dataset.id);
});
$('#search').addEventListener('input', render);
['year', 'status', 'sort'].forEach(id => $(`#${id}`).addEventListener('change', render));
document.querySelectorAll('[data-view]').forEach(button => button.addEventListener('click', () => { state.view = button.dataset.view; render(); }));
$('#reset').addEventListener('click', () => { $('#search').value = ''; $('#year').value = 'all'; $('#status').value = 'all'; render(); });
$('.close-dialog').addEventListener('click', () => $('#detail').close());
$('#detail').addEventListener('click', event => { if (event.target === $('#detail')) { const rect = $('#detail').getBoundingClientRect(); if (event.clientX < rect.left || event.clientX > rect.right || event.clientY < rect.top || event.clientY > rect.bottom) $('#detail').close(); } });
async function init() {
  try {
    const response = await fetch('data/series.json');
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    state.entries = await response.json();
    const years = [...new Set(state.entries.map(entry => entry.watched.slice(0,4)))].sort().reverse();
    years.forEach(year => { const option = document.createElement('option'); option.value = year; option.textContent = year; $('#year').append(option); });
    $('#total-series').textContent = new Set(state.entries.map(entry => entry.id)).size;
    $('#total-seasons').textContent = state.entries.reduce((sum, entry) => sum + entry.seasons.length, 0);
    $('#total-years').textContent = years.length;
    const firstYear = [...years].sort()[0];
    $('.profile span:last-child').textContent = `Since ${firstYear}`;
    $('.stats>div:last-child span').textContent = years.length === 1 ? 'YEAR OF STORIES' : 'YEARS OF STORIES';
    const latest = [...state.entries].sort((a,b) => b.watched.localeCompare(a.watched))[0];
    if (latest) $('#latest-title').innerHTML = `${escapeHTML(latest.title)} <small>${watchLabel(latest)}</small>`;
    const params = new URLSearchParams(location.search);
    for (const key of ['year','status','sort']) if ([...$(`#${key}`).options].some(option => option.value === params.get(key))) $(`#${key}`).value = params.get(key);
    $('#search').value = params.get('q') || '';
    if (params.get('view') === 'diary') state.view = 'diary';
    render();
  } catch (error) {
    $('#load-error').hidden = false;
    console.error('Unable to load viewing diary:', error);
  }
}
init();
