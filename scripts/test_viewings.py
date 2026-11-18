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

    def test_mixed_new_and_repeated_seasons_preserve_one_source_record(self):
        entries = self.load({'2026': [
            viewing(date='2026-04-20', seasons=[1, 2], notes='Together'),
            viewing(date='2026-04-01', seasons=[1]),
        ]})
        regular, repeat, first = entries
        self.assertEqual((regular['seasons'], regular['watch']), ([2], 'watch'))
        self.assertEqual((repeat['seasons'], repeat['watch']), ([1], 'rewatch'))
        self.assertEqual(regular['sourceId'], repeat['sourceId'])
        self.assertNotEqual(regular['id'], repeat['id'])
        self.assertEqual(regular['editUrl'], repeat['editUrl'])
        self.assertEqual(regular['notes'], repeat['notes'])
        self.assertEqual(first['watch'], 'watch')

    def test_unfinished_first_attempt_does_not_make_completion_a_rewatch(self):
        entries = self.load({'2026': [
            viewing(date='2026-01', status='unfinished'),
            viewing(date='2026-02'),
            viewing(date='2026-03', status='unfinished'),
        ]})
        self.assertEqual([entry['watch'] for entry in entries], ['watch', 'watch', 'rewatch'])

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
        self.assertEqual(entries[0]['seasons'], [3])
        self.assertEqual(entries[1]['seasons'], [1, 2])
        self.assertEqual(entries[1]['watch'], 'rewatch')
        self.assertTrue(entries[2]['allSeasons'])

    def test_explicit_rewatch_is_preserved_without_an_earlier_record(self):
        entries = self.load({'2026': [viewing(rewatch=True)]})
        self.assertEqual(entries[0]['watch'], 'rewatch')
