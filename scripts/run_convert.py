from pathlib import Path
from wireviz2kicad.cli import convert

if __name__ == '__main__':
    convert(Path('examples/example_loom.yml'), Path('out.kicad_sch'))
