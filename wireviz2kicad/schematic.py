"""Minimal KiCad S-expression builder to embed PNG and title block.

This module produces a very small, template-like `.kicad_sch` content containing
an `image` object with base64 data and simple text fields for the title block.

This is a starting point and should be extended to match real KiCad templates.
"""
from typing import Optional, List
from pathlib import Path
import uuid
from datetime import date
from . import encoder as wz_encoder


def build_sheet(
    meta: dict,
    image_b64: Optional[str],
    sheet_size: str = "A3",
    include_bom: bool = True,
    image_align: str = "fit-width",
    max_image_scale: Optional[float] = None,
    force_inline_bom: bool = False,
    force_split_bom: bool = False,
):
    # Title-block values extracted from meta (merged from parser)
    tb = meta.get("title_block") or {}

    # Prefer explicit top-level fields, then fall back to title_block entries.
    title = meta.get("title") or tb.get("title") or "WireViz Sheet"
    project = tb.get("company") or meta.get("project") or ""
    author = meta.get("author") or tb.get("engineer") or ""
    rev = tb.get("rev") or meta.get("rev") or "1"

    # KiCad-compatible S-expression header (closer to eeschema output)
    gen_uuid = str(uuid.uuid4())
    today = date.today().isoformat()
    header_parts = [
        "(kicad_sch",
        f"\t(version 20250114)",
        f"\t(generator \"eeschema\")",
        f"\t(generator_version \"9.0\")",
        f"\t(uuid \"{gen_uuid}\")",
        f"\t(paper \"{sheet_size}\")",
        "\t(title_block",
        f"\t\t(title \"{title}\")",
        f"\t\t(date \"{today}\")",
        f"\t\t(rev \"{rev}\")",
        f"\t\t(company \"{project or ''}\")",
    ]

    # comment entries inside the title_block
    # prefer explicit part_number (from parser), then pn, then top-level meta pn, then file
    c1 = tb.get("part_number") or tb.get("pn") or meta.get("pn") or tb.get("file") or ""
    c2 = tb.get("engineer") or ""
    c3 = tb.get("checked") or ""
    c4 = tb.get("approved") or ""

    # Title-block template support (simple placeholder formatting).
    # If `meta['title_block_template']` is a string it may contain placeholders
    # like {pn}, {engineer}, {checked}, {approved}, {title}, {company}, {date}.
    tb_template = meta.get("title_block_template")

    class _SafeDict(dict):
        def __missing__(self, key):
            return ""

    mapping = _SafeDict({
        "pn": c1,
        "part_number": c1,
        "engineer": c2,
        "checked": c3,
        "approved": c4,
        "title": title,
        "company": project,
        "date": today,
        "rev": rev,
    })

    if isinstance(tb_template, str) and tb_template.strip():
        try:
            rendered = tb_template.format_map(mapping)
            # add each non-empty line inside the title_block
            for line in rendered.splitlines():
                line = line.rstrip()
                if not line:
                    continue
                # if the template already contains leading parens/fields, append directly
                if line.startswith("("):
                    header_parts.append(f"\t\t{line}")
                else:
                    header_parts.append(f"\t\t{line}")
        except Exception:
            # fallback to default simple comment lines if template fails
            header_parts.append(f"\t\t(comment 1 \"{c1}\")")
            header_parts.append(f"\t\t(comment 2 \"{c2}\")")
            header_parts.append(f"\t\t(comment 3 \"{c3}\")")
            header_parts.append(f"\t\t(comment 4 \"{c4}\")")
    else:
        header_parts.append(f"\t\t(comment 1 \"{c1}\")")
        header_parts.append(f"\t\t(comment 2 \"{c2}\")")
        header_parts.append(f"\t\t(comment 3 \"{c3}\")")
        header_parts.append(f"\t\t(comment 4 \"{c4}\")")
    # close title_block and continue
    header_parts.append("\t)")
    header_parts.append("\t(lib_symbols)")

    parts = list(header_parts)
    bom_kicad = None

    separate_bom = False
    # honor force flags from meta if present (meta takes precedence)
    try:
        if isinstance(meta.get("force_inline_bom"), bool):
            force_inline_bom = bool(meta.get("force_inline_bom"))
        if isinstance(meta.get("force_split_bom"), bool):
            force_split_bom = bool(meta.get("force_split_bom"))
    except Exception:
        pass
    # sheet physical sizes in mm (width x height) and margin defaults
    sheet_sizes = {
        "A3": (420.0, 297.0),
        "A4": (297.0, 210.0),
    }
    page_w, page_h = sheet_sizes.get(sheet_size, (420.0, 297.0))
    # Allow overriding margin via meta['margin_mm'] (from global config)
    try:
        margin = float(meta.get("margin_mm", 10.0)) if meta.get("margin_mm") is not None else 10.0
    except Exception:
        margin = 10.0
    if image_b64:
        # Determine image scale to fit the selected sheet size. If the image
        # would occupy too much of the page, move the BOM to a separate page.
        img_uuid = str(uuid.uuid4())
        # default placement (these could be made configurable)
        # we'll position the image top-left inside the margin
        img_x = None
        img_y = None

        # sheet physical sizes in mm (width x height)
        sheet_sizes = {
            "A3": (420.0, 297.0),
            "A4": (297.0, 210.0),
        }
        page_w, page_h = sheet_sizes.get(sheet_size, (420.0, 297.0))
        # usable area with margins
        # Allow overriding margin via meta['margin_mm'] (from global config)
        try:
            margin = float(meta.get("margin_mm", 10.0)) if meta.get("margin_mm") is not None else 10.0
        except Exception:
            margin = 10.0
        usable_w = page_w - 2 * margin
        # reserve some space for title block (approx)
        title_block_h = 25.0
        usable_h = page_h - margin - title_block_h

        # get image pixel size and estimate mm using DPI (default 96)
        img_px_w = img_px_h = None
        try:
            png_path = Path(meta.get("png")) if meta.get("png") else None
            if png_path and png_path.exists():
                img_px_w, img_px_h = wz_encoder.png_size(png_path)
        except Exception:
            img_px_w = img_px_h = None

        dpi = float(meta.get("dpi", 96)) if meta.get("dpi") else 96.0
        mm_per_px = 25.4 / dpi

        # fallback defaults
        img_scale = 1.0
        try:
            if img_px_w and img_px_h:
                img_mm_w = img_px_w * mm_per_px
                img_mm_h = img_px_h * mm_per_px
                # compute scale to fit into usable area
                scale_w = usable_w / img_mm_w if img_mm_w > 0 else 1.0
                scale_h = usable_h / img_mm_h if img_mm_h > 0 else 1.0
                # Prefer filling the usable page width (upscale allowed).
                # If the resulting height exceeds the usable height the BOM
                # will normally be moved to a separate file/page. This behaviour
                # can be controlled with `meta['bom_threshold']`:
                # - numeric >0: use as fraction of usable_h (e.g. 0.8)
                # - 0 or False: disable splitting and always keep BOM in same file
                target_scale = scale_w
                img_scale = round(target_scale, 6)
                # Determine threshold behaviour from meta
                raw_thr = meta.get("bom_threshold")
                threshold_disabled = False
                threshold_value = 0.8
                try:
                    if raw_thr is None:
                        threshold_value = 0.8
                    elif isinstance(raw_thr, (int, float)):
                        if float(raw_thr) <= 0:
                            threshold_disabled = True
                        else:
                            threshold_value = float(raw_thr)
                    else:
                        # attempt to coerce string values like "0.75"
                        val = float(str(raw_thr))
                        if val <= 0:
                            threshold_disabled = True
                        else:
                            threshold_value = val
                except Exception:
                    threshold_value = 0.8

                if not threshold_disabled:
                    if img_mm_h * img_scale > usable_h * threshold_value:
                        separate_bom = True
                # allow max_image_scale to cap scaling
                try:
                    # prefer explicit param, fall back to meta
                    if max_image_scale is None and meta.get("max_image_scale") is not None:
                        max_image_scale = float(meta.get("max_image_scale"))
                except Exception:
                    max_image_scale = None
                if max_image_scale and img_scale > float(max_image_scale):
                    img_scale = float(max_image_scale)
        except Exception:
            img_scale = 1.0

        # compute position based on alignment
        if img_px_w and img_px_h:
            if image_align == "top-left":
                img_x = margin + (img_mm_w * img_scale) / 2.0
                img_y = margin + (img_mm_h * img_scale) / 2.0
            elif image_align == "center":
                img_x = page_w / 2.0
                img_y = (page_h - title_block_h) / 2.0
            else:  # fit-width or any unknown -> default behavior
                img_x = margin + (img_mm_w * img_scale) / 2.0
                img_y = margin + (img_mm_h * img_scale) / 2.0
        parts.append("\t(image")
        # if we failed to compute positions above, fall back to defaults
        if img_x is None:
            img_x = 148.59
        if img_y is None:
            img_y = 85.09
        parts.append(f"\t\t(at {round(img_x,2)} {round(img_y,2)})")
        parts.append(f"\t\t(scale {img_scale})")
        parts.append(f"\t\t(uuid \"{img_uuid}\")")
        # Put base64 data as multiple quoted lines (KiCad-style)
        # split into 76-char chunks and format as:
        #   (data "chunk0"
        #     "chunk1"
        #     "chunk2"
        #   )
        chunk_size = 76
        chunks = [image_b64[i : i + chunk_size] for i in range(0, len(image_b64), chunk_size)]
        if chunks:
            parts.append(f'\t\t(data "{chunks[0]}"')
            for c in chunks[1:]:
                parts.append(f"\t\t\t\"{c}\"")
            parts.append("\t\t)")
        parts.append("\t)")

    bom_table_block = None
    if meta.get("bom"):
        try:
            bom_path = Path(meta.get("bom"))
            # compute default bottom-left placement for BOM
            # small offsets inside margin
            # position BOM inside computed margins (small inset)
            bom_start_x = margin + 2.0
            bom_start_y = page_h - margin - 2.0
            bom_table_block = _build_kicad_table(bom_path, start_x=bom_start_x, start_y=bom_start_y)
            # (No inline text rendering for BOM; keep table-only output)
        except Exception:
            bom_table_block = "(bom (note \"BOM rendering failed\"))"
            bom_text_block = None

    # Determine final BOM placement considering force flags
    if force_inline_bom:
        # force keeping BOM inline
        if bom_table_block and include_bom:
            parts.append(bom_table_block)
            # no-op: inline text block removed
    elif force_split_bom:
        # force split: do not append to main
        pass
    else:
        # default behaviour when not forced
        if bom_table_block and not separate_bom and include_bom:
            parts.append(bom_table_block)
            # no-op: inline text block removed

    # sheet instances and final flags for the main sheet
    parts.append("\t(sheet_instances")
    parts.append("\t\t(path \"/\"")
    parts.append("\t\t\t(page \"1\")")
    parts.append("\t\t)")
    parts.append("\t)")
    parts.append("\t(embedded_fonts no)")

    # close the top-level kicad_sch S-expression for the main sheet
    parts.append(")")
    main_kicad = "\n".join(parts)

    # Build a second BOM-only schematic file if needed
    if separate_bom and bom_table_block and include_bom:
        bom_parts = list(header_parts)
        # replace title with BOM indicator
        for i, p in enumerate(bom_parts):
            if p.startswith("\t\t(title "):
                bom_parts[i] = f"\t\t(title \"{title} - BOM\")"
                break
        bom_parts.append(bom_table_block)
        bom_parts.append("\t(sheet_instances")
        bom_parts.append("\t\t(path \"/\"")
        bom_parts.append("\t\t\t(page \"1\")")
        bom_parts.append("\t\t)")
        bom_parts.append("\t)")
        bom_parts.append("\t(embedded_fonts no)")
        bom_parts.append(")")
        bom_kicad = "\n".join(bom_parts)

    # Return a str subclass that is also iterable so callers can either
    # treat the result as a plain string or unpack it as (main, bom).
    class _SexpString(str):
        def __new__(cls, value, bom_value=None):
            obj = str.__new__(cls, value)
            obj._bom = bom_value
            return obj

        def __iter__(self):
            # allow unpacking: main, bom = result
            yield str(self)
            yield self._bom

        @property
        def bom(self):
            return self._bom

    return _SexpString(main_kicad, bom_kicad)


def _build_kicad_table(bom_path: Path, start_x: float = 49.53, start_y: float = 195.58) -> str:
    """Build a KiCad-like `(table ...)` S-expression from a TSV BOM.

    This will create column widths, row heights and individual `table_cell`
    entries for the header and each data row. It's an approximation of the
    native KiCad table structure (uuids, positions, font sizes) so KiCad will
    recognise it as a proper table block similar to `back.kicad_sch`.
    """
    # Read structured rows
    rows = []
    try:
        # Import the package BOM parser reliably from this package
        from . import bom as _bom
        rows = _bom.parse_bom_tsv(bom_path)
    except Exception:
        # Fallback: empty table (parsing failed)
        rows = []

    headers = list(rows[0].keys()) if rows else []

    # Header overrides for display label and fixed widths (mm)
    header_overrides = {
        "id": {"label": "ID", "width": 21.59},
    }

    # Simple sizing heuristics (chars -> mm) used as fallback
    char_mm = 1.27
    col_widths = []
    display_headers = []
    for h in headers:
        key = str(h).strip()
        low = key.lower()
        # apply override if present
        if low in header_overrides:
            disp = header_overrides[low]["label"]
            w = header_overrides[low]["width"]
        else:
            disp = key
            maxlen = len(key)
            for r in rows:
                maxlen = max(maxlen, len(str(r.get(h, ""))))
            w = round(maxlen * char_mm, 2)
        display_headers.append(disp)
        col_widths.append(w)

    # Row heights: header + rows
    row_height = 2.54
    row_heights = [row_height] * (1 + max(1, len(rows)))

    # Build table parts
    tbl = []
    tbl.append("\t(table")
    tbl.append(f"\t\t(column_count {len(headers)})")
    tbl.append("\t\t(border")
    tbl.append("\t\t\t(external yes)")
    tbl.append("\t\t\t(header yes)")
    tbl.append("\t\t\t(stroke")
    tbl.append("\t\t\t\t(width 0)")
    tbl.append("\t\t\t\t(type solid)")
    tbl.append("\t\t\t\t(color 0 0 0 1)")
    tbl.append("\t\t\t)")
    tbl.append("\t\t)")
    tbl.append("\t\t(separators")
    tbl.append("\t\t\t(rows yes)")
    tbl.append("\t\t\t(cols yes)")
    tbl.append("\t\t\t(stroke")
    tbl.append("\t\t\t\t(width 0)")
    tbl.append("\t\t\t\t(type solid)")
    tbl.append("\t\t\t\t(color 0 0 0 1)")
    tbl.append("\t\t\t)")
    tbl.append("\t\t)")

    # Column widths
    if col_widths:
        tbl.append("\t\t(column_widths " + " ".join(str(w) for w in col_widths) + ")")
    else:
        tbl.append("\t\t(column_widths)")

    # Row heights
    tbl.append("\t\t(row_heights " + " ".join(str(h) for h in row_heights) + ")")

    # Cells: header row first
    tbl.append("\t\t(cells")
    # starting coordinates are provided by caller (defaults approximate)
    x = start_x
    y = start_y

    def _cell_block(text, w, x_pos, y_pos):
        uid = str(uuid.uuid4())
        cb = []
        cb.append(f'\t\t\t(table_cell "{text}"')
        cb.append("\t\t\t\t(exclude_from_sim no)")
        cb.append(f"\t\t\t\t(at {round(x_pos,2)} {round(y_pos,2)} 0)")
        cb.append(f"\t\t\t\t(size {w} {row_height})")
        cb.append("\t\t\t\t(margins 0.9525 0.9525 0.9525 0.9525)")
        cb.append("\t\t\t\t(span 1 1)")
        cb.append("\t\t\t\t(fill")
        cb.append("\t\t\t\t\t(type none)")
        cb.append("\t\t\t\t)")
        cb.append("\t\t\t\t(effects")
        cb.append("\t\t\t\t\t(font")
        cb.append("\t\t\t\t\t\t(size 1.27 1.27)")
        cb.append("\t\t\t\t\t\t(color 0 0 0 1)")
        cb.append("\t\t\t\t\t)")
        cb.append("\t\t\t\t\t(justify left top)")
        cb.append("\t\t\t\t)")
        cb.append(f"\t\t\t\t(uuid \"{uid}\")")
        cb.append("\t\t\t)")
        return cb

    # Header cells (use display_headers for human-facing labels)
    for i, h in enumerate(display_headers):
        w = col_widths[i] if i < len(col_widths) else 20.0
        for line in _cell_block(h, w, x, y):
            tbl.append(line)
        x += w

    # Data rows
    y -= row_height
    for r in rows:
        x = start_x
        for i, h in enumerate(headers):
            val = str(r.get(h, ""))
            w = col_widths[i] if i < len(col_widths) else 20.0
            for line in _cell_block(val, w, x, y):
                tbl.append(line)
            x += w
        y -= row_height

    tbl.append("\t\t)")
    tbl.append("\t)")
    return "\n".join(tbl)
