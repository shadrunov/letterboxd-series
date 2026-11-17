"""Canonical TMDB references shared by the importer and diary builder."""
import re
from urllib.parse import urlsplit


def parse_reference(text):
    text = text.strip()
    link = re.fullmatch(r'\[[^\]]*\]\((https?://[^\s)]+)\)', text)
    if link:
        text = link[1]
    if not text.startswith(('https://', 'http://')):
        return None
    url = urlsplit(text)
    match = re.fullmatch(r'/(tv|movie)/([1-9]\d*)(?:-[^/]*)?/?', url.path)
    if url.hostname not in ('www.themoviedb.org', 'themoviedb.org') or not match:
        raise ValueError('Use a TMDB /tv/123 or /movie/123 link, or a plain series title')
    kind, number = match.groups()
    return f'{kind}/{number}'


def reference_url(reference):
    return f'https://www.themoviedb.org/{reference}'
