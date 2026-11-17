"""YAML diary validation, metadata write-back, and repeat-viewing regression checks."""
import json
import tempfile
import unittest
from pathlib import Path
import yaml
from build import load_diary, parse_year
from diary import parse_seasons, read_document, fill_names

URL = 'https://www.themoviedb.org/tv/125910'
SHOW = {'id': 'tmdb:tv/125910', 'title': 'Young Royals', 'source': 'TMDB', 'mediaType': 'tv'}


def viewing(**changes):
    return dict(url=URL, date='2026-01', seasons=[1], tags=[], **{}) | changes


def write_diary(root, rows, year='2026'):
    directory = root / 'diary'
    directory.mkdir(exist_ok=True)
    path = directory / f'{year}.yaml'
    path.write_text(yaml.safe_dump(rows, allow_unicode=True, sort_keys=False))
    return path


class DiaryTest(unittest.TestCase):
    def parse(self, rows, year='2026'):
        with tempfile.TemporaryDirectory() as directory:
            path = write_diary(Path(directory), rows, year)
            return parse_year(path, {'tv/125910': SHOW})

    def test_partial_and_complete_rewatches_stay_separate(self):
        entries = self.parse([viewing(seasons=[1,2,3]), viewing(seasons=[2,3], rewatch=True), viewing(seasons='all', rewatch=True, status='unfinished')])
        self.assertEqual(len({e['id'] for e in entries}), 3)
        self.assertEqual(len({e['showId'] for e in entries}), 1)
        self.assertEqual(entries[1]['seasons'], [2,3])
        self.assertEqual(entries[1]['watch'], 'rewatch')
        self.assertEqual(entries[2]['status'], 'unfinished')
        self.assertTrue(entries[2]['allSeasons'])
        self.assertEqual(entries[2]['seasons'], [])

    def test_dates_keep_precision_and_enforce_file_year(self):
        entries = self.parse([viewing(date='2026-02-28'), viewing(date=2026)])
        self.assertEqual(entries[0]['watched'], '2026-02')
        self.assertEqual(entries[0]['watchDate'], '2026-02-28')
        self.assertEqual(entries[1]['watched'], '2026')
        for value in ['2026-02-30', '2026-13', '2025-01', 'Jan', True, None]:
            with self.subTest(value=value), self.assertRaises(ValueError):
                self.parse([viewing(date=value)])

    def test_tags_notes_and_names_need_no_escaping_pipes(self):
        entry = self.parse([viewing(tags=['queer','w/ alena ❤️','français','queer'], notes='a | b', name='Readable name')])[0]
        self.assertEqual(entry['tags'], ['queer','w/ alena ❤️','français'])
        self.assertEqual(entry['notes'], 'a | b')
        self.assertEqual(entry['title'], 'Young Royals')

    def test_empty_year_files_and_sorting(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for year in ['2024','2026','2025']:
                write_diary(root, [], year)
            diary = load_diary(root)
            self.assertEqual(diary['years'], ['2026','2025','2024'])
            self.assertEqual(diary['entries'], [])

    def test_invalid_fields_report_file_and_line(self):
        for row in [viewing(url='https://example.com/tv/1'), viewing(tags='queer'), viewing(seasons=[]), viewing(seasons=[True]), viewing(rewatch='yes'), viewing(status='complete'), viewing(dtae='2026-01')]:
            with self.subTest(row=row), self.assertRaisesRegex(ValueError, r'2026\.yaml:\d+:'):
                self.parse([row])

    def test_duplicate_yaml_fields_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / '2026.yaml'
            path.write_text(f'- url: {URL}\n  date: 2026-01\n  date: 2026-02\n  seasons: [1]\n')
            with self.assertRaisesRegex(ValueError, 'duplicate field date'):
                read_document(path)

    def test_season_formats_and_validation(self):
        self.assertEqual(parse_seasons('S1-S3'), [1,2,3])
        self.assertEqual(parse_seasons([3,1]), [1,3])
        self.assertEqual(parse_seasons(2), [2])
        self.assertEqual(parse_seasons('all'), [])
        for value in [0, '', [1,1], '1-4,3', 1001, '<script>', True]:
            with self.subTest(value=value), self.assertRaises(ValueError):
                parse_seasons(value)

    def test_name_writeback_preserves_comments_and_all_user_fields(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'diary').mkdir()
            path = root / 'diary/2026.yaml'
            original = f'# My diary\n- url: {URL}  # source\n  date: 2026-01\n  seasons: [1, 3]\n  tags: [queer, "w/ alena ❤️"]  # keep\n  notes: "a | b"\n'
            path.write_text(original)
            self.assertEqual(fill_names(root, {'tv/125910': SHOW}), 1)
            self.assertEqual(path.read_text(), original.replace('  # source\n', '  # source\n  name: "Young Royals"\n'))
            self.assertEqual(fill_names(root, {'tv/125910': SHOW}), 0)
            self.assertEqual(read_document(path)[1][0][1]['name'], 'Young Royals')

    def test_updates_existing_name_and_handles_final_line_without_newline(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = write_diary(root, [viewing(name='Old name'), viewing(rewatch=True)])
            self.assertEqual(fill_names(root, {'tv/125910': SHOW}), 2)
            self.assertTrue(all(row['name']=='Young Royals' for _,row,_ in read_document(path)[1]))
            path.write_text(f'- date: 2026-01\n  seasons: [1]\n  url: {URL}')
            self.assertEqual(fill_names(root, {'tv/125910': SHOW}), 1)
            self.assertEqual(read_document(path)[1][0][1]['name'], 'Young Royals')

    def test_empty_name_placeholders_keep_valid_yaml_and_comments(self):
        for placeholder in ['name:', 'name: # keep']:
            with tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                path = write_diary(root, [])
                path.write_text(f'- url: {URL}\n  {placeholder}\n  date: 2026-01\n  seasons: [1]\n')
                self.assertEqual(fill_names(root, {'tv/125910': SHOW}), 1)
                self.assertEqual(read_document(path)[1][0][1]['name'], 'Young Royals')
                if '# keep' in placeholder:
                    self.assertIn('# keep', path.read_text())


if __name__ == '__main__':
    unittest.main()
