"""Simple YAML parser for WireViz inputs."""
from pathlib import Path
import yaml


def parse_yaml(path: Path) -> dict:
    """Parse a WireViz YAML file and return metadata dict.

    Expected keys (best-effort): title, project, author, png, bom
    """
    with path.open("r", encoding="utf-8") as f:
        try:
            data = yaml.safe_load(f)
        except yaml.YAMLError as e:
            # Provide a clearer error message including file path
            raise ValueError(f"Failed to parse YAML file {path}: {e}") from e
    # If file is empty or contains only comments, safe_load may return None
    if data is None:
        data = {}
    meta = {}
    p = Path(path)
    # Best-effort extraction
    # Support top-level `title` or nested `metadata.title` (WireViz output)
    metadata_node = data.get("metadata") if isinstance(data, dict) else None
    meta["title"] = (
        data.get("title")
        or (metadata_node.get("title") if isinstance(metadata_node, dict) else None)
        or data.get("project")
        or Path(path).stem
    )
    # company/project and author fields may live under `metadata`
    meta["project"] = data.get("project") or (metadata_node.get("company") if isinstance(metadata_node, dict) else None)
    # try common author fields
    author = data.get("author")
    if not author and isinstance(metadata_node, dict):
        # try metadata.authors.Created.name or metadata.authors.Approved.name
        authors = metadata_node.get("authors")
        if isinstance(authors, dict):
            created = authors.get("Created")
            if isinstance(created, dict):
                author = created.get("name")
            if not author:
                approved = authors.get("Approved")
                if isinstance(approved, dict):
                    author = approved.get("name")
    meta["author"] = author
    # Build a title_block dict from metadata authors and common fields
    title_block = {}
    if isinstance(metadata_node, dict):
        authors = metadata_node.get("authors")
        # authors may be a dict keyed by role, or a list of author entries
        if isinstance(authors, dict):
            # support case-insensitive keys like 'checked' or 'Checked'
            lower_map = {k.lower(): v for k, v in authors.items()}
            created = lower_map.get("created")
            if isinstance(created, dict):
                title_block["engineer"] = created.get("name")
            checked = lower_map.get("checked") or lower_map.get("reviewer") or lower_map.get("reviewed")
            if isinstance(checked, dict):
                title_block["checked"] = checked.get("name")
            approved = lower_map.get("approved")
            if isinstance(approved, dict):
                title_block["approved"] = approved.get("name")
        elif isinstance(authors, list):
            # list entries often contain dicts with name and optional role/type
            for a in authors:
                if not isinstance(a, dict):
                    continue
                name = a.get("name") or a.get("author")
                role = a.get("role") or a.get("type") or a.get("job")
                if not name:
                    continue
                if role:
                    r = str(role).strip().lower()
                    if "create" in r or "engineer" in r:
                        title_block.setdefault("engineer", name)
                    elif "check" in r or "review" in r:
                        title_block.setdefault("checked", name)
                    elif "approv" in r:
                        title_block.setdefault("approved", name)
                    else:
                        # generic mapping: first author becomes engineer if unset
                        title_block.setdefault("engineer", name)
                else:
                    title_block.setdefault("engineer", name)
    # allow top-level mappings for title_block fields in the wireviz YAML
    # e.g. title_block: { part_number: ..., comment1: ... }
    tb_node = data.get("title_block") or (metadata_node.get("title_block") if isinstance(metadata_node, dict) else None)
    if isinstance(tb_node, dict):
        # copy user-provided title_block fields, overriding extracted authors
        for k, v in tb_node.items():
            title_block[k] = v
    # Allow a template reference for title block (string or dict)
    tb_template = data.get("title_block_template") or (
        metadata_node.get("title_block_template") if isinstance(metadata_node, dict) else None
    )
    if tb_template:
        meta["title_block_template"] = tb_template
    # try common per-sheet fields
    # file -> YAML filename, part_number or part
    title_block.setdefault("file", str(p.name))
    # part number may be under top-level keys or under metadata
    part_no = (
        data.get("part_number")
        or data.get("part")
        or data.get("pn")
        or (metadata_node.get("pn") if isinstance(metadata_node, dict) else None)
    )
    if part_no:
        title_block.setdefault("part_number", part_no)
        # expose short PN at top-level meta for easy access by renderer
        meta["pn"] = part_no
    # size and id may be provided
    if data.get("size"):
        title_block.setdefault("size", data.get("size"))
    if data.get("id"):
        title_block.setdefault("id", data.get("id"))
    # attach title_block to meta if any entries exist
    if title_block:
        meta["title_block"] = title_block
    # wireviz image/bom paths: try common keys
    meta["png"] = data.get("png") or data.get("image")
    meta["bom"] = data.get("bom")

    # If PNG not specified, look for a PNG with same stem in the same directory
    p = Path(path)
    if not meta.get("png"):
        candidate = p.with_suffix(".png")
        if candidate.exists():
            meta["png"] = str(candidate)
        else:
            alt = p.parent / (p.stem + ".png")
            if alt.exists():
                meta["png"] = str(alt)

    # If BOM not specified, look for common BOM filenames next to the YAML
    if not meta.get("bom"):
        candidate_bom = p.with_suffix(".bom.tsv")
        if candidate_bom.exists():
            meta["bom"] = str(candidate_bom)
        else:
            alt_bom = p.parent / (p.stem + ".bom.tsv")
            if alt_bom.exists():
                meta["bom"] = str(alt_bom)

    return meta
