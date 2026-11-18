"""Group season logs into viewing rounds in chronological YAML order."""


def seasons_for_viewing(entry):
    if entry.get('mediaType') == 'movie':
        return {0}
    if not entry['allSeasons']:
        return set(entry['seasons'])
    date = entry['watchDate']
    return {
        season['number']
        for season in entry.get('seasonDetails', [])
        if season['number'] > 0 and season.get('airDate')
        and season['airDate'][:len(date)] <= date
    }


def group_viewings(entries):
    rounds = {}
    assigned = {}
    # Python's stable sort preserves top-to-bottom YAML order for equal dates.
    for entry in sorted(entries, key=lambda item: item['watchDate']):
        seasons = seasons_for_viewing(entry)
        show_rounds = rounds.setdefault(entry['showId'], [])
        current = show_rounds[-1] if show_rounds else None
        if current is None or entry['watch'] == 'rewatch' or seasons & current['completed']:
            current = {
                'number': len(show_rounds) + 1,
                'watch': 'rewatch' if show_rounds or entry['watch'] == 'rewatch' else 'watch',
                'seasons': set(),
                'completed': set(),
                'entries': [],
            }
            show_rounds.append(current)
        current['entries'].append(entry)
        current['seasons'].update(seasons)
        if entry['status'] == 'watched':
            current['completed'].update(seasons)
        assigned[entry['id']] = current

    result = []
    for entry in entries:
        viewing = assigned[entry['id']]
        complete = viewing['seasons'] <= viewing['completed']
        if not viewing['seasons']:
            complete = all(row['status'] == 'watched' for row in viewing['entries'])
        result.append(dict(
            entry,
            viewingId=f'{entry["showId"]}:viewing:{viewing["number"]}',
            viewingNumber=viewing['number'],
            viewingStatus='watched' if complete else 'unfinished',
            watch=viewing['watch'],
        ))
    return result
