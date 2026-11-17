"""TMDB import regression tests use fixture responses; never need credentials or network."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from build import parse_year, load_diary
from import_tmdb import discover_references, fetch_metadata, import_titles, request_bytes
from test_diary import HEADER
from tmdb import parse_reference


class TMDBTest(unittest.TestCase):
    def root(self, directory, rows):
        root = Path(directory)
        (root / 'diary').mkdir()
        (root / 'diary/2026.md').write_text(HEADER + rows)
        return root

    def test_url_canonicalization(self):
        for url in ['https://www.themoviedb.org/tv/100088/',
                    'https://themoviedb.org/tv/100088-heartstopper?language=en#cast',
                    '[Heartstopper](https://www.themoviedb.org/tv/100088)']:
            self.assertEqual(parse_reference(url), 'tv/100088')
        self.assertEqual(parse_reference('https://www.themoviedb.org/movie/1751639/'), 'movie/1751639')
        self.assertIsNone(parse_reference('Young Royals'))
        for url in ['https://evil.test/tv/100088', 'https://www.themoviedb.org/person/1',
                    'https://www.themoviedb.org/tv/1/season/2', 'https://www.themoviedb.org/tv/0']:
            with self.subTest(url=url), self.assertRaises(ValueError):
                parse_reference(url)

    def test_read_token_and_v3_api_key_authentication(self):
        from unittest.mock import MagicMock
        for secret, expected_query in [('fixture-read-token', False), ('a' * 32, True), ('Bearer fixture-read-token', False)]:
            response = MagicMock()
            response.__enter__.return_value.read.return_value = b'{}'
            with patch('import_tmdb.urlopen', return_value=response) as open_url:
                request_bytes('https://api.themoviedb.org/3/tv/100088?language=en-US', secret)
            request = open_url.call_args.args[0]
            if expected_query:
                self.assertIn('api_key=', request.full_url)
                self.assertIsNone(request.get_header('Authorization'))
            else:
                self.assertNotIn('api_key=', request.full_url)
                self.assertEqual(request.get_header('Authorization'), 'Bearer fixture-read-token')

    def test_discovery_fetches_each_title_once(self):
        with tempfile.TemporaryDirectory() as directory:
            root = self.root(directory, '| Jan | https://www.themoviedb.org/tv/100088 | 1 | watch | watched | | |\n'
                             '| Oct | https://www.themoviedb.org/tv/100088-heartstopper | all | rewatch | watched | | |\n')
            self.assertEqual(discover_references(root), ['tv/100088'])
            with patch('import_tmdb.fetch_metadata', return_value={'title': 'Heartstopper', 'poster': ''}) as fetch:
                import_titles(root, root / 'cache', token='fixture-token')
                self.assertEqual(fetch.call_count, 1)
            with patch('import_tmdb.fetch_metadata') as fetch:
                import_titles(root, root / 'cache')
                fetch.assert_not_called()

    def test_new_links_need_token_and_leave_no_partial_catalogue(self):
        with tempfile.TemporaryDirectory() as directory:
            root = self.root(directory, '| Jan | https://www.themoviedb.org/tv/100088 | 1 | watch | watched | | |\n')
            with self.assertRaisesRegex(ValueError, 'TMDB_READ_ACCESS_TOKEN'):
                import_titles(root, root / 'cache')
            self.assertFalse((root / 'cache/catalogue.json').exists())
            with patch('import_tmdb.fetch_metadata', side_effect=ValueError('Not found')):
                with self.assertRaisesRegex(ValueError, 'Not found'):
                    import_titles(root, root / 'cache', token='fixture-token')
            self.assertFalse((root / 'cache/catalogue.json').exists())

    def test_metadata_and_poster_saved_without_credentials(self):
        payload = {'id': 100088, 'name': 'Heartstopper', 'first_air_date': '2022-04-22',
                   'poster_path': '/fixture.jpg', 'genres': [{'name': 'Drama'}], 'overview': 'A story.'}
        with tempfile.TemporaryDirectory() as directory:
            cache = Path(directory)
            with patch('import_tmdb.request_bytes', side_effect=[json.dumps(payload).encode(), b'poster-fixture']) as request:
                metadata = fetch_metadata('tv/100088', 'fixture-secret', cache)
            self.assertEqual(metadata['title'], 'Heartstopper')
            self.assertEqual(metadata['year'], 2022)
            self.assertEqual(metadata['source'], 'TMDB')
            self.assertEqual(metadata['poster'], 'assets/posters/tmdb/tv-100088.jpg')
            self.assertEqual((cache / 'posters/tv-100088.jpg').read_bytes(), b'poster-fixture')
            self.assertNotIn('fixture-secret', json.dumps(metadata))
            self.assertIn('/3/tv/100088?', request.call_args_list[0].args[0])

    def test_missing_poster_reimports_and_refresh_reimports(self):
        with tempfile.TemporaryDirectory() as directory:
            root = self.root(directory, '| Jan | https://www.themoviedb.org/tv/100088 | 1 | watch | watched | | |\n')
            cache = root / 'cache'
            cache.mkdir()
            (cache / 'catalogue.json').write_text(json.dumps({'tv/100088': {'poster': 'assets/posters/tmdb/tv-100088.jpg'}}))
            with patch('import_tmdb.fetch_metadata', return_value={'poster': ''}) as fetch:
                import_titles(root, cache, token='fixture-token')
                self.assertEqual(fetch.call_count, 1)
            with patch('import_tmdb.fetch_metadata', return_value={'poster': ''}) as fetch:
                import_titles(root, cache, token='fixture-token', refresh=True)
                self.assertEqual(fetch.call_count, 1)

    def test_movie_uses_movie_endpoint_and_blank_seasons(self):
        payload = {'id': 1751639, 'title': 'Fixture Film', 'release_date': '', 'poster_path': None}
        with tempfile.TemporaryDirectory() as directory:
            root = self.root(directory, '| Jan | https://www.themoviedb.org/movie/1751639/ | | rewatch | watched | queer | |\n')
            with patch('import_tmdb.request_bytes', return_value=json.dumps(payload).encode()) as request:
                metadata = fetch_metadata('movie/1751639', 'fixture-token', root / 'cache')
            self.assertIn('/3/movie/1751639?', request.call_args.args[0])
            entries = parse_year(root / 'diary/2026.md', {}, {'movie/1751639': metadata})
            self.assertEqual(entries[0]['title'], 'Fixture Film')
            self.assertEqual(entries[0]['seasons'], [])
            self.assertEqual(entries[0]['mediaType'], 'movie')

    def test_existing_plain_title_and_tmdb_rewatch_share_identity(self):
        with tempfile.TemporaryDirectory() as directory:
            root = self.root(directory, '| Jan | Heartstopper | 3 | watch | watched | | |\n'
                             '| Sep | https://www.themoviedb.org/tv/100088 | all | rewatch | watched | | |\n')
            (root / 'data').mkdir()
            (root / 'data/shows.csv').write_text('Series,Year,Poster,URL,Genres,Summary,Image source\n')
            (root / '.cache/tmdb').mkdir(parents=True)
            (root / '.cache/tmdb/catalogue.json').write_text(json.dumps({
                'tv/100088': {'id': 'tmdb:tv/100088', 'source': 'TMDB', 'title': 'Heartstopper', 'poster': ''}
            }))
            entries = load_diary(root)['entries']
            self.assertEqual(entries[0]['showId'], entries[1]['showId'])
            self.assertNotEqual(entries[0]['id'], entries[1]['id'])

    def test_uncached_reference_reports_location(self):
        with tempfile.TemporaryDirectory() as directory:
            root = self.root(directory, '| Jan | https://www.themoviedb.org/tv/100088 | 1 | watch | watched | | |\n')
            with self.assertRaisesRegex(ValueError, r'2026.md:3:.*not cached'):
                parse_year(root / 'diary/2026.md', {})


if __name__ == '__main__':
    unittest.main()
