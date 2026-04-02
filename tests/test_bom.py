from pathlib import Path
from wireviz2kicad import bom


def test_render_bom_tsv(tmp_path):
    p = tmp_path / "bom.tsv"
    p.write_text("Ref\tQty\tDescription\nU1\t1\tATMEGA328\nU2\t2\tLED\n")
    out = bom.render_bom_tsv(p)
    assert out.startswith("(bom")
    assert "(item (ref \"U1\") (qty \"1\")" in out
    assert "ATMEGA328" in out


def test_render_bom_table(tmp_path):
    p = tmp_path / "bom.tsv"
    p.write_text("Id\tDescription\tQty\tUnit\tDesignators\tManufacturer\tMPN\n1\tCable, UL1007, 12 x 24 AWG\t150\tmm\tW1-I/O-Connector\tAlpha Wire\t6712\n2\tConnector, Keystone 7312\t1\t\tJ5\tKeystone\t1270\n")
    out = bom.render_bom_table(p)
    assert out.startswith("(bom")
    assert "Description" in out
    assert "Cable, UL1007" in out


def test_render_bom_paging(tmp_path):
    p = tmp_path / "bom.tsv"
    # create 55 rows to force multiple pages with default rows_per_page=20
    headers = "Id\tDescription\tQty\tUnit\tDesignators\tManufacturer\tMPN\n"
    rows = []
    for i in range(1, 56):
        rows.append(f"{i}\tPart {i} description\t1\t\tJ{i}\tMaker\tMPN{i}")
    p.write_text(headers + "\n".join(rows) + "\n")
    out = bom.render_bom_table(p, rows_per_page=20)
    # Expect 3 page blocks
    assert out.count("(bom (page") == 3
    assert "Part 1 description" in out
    assert "Part 55 description" in out