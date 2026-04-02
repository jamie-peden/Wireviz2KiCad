# Wireviz2KiCad

**WireViz → KiCad converter**

Converts a WireViz YAML file, plus PNG and BOM assets, into a KiCad schematic sheet (`.kicad_sch`). The output embeds your wiring diagram, populates the title block, and renders a native KiCad BOM table — all from a single command.


---

## Features

- Embeds PNG diagrams as base64 inside the schematic
- Populates a KiCad `title_block` from WireViz metadata (PN, authors, company)
- Renders the BOM as a native KiCad `(table ...)` S-expression block
- Configurable layout via `.wireviz2kicad.yml` or CLI flags
- Lightweight title block template support using Python format strings

---

## Prerequisites

- WireViz: you must run your WireViz export workflow first so a PNG (diagram image)
  is available alongside the sheet YAML. The converter embeds that PNG into the
  generated KiCad schematic. If your WireViz step does not produce a PNG, run
  it first and place the PNG next to the YAML file (same stem name).
  Example (WireViz CLI, generates PNG):

```powershell
wireviz .\examples\example_loom.yml -f pt
```
- KiCad 9+: the generated `.kicad_sch` targets KiCad 9+ style S-expressions —
  use KiCad version 9 or later to open the files reliably.

## Requirements

- Python 3.11+
- PyYAML
- Typer
- Pillow

---

## Install

```bash
git clone https://github.com/jamie-peden/Wireviz2KiCad.git
cd Wireviz2KiCad
pip install -r requirements.txt
```

---

## Quickstart

```bash
python -m wireviz2kicad.cli examples/example_loom.yml --output out.kicad_sch
```

Write outputs to a folder:

```bash
python -m wireviz2kicad.cli examples/example_loom.yml --output out.kicad_sch --output-dir generated
```

---

## CLI Options

| Flag | Config key | Description |
|---|---|---|
| `--image-align` | `image_align` | Diagram placement: `top-left`, `center`, `fit-width` (default) |
| `--max-image-scale` | `max_image_scale` | Numeric cap for computed image scale, e.g. `0.8` |
| `--force-inline-bom` | `force_inline_bom` | Keep BOM inside the same `.kicad_sch` file |
| `--force-split-bom` | `force_split_bom` | Force BOM into a separate `_bom.kicad_sch` file |
| `--output-dir` | `output_dir` | Write outputs to this directory |
| `--config` | | Path to a specific config file |

### Examples

Keep the BOM inline and cap the image scale:

```bash
python -m wireviz2kicad.cli examples/example_loom.yml \
  --output out.kicad_sch \
  --force-inline-bom \
  --max-image-scale 0.9
```

Write to a build directory with a centred image:

```bash
python -m wireviz2kicad.cli examples/example_loom.yml \
  --output out.kicad_sch \
  --output-dir build \
  --image-align center
```

---

## Configuration

Global defaults live in `.wireviz2kicad.yml` at the repo root:

```yaml
title_block:
  title: "Default Project Title"
  company: "Acme"

dpi: 300
margin_mm: 8
bom_threshold: 0.75
image_align: fit-width
max_image_scale: 1.0
force_inline_bom: false
force_split_bom: false
output_dir: generated
```

---

## Title Block Templates

Add a `title_block_template` key to your sheet YAML (top-level or under `metadata`). The template is a Python format string.

**Available placeholders:**

`{pn}`, `{part_number}`, `{engineer}`, `{checked}`, `{approved}`, `{title}`, `{company}`, `{date}`, `{rev}`

**Example:**

```yaml
title_block_template: |
  (comment 1 "{pn}")
  (comment 2 "{engineer}")
  (comment 3 "{checked}")
  (comment 4 "{approved}")
```

The converter renders the template and inserts the resulting lines inside the generated `(title_block ...)` S-expression. Missing placeholders become empty strings.

---

## Tests

Run the unit tests with:

```bash
python -m unittest discover -v
```

`pytest` will also discover these tests automatically if you prefer it.

---

## Contributing

Open issues and PRs are welcome.

---
