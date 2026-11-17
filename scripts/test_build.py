"""Publishing checks: matched asset versions and safely embedded diary data."""
import json
import re
import unittest
from build import render_index

PAGE = '<link href="style.css"><!-- DIARY_DATA --><script src="app.js" defer></script>'


class PublishedPageTest(unittest.TestCase):
    def test_diary_data_is_present_without_a_network_request(self):
        diary = {'years': ['2026'], 'entries': [{'title': 'Mary & George'}]}
        html = render_index(PAGE, diary, b'javascript', b'stylesheet')
        payload = re.search(r'<script id="diary-data" type="application/json">(.*?)</script>', html)[1]
        self.assertEqual(json.loads(payload), diary)

    def test_script_closing_tags_in_metadata_cannot_escape_json_block(self):
        diary = {'entries': [{'title': '</script><script>alert(1)</script> & <em>story</em>'}]}
        html = render_index(PAGE, diary, b'javascript', b'stylesheet')
        payload = re.search(r'<script id="diary-data" type="application/json">(.*?)</script>', html)[1]
        self.assertNotIn('<', payload)
        self.assertNotIn('>', payload)
        self.assertNotIn('&', payload)
        self.assertEqual(json.loads(payload), diary)

    def test_versions_change_only_with_the_matching_asset(self):
        a = render_index(PAGE, {}, b'old code', b'style')
        b = render_index(PAGE, {}, b'new code', b'style')
        self.assertNotEqual(re.search(r'app.js\?v=([a-f0-9]+)', a)[1], re.search(r'app.js\?v=([a-f0-9]+)', b)[1])
        self.assertEqual(re.search(r'style.css\?v=([a-f0-9]+)', a)[1], re.search(r'style.css\?v=([a-f0-9]+)', b)[1])
        self.assertEqual(a, render_index(PAGE, {}, b'old code', b'style'))


if __name__ == '__main__':
    unittest.main()
