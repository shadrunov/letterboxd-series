"""Fetch uncached TMDB titles and posters before building. No third-party packages."""
import argparse
import getpass
import json
import os
import re
import sys
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from build import ROOT, table_rows
from tmdb import parse_reference, reference_url

CACHE = ROOT / '.cache/tmdb'


def discover_references(root=ROOT):
    refs = set()
    for path in (root / 'diary').glob('[0-9][0-9][0-9][0-9].md'):
        for number, cells in table_rows(path):
            try:
                ref = parse_reference(cells[1])
            except ValueError as error:
                raise ValueError(f'{path.name}:{number}: {error}') from error
            if ref:
                refs.add(ref)
    return sorted(refs)


def read_cache(cache):
    path = cache / 'catalogue.json'
    return json.loads(path.read_text()) if path.exists() else {}


def request_bytes(url, token=None):
    headers = {'Accept': 'application/json' if token else 'image/*', 'User-Agent': 'SeriesDiary/1.0'}
    if token:
        headers['Authorization'] = f'Bearer {token}'
    for attempt in range(3):
        try:
            with urlopen(Request(url, headers=headers), timeout=30) as response:
                data = response.read(15 * 1024 * 1024 + 1)
                if len(data) > 15 * 1024 * 1024:
                    raise ValueError('TMDB response exceeded size limit')
                return data
        except HTTPError as error:
            if error.code == 429 or 500 <= error.code < 600:
                if attempt < 2:
                    time.sleep(attempt + 1)
                    continue
            if error.code in (401, 403):
                raise ValueError('TMDB authentication failed. Check TMDB_READ_ACCESS_TOKEN.') from None
            if error.code == 404:
                raise ValueError('TMDB title not found. Check the link in your diary table.') from None
            raise ValueError(f'TMDB request failed (HTTP {error.code})') from None
        except URLError:
            if attempt < 2:
                time.sleep(attempt + 1)
                continue
            raise ValueError('Could not reach TMDB. Try the workflow again later.') from None


def fetch_metadata(reference, token, cache):
    kind, number = reference.split('/')
    data = json.loads(request_bytes(f'https://api.themoviedb.org/3/{reference}?language=en-US', token))
    title = data.get('name' if kind == 'tv' else 'title')
    if not title or data.get('id') != int(number):
        raise ValueError('TMDB returned incomplete or mismatched title details')
    date = data.get('first_air_date' if kind == 'tv' else 'release_date') or ''
    image = data.get('poster_path')
    poster = ''
    image_url = ''
    if image:
        if not re.fullmatch(r'/[A-Za-z0-9_.-]+\.(jpg|png|webp)', image):
            raise ValueError('TMDB returned an invalid poster path')
        image_url = f'https://image.tmdb.org/t/p/w500{image}'
        filename = f'{kind}-{number}{Path(image).suffix}'
        (cache / 'posters').mkdir(parents=True, exist_ok=True)
        (cache / 'posters' / filename).write_bytes(request_bytes(image_url))
        poster = f'assets/posters/tmdb/{filename}'
    return dict(id=f'tmdb:{reference}', title=title, year=int(date[:4]) if re.match(r'^\d{4}-', date) else None,
                mediaType=kind, poster=poster, url=reference_url(reference), source='TMDB',
                genres=[genre['name'] for genre in data.get('genres', [])], summary=data.get('overview') or '',
                imageSource=image_url, fetchedAt=time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()))


def import_titles(root=ROOT, cache=CACHE, token=None, refresh=False):
    refs = discover_references(root)
    cached = read_cache(cache)
    missing = [ref for ref in refs if refresh or ref not in cached or
               (cached[ref].get('poster') and not (cache / 'posters' / Path(cached[ref]['poster']).name).is_file())]
    if missing and not token:
        raise ValueError('New TMDB links need a token. Add the Actions secret TMDB_READ_ACCESS_TOKEN, or run this script locally and enter your token at the hidden prompt.')
    for ref in missing:
        print(f'Fetching TMDB {ref}…')
        cached[ref] = fetch_metadata(ref, token, cache)
    if missing:
        cache.mkdir(parents=True, exist_ok=True)
        temporary = cache / 'catalogue.json.tmp'
        temporary.write_text(json.dumps(cached, indent=2, ensure_ascii=False) + '\n')
        temporary.replace(cache / 'catalogue.json')
    print(f'TMDB: {len(refs)} titles referenced, {len(missing)} fetched, {len(refs) - len(missing)} cached.')
    return cached


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--refresh', action='store_true', help='Fetch referenced titles again, including their posters')
    args = parser.parse_args()
    token = os.environ.get('TMDB_READ_ACCESS_TOKEN')
    if not token and sys.stdin.isatty():
        refs = discover_references()
        cached = read_cache(CACHE)
        if refs and (args.refresh or any(ref not in cached or (cached[ref].get('poster') and not (CACHE / 'posters' / Path(cached[ref]['poster']).name).is_file()) for ref in refs)):
            token = getpass.getpass('TMDB API Read Access Token (hidden): ')
    try:
        import_titles(token=token, refresh=args.refresh)
    except (ValueError, OSError) as error:
        print(f'Import failed: {error}', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
