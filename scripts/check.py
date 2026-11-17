"""Check diary data and local assets without third-party dependencies."""
import json
import pathlib
import re

root = pathlib.Path(__file__).resolve().parent.parent
entries = json.loads((root / 'data/series.json').read_text())
ids = set()
assert entries, 'Diary is empty'
for entry in entries:
    assert entry['id'] not in ids, f"Duplicate ID: {entry['id']}"
    ids.add(entry['id'])
    assert re.fullmatch(r'\d{4}-(0[1-9]|1[0-2])', entry['watched']), entry
    assert entry['status'] in {'watched', 'unfinished'}, entry
    assert entry['title'] and isinstance(entry['year'], int), entry
    assert entry['seasons'] and all(isinstance(s, int) and s > 0 for s in entry['seasons']), entry
    assert len(entry['seasons']) == len(set(entry['seasons'])), entry
    assert entry['url'].startswith('https://www.tvmaze.com/shows/'), entry
    assert entry['poster'].startswith('assets/posters/'), entry
    assert (root / entry['poster']).is_file(), entry['poster']
for filename in ['index.html', 'style.css', 'app.js', 'assets/favicon.svg']:
    assert (root / filename).is_file(), filename
print(f"Validated {len(entries)} entries, {sum(len(e['seasons']) for e in entries)} logged seasons, and all local assets.")
