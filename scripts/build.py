"""Build the static diary from readable yearly Markdown tables. Python 3, no packages."""
import csv
import hashlib
import json
import re
import shutil
from tmdb import parse_reference
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
COLUMNS = ['Month', 'Series', 'Seasons', 'Watch', 'Status', 'Tags', 'Notes']
MONTHS = ['jan', 'feb', 'mar', 'apr', 'may', 'jun', 'jul', 'aug', 'sep', 'oct', 'nov', 'dec']


def parse_seasons(text):
    if text.lower() == 'all':
        return []  # Deliberately don't invent how many seasons existed at the time.
    seasons = []
    for part in text.split(','):
        match = re.fullmatch(r'[sS]?(\d+)(?:\s*[-–]\s*[sS]?(\d+))?', part.strip())
        if not match:
            raise ValueError('Seasons must be numbers, ranges (1-3), or all')
        first, last = int(match[1]), int(match[2] or match[1])
        if not 1 <= first <= last <= 1000:
            raise ValueError('Invalid season range')
        seasons.extend(range(first, last + 1))
    if len(set(seasons)) != len(seasons):
        raise ValueError('Repeated season in a single viewing')
    return sorted(seasons)


def table_rows(path):
    header = False
    for number, line in enumerate(path.read_text().splitlines(), 1):
        if not line.strip().startswith('|'):
            continue
        cells = [cell.strip().replace('\\|', '|') for cell in re.split(r'(?<!\\)\|', line.strip().strip('|'))]
        if all(re.fullmatch(r':?-+:?', cell) for cell in cells):
            continue
        if not header:
            if cells != COLUMNS:
                raise ValueError(f'{path.name}:{number}: expected columns {COLUMNS}')
            header = True
            continue
        if len(cells) != len(COLUMNS):
            raise ValueError(f'{path.name}:{number}: expected {len(COLUMNS)} columns, got {len(cells)}')
        yield number, cells
    if not header:
        raise ValueError(f'{path.name}: missing diary table')


def parse_year(path, catalogue, tmdb_cache=None):
    year = path.stem
    entries = []
    for number, cells in table_rows(path):
        try:
            if len(cells) != len(COLUMNS):
                raise ValueError(f'Expected {len(COLUMNS)} columns, got {len(cells)}')
            month, title, seasons, watch, status, tags, notes = cells
            if not title:
                raise ValueError('Series title is required')
            if month.strip().lower() in ('', '-', '?', 'unknown'):
                month_number = None
            elif month.lower()[:3] in MONTHS:
                month_number = MONTHS.index(month.lower()[:3]) + 1
            elif month.isdigit() and 1 <= int(month) <= 12:
                month_number = int(month)
            else:
                raise ValueError(f'Invalid month: {month}')
            watch = watch.lower() or 'watch'
            status = status.lower() or 'watched'
            if watch not in ('watch', 'rewatch'):
                raise ValueError('Watch must be watch or rewatch')
            if status not in ('watched', 'unfinished'):
                raise ValueError('Status must be watched or unfinished')
            reference = parse_reference(title)
            if reference:
                show = (tmdb_cache or {}).get(reference)
                if show is None:
                    raise ValueError(f'TMDB {reference} is not cached. Run python3 scripts/import_tmdb.py first.')
                title = show['title']
            else:
                show = catalogue.get(title.casefold(), {})
            title = show.get('title', title)
            is_movie = show.get('mediaType') == 'movie'
            if is_movie and seasons:
                raise ValueError('Movie links do not have seasons; leave the Seasons cell blank')
            season_numbers = [] if is_movie else parse_seasons(seasons)
            tag_list = list(dict.fromkeys(t.strip() for t in tags.split(',') if t.strip()))
            show_id = show.get('id') or title.casefold()
            entries.append(dict(show, id=f'{year}-{number}', showId=show_id, title=title,
                                watched=f'{year}-{month_number:02}' if month_number else year,
                                seasons=season_numbers, allSeasons=seasons.lower() == 'all',
                                watch=watch, status=status, tags=tag_list, notes=notes,
                                editUrl=f'https://github.com/shadrunov/letterboxd-series/edit/main/diary/{year}.md#L{number}'))
        except ValueError as error:
            raise ValueError(f'{path.name}:{number}: {error}') from error
    return entries


def load_diary(root=ROOT):
    cache_path = root / '.cache/tmdb/catalogue.json'
    tmdb_cache = json.loads(cache_path.read_text()) if cache_path.exists() else {}
    catalogue = {}
    registry = root / 'data/shows.csv'
    if registry.exists():
        with registry.open(newline='') as file:
            for row in csv.DictReader(file):
                key = row['Series'].casefold()
                if key in catalogue:
                    raise ValueError(f'Duplicate catalogue title: {row["Series"]}')
                reference = parse_reference(row.get('TMDB', ''))
                if not reference:
                    continue
                if reference not in tmdb_cache:
                    raise ValueError(f'TMDB {reference} is not cached. Run python3 scripts/import_tmdb.py first.')
                show = dict(tmdb_cache[reference])
                link = row.get('Letterboxd', '').strip()
                if link:
                    if not re.fullmatch(r'https://letterboxd\.com/film/[^/?#]+/', link):
                        raise ValueError(f'Invalid Letterboxd page: {link}')
                    show['letterboxd'] = link
                catalogue[key] = show
    files = sorted((root / 'diary').glob('[0-9][0-9][0-9][0-9].md'), reverse=True)
    if not files:
        raise ValueError('No yearly diary files found')
    # Registry links also apply to entries using the TMDB URL directly.
    for show in catalogue.values():
        if show.get('letterboxd'):
            tmdb_cache[show['id'].removeprefix('tmdb:')] = show
    entries = [entry for path in files for entry in parse_year(path, catalogue, tmdb_cache)]
    # Link earlier plain-title records to a later TMDB reference when unambiguous.
    by_title = {}
    for entry in entries:
        if entry.get('source') == 'TMDB':
            by_title.setdefault(entry['title'].casefold(), set()).add(entry['showId'])
    for entry in entries:
        matches = by_title.get(entry['title'].casefold(), set())
        if entry.get('source') != 'TMDB' and len(matches) == 1:
            entry['showId'] = next(iter(matches))
    return dict(years=[p.stem for p in files], entries=entries)


def render_index(source, diary, script, stylesheet):
    """Publish matching assets and data together, without stale browser file mixes."""
    marker = '<!-- DIARY_DATA -->'
    if source.count(marker) != 1:
        raise ValueError('index.html must contain exactly one diary data marker')
    payload = json.dumps(diary, ensure_ascii=False).replace('&', '\\u0026').replace('<', '\\u003c').replace('>', '\\u003e')
    source = source.replace(marker, f'<script id="diary-data" type="application/json">{payload}</script>')
    for path, content in [('app.js', script), ('style.css', stylesheet)]:
        version = hashlib.sha256(content).hexdigest()[:16]
        source = source.replace(f'"{path}"', f'"{path}?v={version}"')
    return source


def build():
    diary = load_diary()
    out = ROOT / '_site'
    if out.exists():
        shutil.rmtree(out)
    out.mkdir()
    for filename in ('style.css', 'app.js'):
        shutil.copy2(ROOT / filename, out / filename)
    (out / 'index.html').write_text(render_index((ROOT / 'index.html').read_text(), diary, (ROOT / 'app.js').read_bytes(), (ROOT / 'style.css').read_bytes()))
    shutil.copytree(ROOT / 'assets', out / 'assets', dirs_exist_ok=True)
    shutil.copytree(ROOT / 'diary', out / 'diary', dirs_exist_ok=True)
    for entry in diary['entries']:
        if entry.get('source') == 'TMDB' and entry.get('poster'):
            source = ROOT / '.cache/tmdb/posters' / Path(entry['poster']).name
            if not source.is_file():
                raise ValueError('Missing cached TMDB poster. Run python3 scripts/import_tmdb.py first.')
            destination = out / entry['poster']
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, destination)
    (out / 'data').mkdir(exist_ok=True)
    (out / 'data/diary.json').write_text(json.dumps(diary, ensure_ascii=False, indent=2) + '\n')
    print(f'Built {len(diary["entries"])} viewings across {len(diary["years"])} yearly tables → _site/')


if __name__ == '__main__':
    build()
