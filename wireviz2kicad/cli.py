"""CLI entrypoint for wireviz2kicad."""
from pathlib import Path
import typer
from . import parser as wz_parser
from . import encoder as wz_encoder
from . import schematic as wz_schematic
from . import config as wz_config

app = typer.Typer(help="Convert WireViz YAML + assets into a KiCad .kicad_sch sheet")


@app.command()
def convert(
    input: Path = typer.Argument(..., exists=True, help="Input WireViz YAML file"),
    output: Path = typer.Option(Path("output.kicad_sch"), help="Output KiCad schematic file"),
    sheet_size: str = typer.Option("A3", help="Sheet size template (A3/A4)"),
    no_bom: bool = typer.Option(False, help="Do not render BOM"),
    config: Path = typer.Option(None, help="Optional global config YAML file (.wireviz2kicad.yml)"),
    image_align: str = typer.Option("fit-width", help="Image alignment: top-left, center, fit-width"),
    max_image_scale: float = typer.Option(None, help="Maximum image scale to apply (decimal)"),
    force_inline_bom: bool = typer.Option(False, help="Force BOM to remain inline in same file"),
    force_split_bom: bool = typer.Option(False, help="Force BOM to be split into a separate file"),
    output_dir: Path = typer.Option(None, help="Optional output directory for generated files"),
):
    """Run conversion pipeline: parse -> encode -> schematic."""
    # load per-sheet metadata (catch parse errors to provide friendlier output)
    try:
        meta = wz_parser.parse_yaml(input)
    except ValueError as e:
        typer.secho(f"YAML parse error in {input}: {e}", fg="red", err=True)
        raise typer.Exit(code=1)

    # load global config: prefer explicit `--config`, then a sibling config
    # next to the input YAML, then fall back to auto-discovery in cwd.
    cfg_path = None
    if config:
        cfg_path = config
    else:
        sibling = input.parent / ".wireviz2kicad.yml"
        if sibling.exists():
            cfg_path = sibling
    global_cfg = wz_config.load_config(cfg_path) or {}

    # Merge global config into meta, but prefer non-empty sheet values.
    # This treats None or empty-string as "missing" so config can supply defaults.
    def _prefer_sheet_over_global(global_d: dict, sheet_d: dict) -> dict:
        out = dict(global_d or {})
        for k, v in (sheet_d or {}).items():
            # if the sheet provides a dict and global has a dict, merge recursively
            if isinstance(v, dict) and isinstance(out.get(k), dict):
                out[k] = _prefer_sheet_over_global(out.get(k, {}), v)
            else:
                # treat empty strings as missing
                if v is None:
                    continue
                if isinstance(v, str) and v.strip() == "":
                    continue
                out[k] = v
        return out

    meta = _prefer_sheet_over_global(global_cfg, meta)
    png_path = meta.get("png")
    if png_path:
        img_b64 = wz_encoder.png_to_base64(Path(png_path))
    else:
        img_b64 = None
    # When invoked programmatically the Typer Option object can be passed
    # directly; coerce to the actual default string if needed.
    if not isinstance(sheet_size, str) and hasattr(sheet_size, 'default'):
        sheet_size = sheet_size.default
    # Coerce `no_bom` Option objects to a real bool when called programmatically
    if not isinstance(no_bom, bool) and hasattr(no_bom, 'default'):
        no_bom = bool(no_bom.default)

    # read force flags from meta if present; CLI flags override config/meta
    try:
        cfg_force_inline = bool(meta.get("force_inline_bom")) if meta.get("force_inline_bom") is not None else False
    except Exception:
        cfg_force_inline = False
    try:
        cfg_force_split = bool(meta.get("force_split_bom")) if meta.get("force_split_bom") is not None else False
    except Exception:
        cfg_force_split = False

    result = wz_schematic.build_sheet(
        meta=meta,
        image_b64=img_b64,
        sheet_size=sheet_size,
        include_bom=(not bool(no_bom)),
        image_align=image_align or meta.get("image_align", "fit-width"),
        max_image_scale=(max_image_scale or meta.get("max_image_scale")),
        force_inline_bom=(force_inline_bom or cfg_force_inline),
        force_split_bom=(force_split_bom or cfg_force_split),
    )
    # build_sheet now may return (main_kicad, bom_kicad_or_None)
    if isinstance(result, tuple):
        main_kicad, bom_kicad = result
    else:
        main_kicad, bom_kicad = result, None

    # allow writing into a specific output directory
    if output_dir:
        output_dir.mkdir(parents=True, exist_ok=True)
        out_path = output_dir / output.name
    else:
        out_path = output

    out_path.write_text(main_kicad, encoding="utf-8")
    typer.echo(f"Wrote {out_path}")

    if bom_kicad:
        if output_dir:
            bom_path = output_dir / (out_path.stem + "_bom.kicad_sch")
        else:
            bom_path = out_path.with_name(out_path.stem + "_bom.kicad_sch")
        bom_path.write_text(bom_kicad, encoding="utf-8")
        typer.echo(f"Wrote {bom_path}")


if __name__ == "__main__":
    app()
