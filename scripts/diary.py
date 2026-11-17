"""Read and enrich human-edited yearly YAML diaries without reformatting them."""
import datetime
import json
import re
from pathlib import Path
import yaml
from tmdb import parse_reference

ROOT = Path(__file__).resolve().parent.parent
FIELDS = {'url', 'name', 'date', 'seasons', 'tags', 'rewatch', 'status', 'notes'}


class DiaryLoader(yaml.SafeLoader):
    def construct_mapping(self, node, deep=False):
        keys = set()
        for key_node, _ in node.value:
            key = self.construct_object(key_node, deep=deep)
            if not isinstance(key, str):
                raise ValueError(f'Line {key_node.start_mark.line + 1}: keys must be text')
            if key in keys:
                raise ValueError(f'Line {key_node.start_mark.line + 1}: duplicate field {key}')
            keys.add(key)
        return super().construct_mapping(node, deep=deep)


def diary_files(root=ROOT):
    return sorted((root / 'diary').glob('[0-9][0-9][0-9][0-9].yaml'), reverse=True)


def parse_seasons(value):
    if isinstance(value, list):
        if not value:
            return []
        if any(type(season) is not int for season in value):
            raise ValueError('seasons must contain integers')
        text = ','.join(map(str, value))
    elif type(value) is int or isinstance(value, str):
        text = str(value)
    else:
        raise ValueError('seasons must be a list, a number, a range, or all')
    if text.strip().lower() == 'all':
        return []
    seasons = []
    for part in text.split(','):
        match = re.fullmatch(r'[sS]?(\d+)(?:\s*[-–]\s*[sS]?(\d+))?', part.strip())
        if not match:
            raise ValueError('seasons must be numbers, ranges (1-3), or all')
        first, last = int(match[1]), int(match[2] or match[1])
        if not 1 <= first <= last <= 1000:
            raise ValueError('Invalid season range')
        seasons.extend(range(first, last + 1))
    if len(set(seasons)) != len(seasons):
        raise ValueError('Repeated season in a single viewing')
    return sorted(seasons)


def date_text(value, year):
    if type(value) is int or isinstance(value, datetime.date):
        value = str(value)
    if not isinstance(value, str) or not re.fullmatch(r'\d{4}(?:-(?:0[1-9]|1[0-2])(?:-\d{2})?)?', value):
        raise ValueError('date must be YYYY-MM, YYYY-MM-DD, or YYYY')
    if len(value) == 10:
        try:
            datetime.date.fromisoformat(value)
        except ValueError:
            raise ValueError('date is not a valid calendar date') from None
    if value[:4] != year:
        raise ValueError(f'date must belong to {year}')
    return value


def read_document(path, text=None):
    text = path.read_text() if text is None else text
    loader = DiaryLoader(text)
    try:
        node = loader.get_single_node()
        data = loader.construct_document(node) if node else []
    except (yaml.YAMLError, ValueError) as error:
        raise ValueError(f'{path.name}: {error}') from error
    finally:
        loader.dispose()
    if data is None:
        data = []
    if not isinstance(data, list):
        raise ValueError(f'{path.name}: diary must be a YAML list')
    rows = []
    seen = set()
    for row, item in zip(data, node.value if node else []):
        number = item.start_mark.line + 1
        try:
            if not isinstance(row, dict) or item.flow_style:
                raise ValueError('use a block entry starting with - url:')
            if item.start_mark.index in seen:
                raise ValueError('repeat viewings need separate entries, not a YAML alias')
            seen.add(item.start_mark.index)
            unknown = row.keys() - FIELDS
            if unknown:
                raise ValueError(f'Unknown fields: {", ".join(sorted(unknown))}')
            if not isinstance(row.get('url'), str) or '\n' in row['url'] or not parse_reference(row['url']):
                raise ValueError('url must be a TMDB TV or movie URL')
            row['date'] = date_text(row.get('date'), path.stem)
            if row.get('name') is not None and (not isinstance(row['name'], str) or '\n' in row['name']):
                raise ValueError('name must be single-line text')
            if type(row.get('rewatch', False)) is not bool:
                raise ValueError('rewatch must be true or false')
            if row.get('status', 'watched') not in ('watched', 'unfinished'):
                raise ValueError('status must be watched or unfinished')
            tags = row.get('tags', [])
            if not isinstance(tags, list) or any(not isinstance(tag, str) for tag in tags):
                raise ValueError('tags must be a list of text labels')
            if not isinstance(row.get('notes', ''), str):
                raise ValueError('notes must be text')
            seasons = row.get('seasons', [])
            numbers = parse_seasons(seasons)
            if parse_reference(row['url']).startswith('tv/') and not numbers and str(seasons).lower() != 'all':
                raise ValueError('TV entries need seasons, for example [1, 2] or all')
            if parse_reference(row['url']).startswith('movie/') and seasons not in ([], None):
                raise ValueError('Movies do not have seasons; omit seasons or use []')
            rows.append((number, row, item))
        except ValueError as error:
            raise ValueError(f'{path.name}:{number}: {error}') from error
    return text, rows


def fill_names(root, catalogue):
    """Only insert or replace name values; keep dates, comments, tags, and spacing."""
    changed = 0
    for path in diary_files(root):
        text, rows = read_document(path)
        edits = []
        for _, row, node in rows:
            reference = parse_reference(row['url'])
            name = catalogue[reference]['title']
            if row.get('name') == name:
                continue
            scalar = json.dumps(name, ensure_ascii=False)
            pairs = {key.value: value for key, value in node.value}
            if 'name' in pairs:
                value = pairs['name']
                prefix = ' ' if text[value.start_mark.index - 1:value.start_mark.index] == ':' else ''
                edits.append((value.start_mark.index, value.end_mark.index, prefix + scalar))
            else:
                end = text.find('\n', pairs['url'].end_mark.index)
                prefix = '' if end >= 0 else '\n'
                position = end + 1 if end >= 0 else len(text)
                edits.append((position, position, prefix + ' ' * node.start_mark.column + f'name: {scalar}\n'))
        for start, end, replacement in sorted(edits, reverse=True):
            text = text[:start] + replacement + text[end:]
        if edits:
            path.write_text(text)
            changed += len(edits)
    return changed
