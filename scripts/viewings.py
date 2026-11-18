"""Classify repeated seasons after loading every year's diary records."""


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


def classify_rewatches(entries):
    completed = {}
    classified = {}
    for entry in sorted(entries, key=lambda item: item['watchDate']):
        seasons = seasons_for_viewing(entry)
        previous = completed.setdefault(entry['showId'], set())
        repeated = seasons & previous
        records = [entry]
        if entry['watch'] == 'watch' and repeated:
            new_seasons = seasons - repeated
            if new_seasons:
                records = [
                    dict(entry, id=entry['id'] + '-watch', sourceId=entry['id'],
                         seasons=sorted(new_seasons), allSeasons=False),
                    dict(entry, id=entry['id'] + '-rewatch', sourceId=entry['id'],
                         seasons=sorted(repeated), allSeasons=False, watch='rewatch'),
                ]
            else:
                records = [dict(entry, watch='rewatch')]
        classified[entry['id']] = records
        if entry['status'] == 'watched':
            previous.update(seasons)
    return [record for entry in entries for record in classified[entry['id']]]
