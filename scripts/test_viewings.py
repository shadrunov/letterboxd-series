"""Repeated seasons are classified across yearly YAML files before diary grouping."""
import json
import tempfile
import unittest
from pathlib import Path
from build import load_diary
from test_diary import SHOW, viewing, write_diary


class RewatchClassificationTest(unittest.TestCase):
    def load(self, records, metadata=None):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for year, rows in records.items():
                write_diary(root, rows, year)
            cache = root / '.cache/tmdb'
            cache.mkdir(parents=True)
            (cache / 'catalogue.json').write_text(json.dumps({'tv/125910': metadata or SHOW}))
            return load_diary(root)['entries']

    def test_repeat_season_is_separate_from_first_watch_across_years(self):
        entries = self.load({
            '2026': [viewing(date='2026-07', seasons=[3], tags=['w/ andrei'])],
            '2024': [viewing(date='2024-10', seasons=[3]), viewing(date='2024-09', seasons=[1, 2])],
        })
        self.assertEqual([(entry['watched'], entry['watch'], entry['seasons']) for entry in entries], [
            ('2026-07', 'rewatch', [3]), ('2024-10', 'watch', [3]), ('2024-09', 'watch', [1, 2]),
        ])
        self.assertEqual(entries[0]['tags'], ['w/ andrei'])

    def test_same_month_rows_extend_one_viewing_until_a_season_repeats(self):
        entries = self.load({'2026': [
            viewing(date='2026-11', seasons=[1], tags=['in dublin']),
            viewing(date='2026-11', seasons=[2, 3], tags=['queer']),
            viewing(date='2026-11', seasons=[1], tags=['second viewing']),
            viewing(date='2026-11', seasons=[2, 3], tags=['second viewing']),
        ]})
        self.assertEqual([entry['viewingNumber'] for entry in entries], [1, 1, 2, 2])
        self.assertEqual([entry['watch'] for entry in entries], ['watch', 'watch', 'rewatch', 'rewatch'])
        self.assertEqual(len({entry['viewingId'] for entry in entries}), 2)
        self.assertEqual(entries[0]['tags'], ['in dublin'])
        self.assertEqual(entries[1]['tags'], ['queer'])

    def test_mixed_new_and_repeated_seasons_start_one_new_viewing(self):
        entries = self.load({'2026': [
            viewing(date='2026-04-01', seasons=[1]),
            viewing(date='2026-04-20', seasons=[1, 2], notes='Together'),
        ]})
        self.assertEqual(len(entries), 2)
        self.assertEqual(entries[1]['viewingNumber'], 2)
        self.assertEqual(entries[1]['seasons'], [1, 2])
        self.assertEqual(entries[1]['watch'], 'rewatch')
        self.assertEqual(entries[1]['notes'], 'Together')

    def test_unfinished_first_attempt_does_not_make_completion_a_rewatch(self):
        entries = self.load({'2026': [
            viewing(date='2026-01', status='unfinished'),
            viewing(date='2026-02'),
            viewing(date='2026-03', status='unfinished'),
        ]})
        self.assertEqual([entry['watch'] for entry in entries], ['watch', 'watch', 'rewatch'])
        self.assertEqual([entry['viewingNumber'] for entry in entries], [1, 1, 2])
        self.assertEqual([entry['viewingStatus'] for entry in entries], ['watched', 'watched', 'unfinished'])

    def test_all_seasons_use_releases_at_the_recorded_date(self):
        metadata = dict(SHOW, seasonDetails=[
            {'number': 0, 'airDate': '2020-01-01'},
            {'number': 1, 'airDate': '2021-01-01'},
            {'number': 2, 'airDate': '2024-07-20'},
            {'number': 3, 'airDate': '2026-03-01'},
            {'number': 4, 'airDate': None},
        ])
        entries = self.load({
            '2024': [viewing(date='2024-07', seasons='all')],
            '2026': [viewing(date='2026-03-01', seasons='all')],
        }, metadata)
        self.assertEqual(len(entries), 2)
        self.assertEqual(entries[0]['watch'], 'rewatch')
        self.assertTrue(entries[0]['allSeasons'])
        self.assertEqual(entries[0]['viewingNumber'], 2)
        self.assertTrue(entries[1]['allSeasons'])

    def test_explicit_rewatch_is_preserved_without_an_earlier_record(self):
        entries = self.load({'2026': [viewing(rewatch=True)]})
        self.assertEqual(entries[0]['watch'], 'rewatch')

    def test_rewatch_round_continues_across_years(self):
        entries = self.load({
            '2024': [viewing(date='2024-10', seasons=[1, 2, 3])],
            '2025': [viewing(date='2025-11', seasons=[1])],
            '2026': [viewing(date='2026-02', seasons=[2, 3])],
        })
        self.assertEqual([entry['viewingNumber'] for entry in entries], [2, 2, 1])
        self.assertEqual(entries[0]['viewingId'], entries[1]['viewingId'])

    def test_repeated_movie_starts_another_viewing(self):
        from viewings import group_viewings
        records = [dict(id=str(number), showId='movie', mediaType='movie', watchDate=date, seasons=[], allSeasons=False, status='watched', watch='watch')
                   for number, date in enumerate(['2026-01', '2026-02'])]
        entries = group_viewings(records)
        self.assertEqual([entry['viewingNumber'] for entry in entries], [1, 2])
