'use strict';
const $ = selector => document.querySelector(selector);
const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
const state = { entries: [], years: [], view: 'cards', tags: new Set() };
const escapeHTML = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;', '<':'&lt;', '>':'&gt;', '"':'&quot;', "'":'&#39;'}[c]));
const seasonLabel = entry => entry.mediaType === 'movie' ? 'Film' : entry.allSeasons ? 'All seasons' : entry.seasons.map(n => `S${n}`).join(' · ');
const watchLabel = entry => entry.watched.length === 4 ? `${entry.watched} · month not recorded` : `${months[Number(entry.watched.slice(5)) - 1]} ${entry.watched.slice(0, 4)}`;
const tagsHTML = entry => entry.tags.map(tag => `<button class="tag" type="button" data-tag="${escapeHTML(tag)}" aria-pressed="${state.tags.has(tag)}">${escapeHTML(tag)}</button>`).join('');
function posterHTML(entry) {
  return entry.poster ? `<img src="${escapeHTML(entry.poster)}" alt="" loading="lazy" width="60" height="90">` : '<span class="poster-placeholder" aria-hidden="true">tv</span>';
}
function entryHTML(entry) {
  const title = escapeHTML(entry.title);
  const unfinished = entry.status === 'unfinished';
  return `<article class="viewing ${unfinished ? 'is-unfinished' : ''}">
    <button class="viewing-poster" type="button" data-id="${entry.id}" aria-label="Details for ${title}, ${escapeHTML(watchLabel(entry))}">${posterHTML(entry)}</button>
    <div class="viewing-info"><button class="card-title" type="button" data-id="${entry.id}">${title} ${entry.year ? `<span class="release-year">${entry.year}</span>` : ''}</button>
      <p class="viewing-seasons">${seasonLabel(entry)}${entry.watch === 'rewatch' ? ' <span class="rewatch-badge">↻ Rewatch</span>' : ''}</p>
      <div class="entry-tags">${tagsHTML(entry)}</div>${entry.notes ? `<p class="viewing-notes">${escapeHTML(entry.notes)}</p>` : ''}
    </div><div class="viewing-when"><span>${entry.watched.length === 4 ? 'Month unknown' : months[Number(entry.watched.slice(5)) - 1]}</span><span class="watch-status">${unfinished ? 'Ⅱ Unfinished' : '✓ Watched'}</span></div>
  </article>`;
}
function matchingEntries() {
  const query = $('#search').value.trim().toLocaleLowerCase();
  return state.entries.filter(entry =>
    ($('#year').value === 'all' || entry.watched.startsWith($('#year').value)) &&
    ($('#status').value === 'all' || entry.status === $('#status').value) &&
    ($('#watch').value === 'all' || entry.watch === $('#watch').value) &&
    [...state.tags].every(tag => entry.tags.includes(tag)) &&
    [entry.title, entry.notes, ...entry.tags].join(' ').toLocaleLowerCase().includes(query));
}
function sortEntries(entries) {
  return entries.sort((a, b) => {
    if ($('#sort').value === 'title') return a.title.localeCompare(b.title) || a.watched.localeCompare(b.watched);
    // Unknown watch months stay at the end in either direction.
    if (a.watched.length !== b.watched.length) return b.watched.length - a.watched.length;
    return $('#sort').value === 'oldest' ? a.watched.localeCompare(b.watched) : b.watched.localeCompare(a.watched);
  });
}
function renderTags() {
  const allTags = [...new Set(state.entries.flatMap(entry => entry.tags))].sort((a,b) => a.localeCompare(b));
  $('#tag-filters').innerHTML = `<button class="tag all-tags" type="button" data-clear-tags aria-pressed="${state.tags.size === 0}">All tags</button>` + allTags.map(tag => `<button class="tag" type="button" data-tag="${escapeHTML(tag)}" aria-pressed="${state.tags.has(tag)}">${escapeHTML(tag)} <span>${state.entries.filter(entry => entry.tags.includes(tag)).length}</span></button>`).join('');
  $('#tag-help').hidden = allTags.length > 0;
}
function render() {
  const entries = matchingEntries();
  const hasFilters = $('#search').value.trim() || $('#status').value !== 'all' || $('#watch').value !== 'all' || state.tags.size;
  const years = state.years.filter(year => $('#year').value === 'all' || year === $('#year').value);
  $('#entries').className = `year-groups view-${state.view}`;
  $('#entries').innerHTML = years.map(year => {
    const group = sortEntries(entries.filter(entry => entry.watched.startsWith(year)));
    if (!group.length && hasFilters) return '';
    const shows = new Set(group.map(entry => entry.showId)).size;
    return `<section class="year-group" aria-labelledby="heading-${year}"><div class="year-heading"><div><h3 id="heading-${year}">${year}</h3><span>${group.length} ${group.length === 1 ? 'viewing' : 'viewings'} · ${shows} series</span></div><a href="https://github.com/shadrunov/letterboxd-series/edit/main/diary/${year}.md" target="_blank" rel="noopener noreferrer" aria-label="Edit ${year} diary table">Edit year <span aria-hidden="true">↗</span></a></div><div class="year-entries">${group.map(entryHTML).join('') || '<p class="empty-year">No viewings recorded yet.</p>'}</div></section>`;
  }).join('');
  $('#collection-count').textContent = entries.length;
  $('#results-label').textContent = `${entries.length} ${entries.length === 1 ? 'viewing' : 'viewings'} · ${new Set(entries.map(entry => entry.showId)).size} series${state.tags.size > 1 ? ' · Matching all selected tags' : ''}`;
  $('#empty-state').hidden = entries.length > 0 || !hasFilters;
  document.querySelectorAll('[data-view]').forEach(button => button.setAttribute('aria-pressed', String(button.dataset.view === state.view)));
  renderTags();
  const params = new URLSearchParams();
  for (const key of ['year','status','watch']) if ($(`#${key}`).value !== 'all') params.set(key, $(`#${key}`).value);
  if ($('#search').value.trim()) params.set('q', $('#search').value.trim());
  if ($('#sort').value !== 'newest') params.set('sort', $('#sort').value);
  if (state.view !== 'cards') params.set('view', state.view);
  [...state.tags].forEach(tag => params.append('tag', tag));
  history.replaceState(null, '', `${location.pathname}${params.size ? '?' + params.toString() : ''}${location.hash}`);
}
function toggleTag(tag) {
  if (state.tags.has(tag)) state.tags.delete(tag); else state.tags.add(tag);
  render();
}
function openDetail(id) {
  const entry = state.entries.find(entry => entry.id === id);
  if (!entry) return;
  const others = state.entries.filter(other => other.showId === entry.showId && other.id !== id).sort((a,b) => b.watched.localeCompare(a.watched));
  $('#detail-content').innerHTML = `<div class="detail-layout"><div class="detail-poster">${posterHTML(entry)}</div><div class="detail-copy"><span class="detail-year">${[entry.year, ...(entry.genres || [])].filter(Boolean).map(escapeHTML).join(' · ')}</span><h2>${escapeHTML(entry.title)}</h2><p class="detail-watch">${seasonLabel(entry)} · ${entry.status === 'unfinished' ? 'Unfinished' : 'Watched'}${entry.watch === 'rewatch' ? ' · ↻ Rewatch' : ''}<br>Logged ${escapeHTML(watchLabel(entry))}</p><div class="entry-tags">${tagsHTML(entry)}</div>${entry.notes ? `<p class="detail-note">${escapeHTML(entry.notes)}</p>` : ''}${others.length ? `<div class="other-viewings"><h3>Also in the diary</h3>${others.map(other => `<p>${escapeHTML(watchLabel(other))} · ${seasonLabel(other)}${other.watch === 'rewatch' ? ' · ↻ Rewatch' : ''}${other.status === 'unfinished' ? ' · Unfinished' : ''}</p>`).join('')}</div>` : ''}<p class="detail-summary">${escapeHTML(entry.summary || '')}</p>${entry.url ? `<a class="detail-link" href="${escapeHTML(entry.url)}" target="_blank" rel="noopener noreferrer">More on ${escapeHTML(entry.source || 'TVmaze')} ↗</a><p class="detail-credit">Summary &amp; poster via ${escapeHTML(entry.source || 'TVmaze')}.</p>` : ''}</div></div>`;
  $('#detail').showModal();
}
$('#entries').addEventListener('click', event => {
  const tag = event.target.closest('[data-tag]');
  if (tag) { toggleTag(tag.dataset.tag); return; }
  const button = event.target.closest('[data-id]');
  if (button) openDetail(button.dataset.id);
});
$('#tag-filters').addEventListener('click', event => {
  const tag = event.target.closest('[data-tag]');
  if (tag) toggleTag(tag.dataset.tag);
  if (event.target.closest('[data-clear-tags]')) { state.tags.clear(); render(); }
});
$('#detail-content').addEventListener('click', event => {
  const tag = event.target.closest('[data-tag]');
  if (tag) { $('#detail').close(); toggleTag(tag.dataset.tag); }
});
$('#search').addEventListener('input', render);
['year','status','watch','sort'].forEach(id => $(`#${id}`).addEventListener('change', render));
document.querySelectorAll('[data-view]').forEach(button => button.addEventListener('click', () => { state.view = button.dataset.view; render(); }));
$('#reset').addEventListener('click', () => {
  $('#search').value = '';
  ['year','status','watch'].forEach(key => $(`#${key}`).value = 'all');
  state.tags.clear();
  render();
});
$('.close-dialog').addEventListener('click', () => $('#detail').close());
$('#detail').addEventListener('click', event => {
  if (event.target === $('#detail')) {
    const rect = $('#detail').getBoundingClientRect();
    if (event.clientX < rect.left || event.clientX > rect.right || event.clientY < rect.top || event.clientY > rect.bottom) $('#detail').close();
  }
});
async function init() {
  try {
    const response = await fetch('data/diary.json');
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const diary = await response.json();
    state.entries = diary.entries;
    state.years = diary.years.sort().reverse();
    state.years.forEach(year => { const option = document.createElement('option'); option.value = year; option.textContent = year; $('#year').append(option); });
    $('#total-series').textContent = new Set(state.entries.map(entry => entry.showId)).size;
    $('#total-viewings').textContent = state.entries.length;
    $('#total-rewatches').textContent = state.entries.filter(entry => entry.watch === 'rewatch').length;
    const firstYear = state.entries.map(entry => entry.watched.slice(0,4)).sort()[0];
    $('.profile span:last-child').textContent = firstYear ? `Since ${firstYear}` : 'A viewing diary';
    const latest = [...state.entries].sort((a,b) => b.watched.localeCompare(a.watched))[0];
    if (latest) $('#latest-title').innerHTML = `${escapeHTML(latest.title)} <small>${escapeHTML(watchLabel(latest))}</small>`;
    const params = new URLSearchParams(location.search);
    for (const key of ['year','status','watch','sort']) if ([...$(`#${key}`).options].some(option => option.value === params.get(key))) $(`#${key}`).value = params.get(key);
    $('#search').value = params.get('q') || '';
    if (['list','diary'].includes(params.get('view'))) state.view = 'list';
    const knownTags = new Set(state.entries.flatMap(entry => entry.tags));
    state.tags = new Set(params.getAll('tag').filter(tag => knownTags.has(tag)));
    render();
  } catch (error) {
    $('#load-error').hidden = false;
    console.error('Unable to load viewing diary:', error);
  }
}
init();
