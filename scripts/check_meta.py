from wireviz2kicad import parser
from pathlib import Path
p = Path('examples/example_loom.yml')
print('exists', p.exists())
meta = parser.parse_yaml(p)
print(meta)
