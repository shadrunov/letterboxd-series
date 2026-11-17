"""Resolve catalogue titles to TMDB, using IMDb IDs for legacy TVmaze entries."""
import csv
import json
import os
from urllib.parse import urlencode
from urllib.request import urlopen
from build import ROOT
from import_tmdb import CACHE, fetch_metadata, read_cache, request_bytes
from tmdb import parse_reference


def main():
    token = os.environ.get('TMDB_READ_ACCESS_TOKEN')
    if not token:
        raise ValueError('TMDB_READ_ACCESS_TOKEN is required')
    cached = read_cache(CACHE)
    resolved = []
    with (ROOT / 'data/shows.csv').open(newline='') as file:
        for row in csv.DictReader(file):
            title = row['Series']
            reference = parse_reference(row.get('TMDB', ''))
            imdb = row.get('IMDb', '')
            if not reference:
                if row.get('URL', '').startswith('https://www.tvmaze.com/shows/'):
                    number = row['URL'].split('/')[4]
                    with urlopen(f'https://api.tvmaze.com/shows/{number}', timeout=30) as response:
                        imdb = json.load(response).get('externals', {}).get('imdb')
                if imdb:
                    data = json.loads(request_bytes(f'https://api.themoviedb.org/3/find/{imdb}?external_source=imdb_id', token))
                    candidates = data.get('tv_results', [])
                else:
                    query = urlencode({'query': title, 'first_air_date_year': row.get('Year', ''), 'language': 'en-US'})
                    candidates = json.loads(request_bytes(f'https://api.themoviedb.org/3/search/tv?{query}', token)).get('results', [])
                    candidates = [c for c in candidates if c['name'].casefold() == title.casefold()]
                if len(candidates) != 1:
                    raise ValueError(f'{title}: expected one unambiguous TMDB match, found {len(candidates)}')
                reference = f'tv/{candidates[0]["id"]}'
            cached[reference] = fetch_metadata(reference, token, CACHE)
            resolved.append({'Series': title, 'TMDB': cached[reference]['url'], 'IMDb': imdb or '', 'Letterboxd': ''})
            print(f'{title} → {reference}: {cached[reference]["title"]} ({cached[reference]["year"]})')
    CACHE.mkdir(parents=True, exist_ok=True)
    (CACHE / 'catalogue.json').write_text(json.dumps(cached, ensure_ascii=False, indent=2) + '\n')
    with (CACHE / 'resolved.csv').open('w', newline='') as file:
        writer = csv.DictWriter(file, fieldnames=['Series', 'TMDB', 'IMDb', 'Letterboxd'], lineterminator='\n')
        writer.writeheader()
        writer.writerows(resolved)


if __name__ == '__main__':
    main()
