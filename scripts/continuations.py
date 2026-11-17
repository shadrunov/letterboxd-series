"""Join explicitly verified, separately catalogued TMDB season continuations."""
from copy import deepcopy
import yaml
from tmdb import parse_reference


def continuation_rules(root):
    path = root / 'data/season-continuations.yaml'
    if not path.exists():
        return []
    rules = yaml.safe_load(path.read_text()) or []
    seen = set()
    for rule in rules:
        if set(rule) != {'series', 'continuation', 'season_offset'}:
            raise ValueError('Invalid season continuation fields')
        for key in ('series', 'continuation'):
            rule[key] = parse_reference(rule[key])
            if not rule[key] or not rule[key].startswith('tv/'):
                raise ValueError('Season continuations require TMDB TV URLs')
        if rule['series'] == rule['continuation'] or rule['continuation'] in seen:
            raise ValueError('Duplicate or self-referencing season continuation')
        if type(rule['season_offset']) is not int or rule['season_offset'] < 1:
            raise ValueError('Season offset must be a positive integer')
        seen.add(rule['continuation'])
    return rules


def combine_continuations(catalogue, rules):
    result = deepcopy(catalogue)
    for rule in rules:
        if rule['series'] not in result:
            continue
        base = result[rule['series']]
        extra = catalogue.get(rule['continuation'])
        if extra is None:
            raise ValueError('Missing TMDB continuation metadata; run the importer first')
        seasons = {season['number']: season for season in base.get('seasonDetails', [])}
        appended = False
        for original in extra.get('seasonDetails', []):
            if original['number'] <= 0:
                continue  # Continuation specials are not regular series seasons.
            number = original['number'] + rule['season_offset']
            # Prefer a native season if TMDB later reunites its records.
            if number not in seasons:
                seasons[number] = dict(original, number=number, name=f'Season {number} · {extra["title"]}')
                appended = True
        base['seasonDetails'] = sorted(seasons.values(), key=lambda season: season['number'])
        base['numberOfSeasons'] = len([number for number in seasons if number > 0])
        counts = [season.get('episodeCount') for number, season in seasons.items() if number > 0]
        base['numberOfEpisodes'] = sum(counts) if counts and all(type(count) is int for count in counts) else None
        if appended:
            base['showStatus'] = extra.get('showStatus', '')
    return result
