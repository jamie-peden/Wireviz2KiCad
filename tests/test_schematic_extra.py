from wireviz2kicad import schematic


def test_build_sheet_returns_string_and_unpackable():
    meta = {"title": "T1", "project": "P1", "author": "A1"}
    result = schematic.build_sheet(meta, image_b64=None)
    # result should behave like a string
    s = str(result)
    assert "kicad_sch" in s
    # but also support unpacking (main, bom)
    main, bom = result
    assert isinstance(main, str)
    # bom may be None or a string
    assert (bom is None) or isinstance(bom, str)
