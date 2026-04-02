import unittest
from pathlib import Path
from wireviz2kicad import parser

class ParserExtendedTests(unittest.TestCase):
    def test_metadata_pn_and_title_block(self):
        p = Path('examples/example_loom.yml')
        meta = parser.parse_yaml(p)
        # pn is present and short form is exposed
        self.assertIn('pn', meta)
        self.assertTrue(meta['pn'].startswith('00'))
        tb = meta.get('title_block') or {}
        self.assertEqual(tb.get('part_number'), meta['pn'])

if __name__ == '__main__':
    unittest.main()
