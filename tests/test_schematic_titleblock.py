import unittest
from pathlib import Path
from wireviz2kicad import parser, encoder, schematic

class SchematicTitleBlockTests(unittest.TestCase):
    def test_title_block_comments_and_pn(self):
        p = Path('examples/example_loom.yml')
        meta = parser.parse_yaml(p)
        img_b64 = None
        if meta.get('png'):
            img_b64 = encoder.png_to_base64(Path(meta['png']))
        main, bom = schematic.build_sheet(meta, img_b64, sheet_size='A3')
        # title_block opening and comment entries
        self.assertIn('(title_block', main)
        self.assertIn('(comment 1 "', main)
        self.assertIn(meta.get('pn'), main)
        # author comments
        self.assertIn('(comment 2 "JP")', main)
        self.assertIn('(comment 3 "SH")', main)
        self.assertIn('(comment 4 "WM")', main)

if __name__ == '__main__':
    unittest.main()
