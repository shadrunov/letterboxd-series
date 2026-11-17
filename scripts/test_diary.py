"""Regression checks for diary editing, unknown dates, and repeated viewings."""
import tempfile
import unittest
from pathlib import Path
from build import load_diary, parse_year, parse_seasons

HEADER = '| Month | Series | Seasons | Watch | Status | Tags | Notes |\n| --- | --- | --- | --- | --- | --- | --- |\n'


class DiaryTest(unittest.TestCase):
    def parse(self, rows, year='2026', catalogue=None):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / f'{year}.md'
            path.write_text(f'# {year}\n\n' + HEADER + rows)
            return parse_year(path, catalogue or {})

    def test_partial_and_complete_rewatches_in_same_month(self):
        entries = self.parse('| Jan | Young Royals | 1-3 | watch | watched | queer | |\n'
                             '| Jan | Young Royals | 2, 3 | rewatch | watched | w/ alena ❤️ | |\n'
                             '| Jan | Young Royals | all | rewatch | unfinished | queer | |\n')
        self.assertEqual(len({e['id'] for e in entries}), 3)
        self.assertEqual(len({e['showId'] for e in entries}), 1)
        self.assertEqual(entries[1]['seasons'], [2, 3])
        self.assertEqual(entries[2]['watch'], 'rewatch')
        self.assertEqual(entries[2]['status'], 'unfinished')
        self.assertTrue(entries[2]['allSeasons'])
        self.assertEqual(entries[2]['seasons'], [])

    def test_rewatch_in_another_year(self):
        original = self.parse('| Feb | Young Royals | 1 | watch | watched | | |\n', '2025')[0]
        repeat = self.parse('| Mar | Young Royals | all | rewatch | watched | | |\n')[0]
        self.assertEqual(original['showId'], repeat['showId'])
        self.assertNotEqual(original['id'], repeat['id'])
        self.assertEqual(original['watched'], '2025-02')
        self.assertEqual(repeat['watched'], '2026-03')

    def test_tags_emoji_escaped_pipes_and_notes(self):
        entry = self.parse('| 8 | Example | S1-S3 | watch | watched | queer, w/ alena ❤️, français, queer | a \\| b |\n')[0]
        self.assertEqual(entry['tags'], ['queer', 'w/ alena ❤️', 'français'])
        self.assertEqual(entry['notes'], 'a | b')
        self.assertEqual(entry['seasons'], [1, 2, 3])

    def test_year_only_and_new_title_need_no_metadata(self):
        entry = self.parse('| ? | A New Series | 1 | | | | |\n')[0]
        self.assertEqual(entry['watched'], '2026')
        self.assertNotIn('poster', entry)
        self.assertEqual(entry['status'], 'watched')

    def test_catalogue_lookup_ignores_title_case(self):
        entry = self.parse('| Jan | example | 1 | watch | watched | | |\n', catalogue={'example': {'id': 'example-id', 'poster': 'example.jpg'}})[0]
        self.assertEqual(entry['showId'], 'example-id')
        self.assertEqual(entry['poster'], 'example.jpg')

    def test_empty_year_table(self):
        self.assertEqual(self.parse(''), [])

    def test_invalid_rows_fail_with_file_and_line(self):
        for row in ['| nope | Example | 1 | watch | watched | | |\n',
                    '| Jan | Example | 3-1 | watch | watched | | |\n',
                    '| Jan | Example | 1 | maybe | watched | | |\n',
                    '| Jan | Example | 1 | watch | complete | | |\n',
                    '| Jan | Example | 1 | watch | watched | missing column |\n']:
            with self.subTest(row=row), self.assertRaisesRegex(ValueError, r'2026\.md:\d+:'):
                self.parse(row)

    def test_season_validation(self):
        for value in ['0', '', '1,1', '1-4,3', '1001', '<script>']:
            with self.subTest(value=value), self.assertRaises(ValueError):
                parse_seasons(value)

    def test_year_files_sort_newest_first(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'diary').mkdir()
            (root / 'data').mkdir()
            (root / 'data/shows.csv').write_text('Series,Year,Poster,URL,Genres,Summary,Image source\n')
            for year in ['2024', '2026', '2025']:
                (root / 'diary' / f'{year}.md').write_text(HEADER)
            diary = load_diary(root)
            self.assertEqual(diary['years'], ['2026', '2025', '2024'])
            self.assertEqual(diary['entries'], [])


if __name__ == '__main__':
    unittest.main()
