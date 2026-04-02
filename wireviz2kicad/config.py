"""Global configuration loader for wireviz2kicad.

Simple YAML-based loader that returns a dict of defaults which can be
merged with per-sheet metadata. Auto-discovers `.wireviz2kicad.yml` in
the current working directory when `path` is None.
"""
from pathlib import Path
import yaml
from typing import Optional


def load_config(path: Optional[Path] = None) -> dict:
    """Load YAML config from `path` or auto-discover `.wireviz2kicad.yml`.

    Returns an empty dict if no config is found or on parse errors.
    """
    try:
        if path:
            p = Path(path)
        else:
            p = Path.cwd() / ".wireviz2kicad.yml"
        if not p.exists():
            return {}
        with p.open("r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
            if not isinstance(data, dict):
                return {}
            return data
    except Exception:
        return {}
