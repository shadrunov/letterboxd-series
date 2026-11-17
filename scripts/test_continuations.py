"""Separately catalogued continuations must not disappear or count twice."""
import unittest
import tempfile
from pathlib import Path
from import_tmdb import discover_references
from test_diary import write_diary, viewing
from copy import deepcopy
from continuations import combine_continuations


class ContinuationTest(unittest.TestCase):
    def test_importer_discovers_continuation_only_for_a_logged_series(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            write_diary(root, [viewing(url='https://www.themoviedb.org/tv/1')])
            (root / 'data').mkdir()
            (root / 'data/season-continuations.yaml').write_text(
                '- series: https://www.themoviedb.org/tv/1\n'
                '  continuation: https://www.themoviedb.org/tv/2\n'
                '  season_offset: 2\n')
            self.assertEqual(discover_references(root), ['tv/1', 'tv/2'])
            write_diary(root, [viewing(url='https://www.themoviedb.org/tv/3')])
            self.assertEqual(discover_references(root), ['tv/3'])

    def test_combines_seasons_with_original_links_without_mutating_cache(self):
        cache = {
            'tv/1': {'seasonDetails': [{'number': 1, 'episodeCount': 7}, {'number': 2, 'episodeCount': 8}], 'showStatus': 'Ended'},
            'tv/2': {'title': 'Renamed continuation', 'showStatus': 'Returning Series', 'seasonDetails': [
                {'number': 0, 'episodeCount': 2},
                {'number': 1, 'episodeCount': 7, 'airDate': '2026-06-07', 'url': 'https://www.themoviedb.org/tv/2/season/1'}]},
        }
        original = deepcopy(cache)
        rules = [{'series': 'tv/1', 'continuation': 'tv/2', 'season_offset': 2}]
        merged = combine_continuations(cache, rules)['tv/1']
        self.assertEqual(merged['numberOfSeasons'], 3)
        self.assertEqual(merged['numberOfEpisodes'], 22)
        self.assertEqual(merged['seasonDetails'][2]['number'], 3)
        self.assertEqual(merged['seasonDetails'][2]['url'], 'https://www.themoviedb.org/tv/2/season/1')
        self.assertEqual(merged['showStatus'], 'Returning Series')
        self.assertEqual(cache, original)
        # If TMDB puts season 3 back on the original title, keep its native data.
        cache['tv/1']['seasonDetails'].append({'number': 3, 'episodeCount': 7, 'name': 'Native season'})
        reunited = combine_continuations(cache, rules)['tv/1']
        self.assertEqual(reunited['numberOfSeasons'], 3)
        self.assertEqual(reunited['numberOfEpisodes'], 22)
        self.assertEqual(reunited['seasonDetails'][2]['name'], 'Native season')

    def test_missing_continuation_fails_instead_of_publishing_incomplete_seasons(self):
        with self.assertRaisesRegex(ValueError, 'Missing TMDB continuation'):
            combine_continuations({'tv/1': {}}, [{'series': 'tv/1', 'continuation': 'tv/2', 'season_offset': 2}])
