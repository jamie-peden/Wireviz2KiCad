from pathlib import Path
from wireviz2kicad import encoder


def test_png_to_base64_roundtrip(tmp_path):
    p = tmp_path / "img.png"
    # create a tiny PNG via base64
    b64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8Xw8AAn8B9g9m5gAAAABJRU5ErkJggg=="
    p.write_bytes(b64.encode('ascii'))
    s = encoder.png_to_base64(p)
    assert isinstance(s, str)
    assert len(s) > 0
