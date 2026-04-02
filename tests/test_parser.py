from pathlib import Path
from wireviz2kicad import parser


def test_parse_yaml_minimal(tmp_path):
    p = tmp_path / "test.yml"
    p.write_text("title: Foo\nproject: Bar\nauthor: Baz\n")
    meta = parser.parse_yaml(p)
    assert meta["title"] == "Foo"
    assert meta["project"] == "Bar"
    assert meta["author"] == "Baz"
