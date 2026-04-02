"""Placeholder BOM parser and renderer.

Expect TSV with header row; this module will parse TSV into rows. Rendering
into KiCad S-expr tables is TODO for Phase 2.
"""
from pathlib import Path
import csv
from typing import List, Dict


def parse_bom_tsv(path: Path) -> List[Dict[str,str]]:
    with path.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f, delimiter="\t")
        return [row for row in reader]


def render_bom_tsv(path: Path) -> str:
    """Parse TSV BOM and return a KiCad-like S-expression fragment representing the BOM.

    The output format is intentionally simple and conservative: a `(bom ...)` block
    containing one `(item (ref "...") (qty "...") (description "..."))` entry per row.
    This is easy to extend later into a layouted table of text objects.
    """
    rows = parse_bom_tsv(path)
    lines = ["(bom"]
    for r in rows:
        # Normalize common header names
        ref = r.get("Ref") or r.get("ref") or r.get("Reference") or r.get("Ref.") or ""
        qty = r.get("Qty") or r.get("Q") or r.get("Quantity") or r.get("qty") or ""
        # join remaining fields into a description
        description = r.get("Description") or r.get("Desc") or ", ".join(
            [v for k, v in r.items() if k not in ("Ref", "ref", "Qty", "qty", "Description", "Desc") and v]
        )
        # Escape double quotes in values
        def esc(s: str) -> str:
            return s.replace('"', '\\"') if s else ""

        lines.append(f"  (item (ref \"{esc(ref)}\") (qty \"{esc(qty)}\") (description \"{esc(description)}\"))")
    lines.append(")")
    return "\n".join(lines)


def render_bom_table(path: Path, max_width: int = 120, rows_per_page: int = 20) -> str:
    """Render BOM as one or more fixed-width table pages and return S-expression.

    The renderer splits rows into pages of `rows_per_page`. Each page produces a
    separate `(bom (page N/M) (table ...))` block so downstream code can place
    each page on its own sheet or area.
    """
    with path.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f, delimiter="\t")
        headers = reader.fieldnames or []
        rows = [row for row in reader]

    if not headers:
        return "(bom (note \"empty bom\"))"

    # Normalize headers and compute column widths based on content sample
    display_headers = headers

    # Helper to compute widths for a slice of rows
    def compute_col_widths(rows_slice):
        col_widths = {h: len(h) for h in display_headers}
        for r in rows_slice:
            for h in display_headers:
                v = r.get(h) or ""
                col_widths[h] = max(col_widths[h], len(str(v)))
        return col_widths

    # Escape helper
    def esc(s: str) -> str:
        return s.replace("\\", "\\\\").replace('"', '\\"')

    pages = []
    total_rows = len(rows)
    if total_rows == 0:
        # Only header
        col_widths = compute_col_widths([])
        header_line = " | ".join(h.ljust(col_widths[h]) for h in display_headers)
        sep_line = "-+-".join("-" * col_widths[h] for h in display_headers)
        table_lines = [header_line, sep_line]
        lines = ["(bom", "  (table"]
        for l in table_lines:
            lines.append(f'    "{esc(l)}"')
        lines.append("  )")
        lines.append(")")
        return "\n".join(lines)

    # Create pages
    for page_idx in range(0, total_rows, rows_per_page):
        chunk = rows[page_idx : page_idx + rows_per_page]
        col_widths = compute_col_widths(chunk)

        # Adjust Description if total width too large
        total_width = sum(col_widths.values()) + 3 * (len(display_headers) - 1)
        if total_width > max_width and "Description" in display_headers:
            others = sum(col_widths[h] for h in display_headers if h != "Description")
            avail = max_width - others - 3 * (len(display_headers) - 1)
            if avail < 10:
                avail = 10
            col_widths["Description"] = avail

        def trunc(s: str, w: int) -> str:
            s = str(s or "")
            return s if len(s) <= w else s[: max(0, w - 1)] + "…"

        header_line = " | ".join(trunc(h, col_widths[h]).ljust(col_widths[h]) for h in display_headers)
        sep_line = "-+-".join("-" * col_widths[h] for h in display_headers)
        data_lines = []
        for r in chunk:
            parts = [trunc(r.get(h, ""), col_widths[h]).ljust(col_widths[h]) for h in display_headers]
            data_lines.append(" | ".join(parts))

        table_lines = [header_line, sep_line] + data_lines

        # Build S-expression for this page
        page_no = page_idx // rows_per_page + 1
        page_total = (total_rows + rows_per_page - 1) // rows_per_page
        page_block = [f"(bom (page {page_no}/{page_total})", "  (table"]
        for l in table_lines:
            page_block.append(f'    "{esc(l)}"')
        page_block.append("  )")
        page_block.append(")")
        pages.append("\n".join(page_block))

    return "\n".join(pages)


def get_table_pages(path: Path, max_width: int = 120, rows_per_page: int = 20):
    """Return list of pages where each page is a list of table lines (strings).

    This reuses the pagination/layout logic from `render_bom_table` but returns
    raw table lines so callers can render them as text objects with coordinates.
    """
    with path.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f, delimiter="\t")
        headers = reader.fieldnames or []
        rows = [row for row in reader]

    if not headers:
        return [["(empty bom)"]]

    display_headers = headers

    def compute_col_widths(rows_slice):
        col_widths = {h: len(h) for h in display_headers}
        for r in rows_slice:
            for h in display_headers:
                v = r.get(h) or ""
                col_widths[h] = max(col_widths[h], len(str(v)))
        return col_widths

    def trunc(s: str, w: int) -> str:
        s = str(s or "")
        return s if len(s) <= w else s[: max(0, w - 1)] + "…"

    pages = []
    total_rows = len(rows)
    if total_rows == 0:
        col_widths = compute_col_widths([])
        header_line = " | ".join(h.ljust(col_widths[h]) for h in display_headers)
        sep_line = "-+-".join("-" * col_widths[h] for h in display_headers)
        pages.append([header_line, sep_line])
        return pages

    for page_idx in range(0, total_rows, rows_per_page):
        chunk = rows[page_idx : page_idx + rows_per_page]
        col_widths = compute_col_widths(chunk)

        total_width = sum(col_widths.values()) + 3 * (len(display_headers) - 1)
        if total_width > max_width and "Description" in display_headers:
            others = sum(col_widths[h] for h in display_headers if h != "Description")
            avail = max_width - others - 3 * (len(display_headers) - 1)
            if avail < 10:
                avail = 10
            col_widths["Description"] = avail

        header_line = " | ".join(trunc(h, col_widths[h]).ljust(col_widths[h]) for h in display_headers)
        sep_line = "-+-".join("-" * col_widths[h] for h in display_headers)
        data_lines = []
        for r in chunk:
            parts = [trunc(r.get(h, ""), col_widths[h]).ljust(col_widths[h]) for h in display_headers]
            data_lines.append(" | ".join(parts))

        table_lines = [header_line, sep_line] + data_lines
        pages.append(table_lines)

    return pages
