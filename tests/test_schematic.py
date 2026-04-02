from wireviz2kicad import schematic


def test_build_sheet_minimal():
    meta = {"title": "T1", "project": "P1", "author": "A1"}
    out = schematic.build_sheet(meta, image_b64=None)
    assert "title" in out.lower()
    assert "kicad_sch" in out


def test_build_sheet_with_bom(tmp_path):
    from wireviz2kicad import bom

    # create a simple bom file
    p = tmp_path / "bom.tsv"
    p.write_text("Id\tDescription\tQty\n1\tPart A\t1\n2\tPart B\t2\n")
    meta = {"title": "T1", "project": "P1", "author": "A1", "bom": str(p)}
    out = schematic.build_sheet(meta, image_b64=None)
    out = str(out)
    # expect a BOM block and BOM content to be present (implementation-agnostic)
    assert "(bom" in out
    assert "Part A" in out
