"""Fetch uncached TMDB titles and posters before building."""
import argparse
import unicodedata
import getpass
import json
import os
import re
import sys
import time
import tempfile
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from urllib.parse import urlencode, urlsplit

from build import ROOT
from diary import diary_files, read_document, fill_names
from tmdb import parse_reference, reference_url

CACHE = ROOT / '.cache/tmdb'


def discover_references(root=ROOT):
    return sorted({parse_reference(row['url']) for path in diary_files(root) for _, row, _ in read_document(path)[1]})


def read_cache(cache):
    path = cache / 'catalogue.json'
    return json.loads(path.read_text()) if path.exists() else {}


def request_bytes(url, token=None):
    headers = {'Accept': 'application/json' if token else 'image/*', 'User-Agent': 'SeriesDiary/1.0'}
    if token:
        token = token.strip()
        if token.lower().startswith('bearer '):
            token = token[7:].strip()
        if re.fullmatch(r'[0-9a-fA-F]{32}', token):
            # v3 API keys use a query parameter; never log this URL.
            url += ('&' if '?' in url else '?') + urlencode({'api_key': token})
        else:
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
                raise ValueError('TMDB title not found. Check the link in your diary YAML.') from None
            raise ValueError(f'TMDB request failed (HTTP {error.code})') from None
        except URLError:
            if attempt < 2:
                time.sleep(attempt + 1)
                continue
            raise ValueError('Could not reach TMDB. Try the workflow again later.') from None


def find_letterboxd(reference, title, year):
    """Return a canonical page only when it identifies the same TMDB entity."""
    kind, number = reference.split('/')
    slug = re.sub(r'[^a-z0-9]+', '-', unicodedata.normalize('NFKD', title).encode('ascii', 'ignore').decode().lower()).strip('-')
    candidates = [f'https://letterboxd.com/tmdb/{number}/'] if kind == 'movie' else [f'https://letterboxd.com/film/{slug}/', f'https://letterboxd.com/film/{slug}-{year}/']
    for url in candidates:
        try:
            request = Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urlopen(request, timeout=10) as response:
                canonical = response.url
                html = response.read(2 * 1024 * 1024).decode('utf-8', errors='replace')
            if not re.fullmatch(r'https://letterboxd\.com/film/[^/?#]+/', canonical):
                continue
            ids = set(re.findall(r'themoviedb\.org/(tv|movie)/(\d+)', html))
            if ids == {(kind, number)}:
                return canonical
        except (OSError, ValueError):
            continue
    return ''


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
    year = int(date[:4]) if re.match(r'^\d{4}-', date) else None
    return dict(metadataVersion=3, letterboxd=find_letterboxd(reference, title, year), id=f'tmdb:{reference}', title=title, year=int(date[:4]) if re.match(r'^\d{4}-', date) else None,
                mediaType=kind, poster=poster, url=reference_url(reference), source='TMDB',
                genres=[genre['name'] for genre in data.get('genres', [])], summary=data.get('overview') or '',
                seasonDetails=[dict(number=season['season_number'], name=season.get('name') or f'Season {season["season_number"]}',
                                    airDate=season.get('air_date'), episodeCount=season.get('episode_count'),
                                    overview=season.get('overview') or '',
                                    url=reference_url(reference) + f'/season/{season["season_number"]}')
                               for season in data.get('seasons', []) if isinstance(season.get('season_number'), int)] if kind == 'tv' else [],
                numberOfSeasons=data.get('number_of_seasons') if kind == 'tv' else None,
                numberOfEpisodes=data.get('number_of_episodes') if kind == 'tv' else None,
                showStatus=data.get('status') or '',
                imageSource=image_url, fetchedAt=time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()))


def import_titles(root=ROOT, cache=CACHE, token=None, refresh=False, write_names=False):
    refs = discover_references(root)
    cached = read_cache(cache)
    missing = [ref for ref in refs if refresh or ref not in cached or cached[ref].get('metadataVersion') != 3 or
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
    if write_names:
        print(f'Updated {fill_names(root, cached)} YAML name fields.')
    print(f'TMDB: {len(refs)} titles referenced, {len(missing)} fetched, {len(refs) - len(missing)} cached.')
    return cached


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--write-names', action='store_true', help='Fill TMDB names in the yearly YAML files')
    parser.add_argument('--refresh', action='store_true', help='Fetch referenced titles again, including their posters')
    parser.add_argument('--check-url', help='Fetch one TMDB link into temporary storage to verify API access, without adding a viewing')
    args = parser.parse_args()
    token = os.environ.get('TMDB_READ_ACCESS_TOKEN')
    if not token and sys.stdin.isatty():
        refs = [args.check_url] if args.check_url else discover_references()
        cached = read_cache(CACHE)
        if refs and (args.check_url or args.refresh or any(ref not in cached or cached[ref].get('metadataVersion') != 3 or (cached[ref].get('poster') and not (CACHE / 'posters' / Path(cached[ref]['poster']).name).is_file()) for ref in refs)):
            token = getpass.getpass('TMDB API Read Access Token (hidden): ')
    try:
        if args.check_url:
            reference = parse_reference(args.check_url)
            if not reference:
                raise ValueError('--check-url needs a TMDB TV or movie link')
            if not token:
                raise ValueError('TMDB verification needs TMDB_READ_ACCESS_TOKEN')
            with tempfile.TemporaryDirectory() as directory:
                result = fetch_metadata(reference, token, Path(directory))
                print(f'Verified TMDB {reference}: {result["title"]}; ' + ('poster downloaded.' if result['poster'] else 'no poster available.'))
        else:
            import_titles(token=token, refresh=args.refresh, write_names=args.write_names)
    except (ValueError, OSError) as error:
        print(f'Import failed: {error}', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
