'use strict';
const $ = selector => document.querySelector(selector);
const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
const state = { entries: [], years: [], mode: 'diary', view: 'list', views: {diary:'list', watched:'large'}, tags: new Set() };
const escapeHTML = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;', '<':'&lt;', '>':'&gt;', '"':'&quot;', "'":'&#39;'}[c]));
const seasonLabel = entry => entry.mediaType === 'movie' ? 'Film' : entry.allSeasons ? 'All seasons' : entry.seasons.map(n => `S${n}`).join(' · ');
const watchLabel = entry => entry.watched.length === 4 ? `${entry.watched} · month not recorded` : `${months[Number(entry.watched.slice(5)) - 1]} ${entry.watched.slice(0, 4)}`;
const editURL = entry => entry.editUrl || `https://github.com/shadrunov/letterboxd-series/edit/main/diary/${entry.watched.slice(0,4)}.yaml`;
const editLink = entry => `<a class="edit-entry" href="${escapeHTML(editURL(entry))}" target="_blank" rel="noopener noreferrer" aria-label="Edit ${escapeHTML(entry.title)} viewing on GitHub" title="Edit on GitHub">✎</a>`;
const tagsHTML = entry => entry.tags.map(tag => `<button class="tag" type="button" data-tag="${escapeHTML(tag)}" aria-pressed="${state.tags.has(tag)}">${escapeHTML(tag)}</button>`).join('');
function posterHTML(entry) {
  return entry.poster ? `<img src="${escapeHTML(entry.poster)}" alt="" loading="lazy" width="200" height="300">` : '<span class="poster-placeholder" aria-hidden="true">tv</span>';
}
function cardHTML(entry, aggregate = false) {
  const title = escapeHTML(entry.title);
  return `<article class="viewing ${entry.status === 'unfinished' ? 'is-unfinished' : ''}">
    <button class="viewing-poster" type="button" data-id="${entry.id}" aria-label="Details for ${title}">${posterHTML(entry)}</button>
    <div class="viewing-info"><button class="card-title" type="button" data-id="${entry.id}">${title} ${entry.year ? `<span class="release-year">${entry.year}</span>` : ''}</button>
      <p class="viewing-seasons">${seasonLabel(entry)}${!aggregate && entry.watch === 'rewatch' ? ' <span class="rewatch-badge">↻ Rewatch</span>' : ''}</p>
      <div class="entry-tags">${tagsHTML(entry)}</div>
    </div><div class="viewing-when"><span>${escapeHTML(watchLabel(entry))}</span>${aggregate ? `<span class="viewing-count">${entry.viewingCount} ${entry.viewingCount === 1 ? 'viewing' : 'viewings'}</span>` : `<span class="watch-status">${entry.status === 'unfinished' ? 'Ⅱ Unfinished' : '✓ Watched'}</span>${editLink(entry)}`}</div>
  </article>`;
}
function diaryTable(groups) {
  return `<div class="diary-table-wrap"><table class="diary-table"><thead><tr><th scope="col">Year</th><th scope="col">Month</th><th scope="col">Series</th><th scope="col">Released</th><th scope="col">Seasons</th><th scope="col">Rewatch</th><th scope="col">Edit</th></tr></thead>${groups.map(({year, entries}) => {
    const calendar = `<div class="calendar-month calendar-year"><strong>${year}</strong></div>`;
    const rows = entries.map((entry,index) => {
      const month = entry.watched.length === 4 ? '<span aria-label="Month not recorded">—</span>' : months[Number(entry.watched.slice(5)) - 1];
      return `<tr><td class="year-cell">${index === 0 ? calendar : `<span class="sr-only">${year}</span>`}</td><td class="month-cell">${month}</td><td class="series-cell"><div class="diary-series"><button class="viewing-poster" type="button" data-id="${entry.id}" aria-label="Details for ${escapeHTML(entry.title)}">${posterHTML(entry)}</button><div><button class="card-title" type="button" data-id="${entry.id}">${escapeHTML(entry.title)}</button><div class="entry-tags">${tagsHTML(entry)}</div></div></div></td><td class="released-cell">${entry.year || '—'}</td><td class="seasons-cell">${seasonLabel(entry)}${entry.status === 'unfinished' ? '<span class="unfinished-text">Unfinished</span>' : ''}</td><td class="rewatch-cell">${entry.watch === 'rewatch' ? '<span class="rewatch-icon" aria-label="Rewatch" title="Rewatch">↻</span>' : '<span class="sr-only">Regular watch</span>'}</td><td class="edit-cell">${editLink(entry)}</td></tr>`;
    }).join('');
    return `<tbody id="heading-${year}" aria-label="${year}">${rows || `<tr><td class="year-cell">${calendar}</td><td colspan="6" class="empty-year">No viewings recorded yet.</td></tr>`}</tbody>`;
  }).join('')}</table></div>`;
}
function matchingEntries() {
  const query = $('#search').value.trim().toLocaleLowerCase();
  return state.entries.filter(entry =>
    ($('#year').value === 'all' || entry.watched.startsWith($('#year').value)) &&
    (state.mode === 'watched' ? entry.status === 'watched' : $('#status').value === 'all' || entry.status === $('#status').value) &&
    ($('#watch').value === 'all' || entry.watch === $('#watch').value) &&
    [...state.tags].every(tag => entry.tags.includes(tag)) &&
    [entry.title, entry.notes, ...entry.tags].join(' ').toLocaleLowerCase().includes(query));
}
function sortEntries(entries) {
  return entries.sort((a,b) => {
    if ($('#sort').value === 'title') return a.title.localeCompare(b.title) || b.watched.localeCompare(a.watched);
    if (a.watched.slice(0,4) === b.watched.slice(0,4) && a.watched.length !== b.watched.length) return b.watched.length - a.watched.length;
    return $('#sort').value === 'oldest' ? a.watched.localeCompare(b.watched) : b.watched.localeCompare(a.watched);
  });
}
function watchedEntries(entries) {
  const groups = new Map();
  for (const entry of entries) {
    if (entry.status !== 'watched') continue;
    if (!groups.has(entry.showId)) groups.set(entry.showId, []);
    groups.get(entry.showId).push(entry);
  }
  return sortEntries([...groups.values()].map(group => {
    const latest = [...group].sort((a,b) => b.watched.localeCompare(a.watched))[0];
    return {...latest, seasons:[...new Set(group.flatMap(entry => entry.seasons))].sort((a,b) => a-b), allSeasons:group.some(entry => entry.allSeasons), tags:[...new Set(group.flatMap(entry => entry.tags))], viewingCount:group.length};
  }));
}
function renderTags() {
  const entries = state.mode === 'watched' ? state.entries.filter(entry => entry.status === 'watched') : state.entries;
  const tags = [...new Set(entries.flatMap(entry => entry.tags))].sort((a,b) => a.localeCompare(b));
  $('#tag-filters').innerHTML = `<button class="tag all-tags" type="button" data-clear-tags aria-pressed="${state.tags.size === 0}">All tags</button>` + tags.map(tag => `<button class="tag" type="button" data-tag="${escapeHTML(tag)}" aria-pressed="${state.tags.has(tag)}">${escapeHTML(tag)} <span>${entries.filter(entry => entry.tags.includes(tag)).length}</span></button>`).join('');
  $('#tag-help').hidden = tags.length > 0;
}
function render() {
  const entries = matchingEntries();
  const watched = state.mode === 'watched';
  const hasFilters = $('#search').value.trim() || (!watched && $('#status').value !== 'all') || $('#watch').value !== 'all' || state.tags.size;
  if (watched && state.view === 'list') state.view = state.views.watched;
  $('#collection-title').textContent = watched ? 'Watched' : 'Diary';
  $('#status-filter').hidden = watched;
  document.querySelectorAll('[data-section]').forEach(button => button.setAttribute('aria-pressed', String(button.dataset.section === state.mode)));
  document.querySelectorAll('[data-view]').forEach(button => {
    button.hidden = watched && button.dataset.view === 'list';
    button.setAttribute('aria-pressed', String(button.dataset.view === state.view));
  });
  if (watched) {
    const shows = watchedEntries(entries);
    $('#entries').className = `watched-collection view-${state.view}`;
    $('#entries').innerHTML = `<div class="year-entries">${shows.map(entry => cardHTML(entry, true)).join('')}</div>`;
    $('#results-label').textContent = `${shows.length} series watched · One card per series`;
  } else {
    $('#entries').className = `year-groups view-${state.view}`;
    const groups = state.years.filter(year => $('#year').value === 'all' || year === $('#year').value).map(year => ({year, entries:sortEntries(entries.filter(entry => entry.watched.startsWith(year)))})).filter(group => group.entries.length || !hasFilters);
    $('#entries').innerHTML = state.view === 'list' ? (groups.length ? diaryTable(groups) : '') : groups.map(({year, entries:group}) => {
      return `<section class="year-group" aria-labelledby="heading-${year}"><div class="year-heading"><div><h3 id="heading-${year}">${year}</h3><span>${group.length} ${group.length === 1 ? 'viewing' : 'viewings'}</span></div><a href="https://github.com/shadrunov/letterboxd-series/edit/main/diary/${year}.yaml" target="_blank" rel="noopener noreferrer">Edit year ↗</a></div>${group.length ? `<div class="year-entries">${group.map(entry => cardHTML(entry)).join('')}</div>` : '<p class="empty-year">No viewings recorded yet.</p>'}</section>`;
    }).join('');
    $('#results-label').textContent = `${entries.length} ${entries.length === 1 ? 'viewing' : 'viewings'} · ${new Set(entries.map(entry => entry.showId)).size} series${state.tags.size > 1 ? ' · Matching all selected tags' : ''}`;
  }
  $('#empty-state').hidden = entries.length > 0 || (!watched && !hasFilters);
  renderTags();
  const params = new URLSearchParams();
  if (watched) params.set('section','watched');
  for (const key of ['year','status','watch']) if ((!watched || key !== 'status') && $(`#${key}`).value !== 'all') params.set(key,$(`#${key}`).value);
  if ($('#search').value.trim()) params.set('q',$('#search').value.trim());
  if ($('#sort').value !== 'newest') params.set('sort',$('#sort').value);
  if (state.view !== (watched ? 'large' : 'list')) params.set('view',state.view);
  [...state.tags].forEach(tag => params.append('tag',tag));
  history.replaceState(null,'',`${location.pathname}${params.size ? '?' + params : ''}${location.hash}`);
}
function toggleTag(tag) { if (state.tags.has(tag)) state.tags.delete(tag); else state.tags.add(tag); render(); }
function setSection(mode) {
  state.views[state.mode] = state.view;
  state.mode = mode;
  state.view = state.views[mode];
  render();
}
function seasonWatchCount(entry, season) {
  return state.entries.filter(viewing => viewing.showId === entry.showId && viewing.status === 'watched' && (
    viewing.seasons.includes(season.number) ||
    (viewing.allSeasons && season.number > 0 && season.airDate && season.airDate.slice(0, viewing.watched.length) <= viewing.watched)
  )).length;
}
function watchedEye(count) {
  if (!count) return '';
  const label = count === 1 ? 'Watched once' : `Watched ${count} times`;
  return `<span class="season-watched" role="img" aria-label="${label}" title="${label}"><svg viewBox="0 0 40 26" aria-hidden="true" focusable="false"><path fill="currentColor" fill-rule="evenodd" d="M1 13Q20-12 39 13Q20 38 1 13ZM20 5a8 8 0 1 0 0 16a8 8 0 1 0 0-16Z"/><circle cx="20" cy="13" r="4.5" fill="currentColor"/></svg>${count > 1 ? `<span class="season-watch-count" aria-hidden="true">${count}</span>` : ''}</span>`;
}
function seasonsHTML(entry) {
  if (entry.mediaType !== 'tv') return '';
  const seasons = [...(entry.seasonDetails || [])].sort((a,b) => (a.number === 0) - (b.number === 0) || a.number - b.number);
  const facts = [];
  if (Number.isInteger(entry.numberOfSeasons)) facts.push(`${entry.numberOfSeasons} ${entry.numberOfSeasons === 1 ? 'season' : 'seasons'}`);
  if (Number.isInteger(entry.numberOfEpisodes)) facts.push(`${entry.numberOfEpisodes} ${entry.numberOfEpisodes === 1 ? 'episode' : 'episodes'}`);
  if (entry.showStatus) facts.push(escapeHTML(entry.showStatus));
  return `<section class="seasons-section" aria-labelledby="seasons-heading"><div class="seasons-heading"><h3 id="seasons-heading">Seasons</h3><p>${facts.join(' · ')}</p></div>${seasons.length ? `<ol class="season-list">${seasons.map(season => {
    const year = season.airDate && /^\d{4}-/.test(season.airDate) ? season.airDate.slice(0,4) : 'Release date TBA';
    const episodes = Number.isInteger(season.episodeCount) ? `${season.episodeCount} ${season.episodeCount === 1 ? 'episode' : 'episodes'}` : 'Episode count unavailable';
    return `<li><div class="season-heading"><div><h4>${escapeHTML(season.name || (season.number === 0 ? 'Specials' : 'Season ' + season.number))}</h4><p>${escapeHTML(year)} · ${episodes}</p></div><div class="season-actions">${watchedEye(seasonWatchCount(entry, season))}${season.url ? `<a href="${escapeHTML(season.url)}" class="season-link" target="_blank" rel="noopener noreferrer" aria-label="${escapeHTML(season.name)} on TMDB">TMDB ↗</a>` : ''}</div></div>${season.overview ? `<details class="season-description"><summary>Season synopsis</summary><p>${escapeHTML(season.overview)}</p></details>` : ''}</li>`;
  }).join('')}</ol>` : '<p class="seasons-unavailable">Season information is not available yet.</p>'}</section>`;
}
function openDetail(id) {
  const entry = state.entries.find(entry => entry.id === id);
  if (!entry) return;
  const history = [...state.entries.filter(other => other.showId === entry.showId)].sort((a,b) => b.watched.localeCompare(a.watched));
  const sourceLinks = [entry.url ? `<a class="detail-link" href="${escapeHTML(entry.url)}" target="_blank" rel="noopener noreferrer">TMDB ↗</a>` : '', entry.letterboxd ? `<a class="detail-link" href="${escapeHTML(entry.letterboxd)}" target="_blank" rel="noopener noreferrer">Letterboxd ↗</a>` : ''].join('');
  $('#detail-content').innerHTML = `<div class="detail-layout"><div class="detail-poster">${posterHTML(entry)}</div><div class="detail-copy"><span class="detail-year">${[entry.year,...(entry.genres || [])].filter(Boolean).map(escapeHTML).join(' · ')}</span><h2>${escapeHTML(entry.title)}</h2><p class="detail-watch">${seasonLabel(entry)} · ${entry.status === 'unfinished' ? 'Unfinished' : 'Watched'}${entry.watch === 'rewatch' ? ' · ↻ Rewatch' : ''}<br>Logged ${escapeHTML(watchLabel(entry))}</p><div class="entry-tags">${tagsHTML(entry)}</div>${entry.notes ? `<p class="detail-note">${escapeHTML(entry.notes)}</p>` : ''}<div class="other-viewings"><h3>Viewing history</h3>${history.map(other => `<p>${escapeHTML(watchLabel(other))} · ${seasonLabel(other)}${other.watch === 'rewatch' ? ' · ↻ Rewatch' : ''}${other.status === 'unfinished' ? ' · Unfinished' : ''} ${editLink(other)}</p>`).join('')}</div><p class="detail-summary">${escapeHTML(entry.summary || '')}</p><div class="source-links">${sourceLinks}</div>${entry.url ? '<p class="detail-credit">Summary &amp; poster via TMDB.</p>' : ''}</div></div>${seasonsHTML(entry)}`;
  $('#detail').showModal();
}
$('#entries').addEventListener('click',event => {
  const tag = event.target.closest('[data-tag]');
  if (tag) { toggleTag(tag.dataset.tag); return; }
  const button = event.target.closest('[data-id]');
  if (button) openDetail(button.dataset.id);
});
$('#tag-filters').addEventListener('click',event => {
  const tag = event.target.closest('[data-tag]');
  if (tag) toggleTag(tag.dataset.tag);
  if (event.target.closest('[data-clear-tags]')) { state.tags.clear(); render(); }
});
$('#detail-content').addEventListener('click',event => { const tag = event.target.closest('[data-tag]'); if (tag) { $('#detail').close(); toggleTag(tag.dataset.tag); } });
$('#search').addEventListener('input',render);
['year','status','watch','sort'].forEach(id => $(`#${id}`).addEventListener('change',render));
document.querySelectorAll('[data-section]').forEach(button => button.addEventListener('click',() => setSection(button.dataset.section)));
document.querySelectorAll('[data-view]').forEach(button => button.addEventListener('click',() => { state.view = button.dataset.view; state.views[state.mode] = state.view; render(); }));
$('#reset').addEventListener('click',() => { $('#search').value = ''; ['year','status','watch'].forEach(key => $(`#${key}`).value = 'all'); state.tags.clear(); render(); });
$('.close-dialog').addEventListener('click',() => $('#detail').close());
$('#detail').addEventListener('click',event => { if (event.target === $('#detail')) { const r = $('#detail').getBoundingClientRect(); if (event.clientX < r.left || event.clientX > r.right || event.clientY < r.top || event.clientY > r.bottom) $('#detail').close(); } });
async function init() {
  try {
    const embedded = $('#diary-data');
    let diary;
    if (embedded) {
      diary = JSON.parse(embedded.textContent);
    } else {
      const response = await fetch('data/diary.json', {cache:'no-store'});
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      diary = await response.json();
    }
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
    if (params.get('section') === 'watched') state.mode = 'watched';
    const layout = {cards:'large',grid:'large',diary:'list'}[params.get('view')] || params.get('view');
    state.view = ['large','small','list'].includes(layout) ? layout : state.views[state.mode];
    if (state.mode === 'watched' && state.view === 'list') state.view = 'large';
    state.views[state.mode] = state.view;
    const knownTags = new Set(state.entries.flatMap(entry => entry.tags));
    state.tags = new Set(params.getAll('tag').filter(tag => knownTags.has(tag)));
    render();
    $('#load-error').hidden = true;
  } catch (error) { $('#load-error').hidden = false; console.error('Unable to load viewing diary:',error); }
}
init();
