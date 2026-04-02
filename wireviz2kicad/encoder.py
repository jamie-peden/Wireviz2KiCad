"""Image encoder utilities."""
from pathlib import Path
import base64


def png_to_base64(path: Path) -> str:
    """Read PNG file and return base64-encoded string suitable for embedding."""
    with path.open("rb") as f:
        data = f.read()
    return base64.b64encode(data).decode("ascii")


def png_to_hex_lines(path: Path, bytes_per_token: int = 32):
    """Read PNG file and return a list of hex-data token strings.

    Each returned string is suitable for insertion as a `(data ...)` token
    in KiCad S-expressions: bytes are formatted as two-digit hex values
    separated by spaces, with at most `bytes_per_token` bytes per token.
    """
    with path.open("rb") as f:
        data = f.read()

    lines = []
    for i in range(0, len(data), bytes_per_token):
        chunk = data[i : i + bytes_per_token]
        hex_parts = [f"{b:02X}" for b in chunk]
        lines.append(" ".join(hex_parts))
    return lines


def png_size(path: Path):
    """Return (width, height) in pixels for a PNG file without external deps.

    Reads the PNG IHDR chunk (big-endian) to extract dimensions.
    """
    with path.open("rb") as f:
        sig = f.read(8)
        if sig[:8] != b"\x89PNG\r\n\x1a\n":
            raise ValueError("Not a PNG file")
        # IHDR chunk is the first after signature: 4 bytes length, 4 bytes 'IHDR', then 13 bytes data
        length_bytes = f.read(4)
        if len(length_bytes) < 4:
            raise ValueError("Truncated PNG")
        chunk_type = f.read(4)
        if chunk_type != b"IHDR":
            # seek forward until IHDR found (robustness)
            f.seek(0)
            data = f.read()
            idx = data.find(b"IHDR")
            if idx == -1:
                raise ValueError("IHDR not found in PNG")
            # IHDR data starts 4 bytes after the 'IHDR' bytes
            hdr_off = idx + 4
            # width and height are the first 8 bytes of IHDR data
            width = int.from_bytes(data[hdr_off:hdr_off+4], "big")
            height = int.from_bytes(data[hdr_off+4:hdr_off+8], "big")
            return width, height
        # read IHDR data
        ihdr = f.read(13)
        if len(ihdr) < 8:
            raise ValueError("Truncated IHDR")
        width = int.from_bytes(ihdr[0:4], "big")
        height = int.from_bytes(ihdr[4:8], "big")
        return width, height
