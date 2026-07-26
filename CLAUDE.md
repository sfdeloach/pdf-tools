# CLAUDE.md

## Overview

`pdf-tools` is a collection of four standalone Python CLI scripts for PDF
manipulation. There is no shared package or entry point — each script is run
directly with `python <script>.py` and has its own `argparse` interface and
`main()`. Most tools deliberately strip PDF metadata from their output.

## Environment

Work inside the project virtualenv, and install the pinned dependencies:

```bash
source .venv/bin/activate       # create first with: python -m venv .venv
pip install -r requirements.txt
```

`pdf_ocr.py` additionally requires **system Tesseract OCR** (not a pip package):

- Arch: `yay -S tesseract`
- Ubuntu/Debian: `sudo apt-get install tesseract-ocr`

## The tools

| Script | Purpose | Key flags |
| --- | --- | --- |
| `pdf_ocr.py` | OCR an image-based PDF into a text file | `-o/--output` (default `converted.txt`), `--dpi` (default 300) |
| `combine.py` | Merge all PDFs in a dir (sorted by filename) into `combined.pdf` | positional `input_dir [output_dir]`, `--page-numbers` |
| `rasterize.py` | Batch-convert PDFs to grayscale, image-only (non-searchable) PDFs | `--noise {none,low,medium,high}`, `--dpi` (default 300), `--jpeg`, `--stdin`, `--stdout` |
| `securitize.py` | Apply security features to a single PDF | `--watermark`, `--footer`, `--password`, `--keywords`, `--stdin`, `--stdout` |

```bash
python pdf_ocr.py document.pdf -o output.txt --dpi 600
python combine.py input/ output/ --page-numbers
python rasterize.py input/ output/ --noise medium --dpi 150 --jpeg
python securitize.py in.pdf out.pdf --footer 0007 --keywords "..." --password secret
# pipe rasterize -> securitize (stream mode, one PDF, no intermediate file):
python rasterize.py input/ --stdout --noise medium | python securitize.py --stdin out.pdf --footer 0007
```

For batch tools (`combine.py`, `rasterize.py`), `output_dir` defaults to
`input_dir` when omitted.

**Stream mode (`rasterize.py` + `securitize.py`)**: the opt-in `--stdin` /
`--stdout` flags switch each tool to process a single PDF over stdin/stdout so
they can be piped together. Without the flags, both behave exactly as before.
In stream mode `rasterize.py` sends all progress/log output to stderr and writes
no `.log` file. `rasterize.py --stdout` from a directory requires exactly one PDF.

## Conventions & architecture notes

- **Standalone scripts** — no shared module; each has `main()` under
  `if __name__ == "__main__"`. There is **no test suite, build step, or linter**
  configured. Run scripts directly to verify changes.
- **Two PDF libraries, do not mix APIs**: `combine.py` and `rasterize.py` use
  **PyMuPDF** (`import fitz`); `securitize.py` uses **PyPDF2** + `reportlab`;
  `pdf_ocr.py` uses `pdf2image` + `pytesseract`. Match the existing library when
  editing a given script.
- **Metadata stripping is intentional.** `combine`, `rasterize`, and
  `securitize` clear document metadata (and XMP) on output by design;
  `securitize` re-adds only `--keywords` if requested.
- **Output naming**: `rasterize.py` appends a `timestamp-uuid` suffix to each
  output filename; `combine.py` always writes `combined.pdf`.
- **Logging**: `rasterize.py` and `combine.py` write a `.log` file into the
  output directory (`rasterize.log` / `combined.log`).
- **Working dirs** `input/`, `output/`, `temp/`, and `.venv/` are gitignored.

## Real-world workflow: annual detailed financial reports

Per the README, the recurring release process for `securitize.py`:

1. Update the *Detail Financial Requests Log* on Google Sheets and assign the
   next sequential request number.
2. Generate the report, then run `securitize.py`, updating `--footer` (the
   request number), `--keywords`, and the output filename. Example:

```bash
python securitize.py --footer 0007 --keywords "prepared for Jackie Husebo" \
  --password m2gZai2x "2025 detailed financials report.pdf" \
  ./releases/2025_0007_details.pdf
```
