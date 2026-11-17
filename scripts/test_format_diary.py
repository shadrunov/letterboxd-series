"""Formatting must be stable and preserve source records, comments, and note values."""
import tempfile
import unittest
from pathlib import Path
from yamllint import linter
from yamllint.config import YamlLintConfig
from diary import ROOT, read_document
from format_diary import formatted_document, format_diaries

URL = 'https://www.themoviedb.org/tv/125910'


class FormatDiaryTest(unittest.TestCase):
    def path(self, directory, text):
        root = Path(directory)
        (root / 'diary').mkdir(exist_ok=True)
        path = root / 'diary/2026.yaml'
        path.write_text(text)
        return path

    def test_sorting_is_newest_first_and_equal_dates_keep_their_order(self):
        text = ''.join(f'- url: {URL}\n  date: {date}\n  seasons: [{season}]\n  tags: []\n' for date, season in [('2026-01',1),('2026-08',2),('2026-08',3),('2026-03-12',4)])
        with tempfile.TemporaryDirectory() as directory:
            path = self.path(directory, text)
            output = formatted_document(path)
            rows = [row for _,row,_ in read_document(path, text=output)[1]]
            self.assertEqual([row['seasons'] for row in rows], [[2],[3],[4],[1]])
            path.write_text(output)
            self.assertEqual(formatted_document(path), output)

    def test_field_order_comments_unicode_and_flow_lists(self):
        text = f'# My diary\n- tags:\n  - "w/ alena ❤️"\n  seasons:\n  - 1\n  - 3\n  date: 2026-07\n  name: "Young Royals" # readable title\n  url: {URL} # source\n'
        with tempfile.TemporaryDirectory() as directory:
            path = self.path(directory, text)
            output = formatted_document(path)
            row = read_document(path, text=output)[1][0][1]
            self.assertEqual(list(row), ['url','name','date','seasons','tags'])
            self.assertIn('# My diary', output)
            self.assertIn('# readable title', output)
            self.assertIn('# source', output)
            self.assertIn('seasons: [1, 3]', output)
            self.assertIn('tags: ["w/ alena ❤️"]', output)
            config = YamlLintConfig(file=str(ROOT / '.yamllint.yaml'))
            self.assertFalse(list(linter.run(output, config)))

    def test_multiline_notes_keep_trailing_blank_lines_and_spaces(self):
        text = f'- url: {URL}\n  date: 2026-01\n  seasons: [1]\n  notes: |+\n    first line  \n\n    second line\n\n\n'
        with tempfile.TemporaryDirectory() as directory:
            path = self.path(directory, text)
            before = read_document(path)[1][0][1]['notes']
            output = formatted_document(path)
            self.assertEqual(read_document(path, text=output)[1][0][1]['notes'], before)
            path.write_text(output)
            self.assertEqual(formatted_document(path), output)

    def test_check_mode_never_writes_and_second_pass_makes_no_change(self):
        text = f'- date: 2026-01\n  seasons: [1]\n  url: {URL}\n'
        with tempfile.TemporaryDirectory() as directory:
            path = self.path(directory, text)
            self.assertEqual(format_diaries(Path(directory), check=True), 1)
            self.assertEqual(path.read_text(), text)
            self.assertEqual(format_diaries(Path(directory)), 1)
            self.assertEqual(format_diaries(Path(directory), check=True), 0)

    def test_invalid_file_stops_all_writes(self):
        with tempfile.TemporaryDirectory() as directory:
            path = self.path(directory, f'- date: 2026-01\n  seasons: [1]\n  url: {URL}\n')
            original = path.read_text()
            (path.parent / '2025.yaml').write_text(f'- url: {URL}\n  date: 2025-13\n  seasons: [1]\n')
            with self.assertRaises(ValueError):
                format_diaries(Path(directory))
            self.assertEqual(path.read_text(), original)

    def test_empty_year_and_comment_only_files(self):
        for text in ['[]\n', '# Empty year\n', '']:
            with tempfile.TemporaryDirectory() as directory:
                path = self.path(directory, text)
                output = formatted_document(path)
                self.assertEqual(read_document(path, text=output)[1], [])
                path.write_text(output)
                self.assertEqual(formatted_document(path), output)


if __name__ == '__main__':
    unittest.main()
