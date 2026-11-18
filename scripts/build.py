"""Build the static diary from readable yearly YAML files."""
import csv
import hashlib
import json
import re
import shutil
from tmdb import parse_reference
from viewings import classify_rewatches
from continuations import continuation_rules, combine_continuations
from diary import diary_files, read_document, parse_seasons
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
def parse_year(path, tmdb_cache):
    entries = []
    _, rows = read_document(path)
    for number, row, _ in rows:
        reference = parse_reference(row['url'])
        show = tmdb_cache.get(reference)
        if show is None:
            raise ValueError(f'{path.name}:{number}: TMDB {reference} is not cached. Run python3 scripts/import_tmdb.py first.')
        value = row.get('seasons', [])
        entries.append(dict(show, id=f'{path.stem}-{number}', showId=show['id'], title=show['title'],
                            watched=row['date'][:7], watchDate=row['date'], seasons=parse_seasons(value),
                            allSeasons=str(value).lower() == 'all', watch='rewatch' if row.get('rewatch') else 'watch',
                            status=row.get('status', 'watched'), tags=list(dict.fromkeys(row.get('tags', []))), notes=row.get('notes', ''),
                            editUrl=f'https://github.com/shadrunov/letterboxd-series/edit/main/diary/{path.name}#L{number}'))
    return entries


def load_diary(root=ROOT):
    cache_path = root / '.cache/tmdb/catalogue.json'
    tmdb_cache = json.loads(cache_path.read_text()) if cache_path.exists() else {}
    tmdb_cache = combine_continuations(tmdb_cache, continuation_rules(root))
    registry = root / 'data/shows.csv'
    if registry.exists():
        with registry.open(newline='') as file:
            for row in csv.DictReader(file):
                reference = parse_reference(row.get('TMDB', ''))
                link = row.get('Letterboxd', '').strip()
                if reference in tmdb_cache and link:
                    if not re.fullmatch(r'https://letterboxd\.com/film/[^/?#]+/', link):
                        raise ValueError(f'Invalid Letterboxd page: {link}')
                    tmdb_cache[reference]['letterboxd'] = link
    files = diary_files(root)
    if not files:
        raise ValueError('No yearly YAML diary files found')
    entries = [entry for path in files for entry in parse_year(path, tmdb_cache)]
    return dict(years=[p.stem for p in files], entries=classify_rewatches(entries))


def render_index(source, diary, script, stylesheet, favicon=None):
    """Publish matching assets and data together, without stale browser file mixes."""
    marker = '<!-- DIARY_DATA -->'
    if source.count(marker) != 1:
        raise ValueError('index.html must contain exactly one diary data marker')
    payload = json.dumps(diary, ensure_ascii=False).replace('&', '\\u0026').replace('<', '\\u003c').replace('>', '\\u003e')
    source = source.replace(marker, f'<script id="diary-data" type="application/json">{payload}</script>')
    assets = [('app.js', script), ('style.css', stylesheet)]
    if favicon is not None:
        assets.append(('assets/favicon.svg', favicon))
    for path, content in assets:
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
    (out / 'index.html').write_text(render_index((ROOT / 'index.html').read_text(), diary, (ROOT / 'app.js').read_bytes(), (ROOT / 'style.css').read_bytes(), (ROOT / 'assets/favicon.svg').read_bytes()))
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
    print(f'Built {len(diary["entries"])} viewings across {len(diary["years"])} yearly YAML files → _site/')


if __name__ == '__main__':
    build()
