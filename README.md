# pdf-tools

A collection of four standalone Python command-line tools for manipulating PDFs.
Each tool is run directly (`python <script>.py`) and has its own flags — there is
no shared entry point. Most tools strip document metadata from their output by
design.

## Table of contents

- [Installation](#installation)
- [Tools at a glance](#tools-at-a-glance)
- [`pdf_ocr.py`](#pdf_ocrpy)
- [`combine.py`](#combinepy)
- [`rasterize.py`](#rasterizepy)
- [`securitize.py`](#securitizepy)
- [Piping rasterize into securitize](#piping-rasterize-into-securitize)
- [Annual detailed financial reports](#annual-detailed-financial-reports)

## Installation

First, create a virtual Python environment (if it does not already exist):

```bash
python -m venv .venv              # run module venv and create hidden folder .venv
source .venv/bin/activate         # activate virtual environment
```

...and install the required packages:

```bash
pip install -r requirements.txt
```

Remember to deactivate the virtual environment when finished:

```bash
deactivate
```

Only `pdf_ocr.py` additionally requires **system Tesseract OCR** (not a pip
package):

- **Arch Linux**: `yay -S tesseract`
- **Ubuntu/Debian**: `sudo apt-get install tesseract-ocr`

## Tools at a glance

| Script | Purpose | Output |
| --- | --- | --- |
| [`pdf_ocr.py`](#pdf_ocrpy) | OCR an image-based PDF into extractable text | a `.txt` file (default `converted.txt`) |
| [`combine.py`](#combinepy) | Merge all PDFs in a directory (sorted by filename) | `combined.pdf` |
| [`rasterize.py`](#rasterizepy) | Convert PDFs to grayscale, image-only (non-searchable) PDFs | one image-only PDF per input |
| [`securitize.py`](#securitizepy) | Apply watermark / footer / password / keywords to one PDF | a single secured PDF |

## `pdf_ocr.py`

Extract text from an **image-based** PDF using OCR, writing the result to a text
file. Pages are separated in the output with `--- Page Break ---` markers.

```bash
python pdf_ocr.py [-h] [-o OUTPUT] [--dpi DPI] pdf_file
```

Basic usage (creates `converted.txt` by default):

```bash
python pdf_ocr.py document.pdf
```

Specify the output file:

```bash
python pdf_ocr.py document.pdf -o output.txt
```

Increase quality (higher DPI, slower processing):

```bash
python pdf_ocr.py document.pdf --dpi 600
```

### Features

- Converts each PDF page to an image and runs OCR on it
- Supports multi-page PDFs
- Progress indicator shows which page is being processed
- Adjustable DPI for a quality/speed trade-off (default: 300)
- Adds page-break markers between pages
- Error handling with helpful messages

Requires **system Tesseract OCR** (see [Installation](#installation)). The program
uses **pytesseract** (a Python wrapper for Tesseract) and **pdf2image** to handle
the conversion.

## `combine.py`

Merge every PDF in a directory into a single `combined.pdf`, sorted by filename
(case-insensitive), with all metadata stripped. A `combined.log` is written to the
output directory.

```bash
python combine.py <input_dir> [<output_dir>] [--page-numbers]
```

Merge all PDFs in `input/` into `output/combined.pdf`:

```bash
python combine.py input/ output/
```

Add page numbers to the merged document (odd pages: bottom-right, even pages:
bottom-left):

```bash
python combine.py input/ output/ --page-numbers
```

If `output_dir` is omitted it defaults to `input_dir`.

## `rasterize.py`

Batch-convert every PDF in a directory into a grayscale, image-only PDF with all
metadata stripped. Because each page is rasterized to an image, the output has no
text layer — the text **cannot be selected, copied, or searched**. Each output
file gets a unique `timestamp-uuid` suffix, and a `rasterize.log` is written to
the output directory.

```bash
python rasterize.py [-h] [--stdin] [--stdout] [--noise {none,low,medium,high}] [--dpi DPI] [--jpeg] [<input_dir>] [<output_dir>]
```

Clean copy (the default — no noise):

```bash
python rasterize.py input/ output/
```

Add anti-OCR noise to further resist text extraction. `--noise` accepts presets
`none` (default), `low`, `medium`, or `high`:

```bash
python rasterize.py input/ output/ --noise medium
```

Control resolution and compression:

```bash
python rasterize.py input/ output/ --dpi 150 --jpeg
```

If `output_dir` is omitted it defaults to `input_dir`. The `--stdin`/`--stdout`
flags enable stream mode — see
[Piping rasterize into securitize](#piping-rasterize-into-securitize). See
`python rasterize.py -h` for all options.

## `securitize.py`

Apply security features to a **single** PDF: a diagonal watermark, a bottom-right
footer code, password encryption, and/or keywords metadata. All other metadata is
stripped; only `--keywords` is re-added when supplied.

```bash
python securitize.py [-h] [--stdin] [--stdout] [--watermark WATERMARK] [--password PASSWORD] [--footer FOOTER] [--keywords KEYWORDS] [input_file] [output_file]
```

Add a footer code and encrypt with a password:

```bash
python securitize.py in.pdf out.pdf --footer 0007 --password secret
```

Apply a watermark and attach keywords:

```bash
python securitize.py in.pdf out.pdf --watermark "CONFIDENTIAL" --keywords "prepared for John Doe"
```

All flags are optional and can be combined. The `--stdin`/`--stdout` flags enable
stream mode — see
[Piping rasterize into securitize](#piping-rasterize-into-securitize).

## Piping rasterize into securitize

Both `rasterize.py` and `securitize.py` support a stream mode so they can be
chained in a Unix pipe, avoiding intermediate files. Stream mode is opt-in and
processes exactly one PDF:

- `--stdin` reads a single input PDF from standard input.
- `--stdout` writes a single output PDF to standard output.

Without these flags, both tools behave exactly as documented above
(directory-batch for `rasterize.py`, file-to-file for `securitize.py`). In stream
mode all progress and log output is sent to stderr so it never corrupts the piped
PDF.

Rasterize a single-PDF directory and pipe it straight into securitize:

```bash
python rasterize.py input/ --stdout --noise medium \
  | python securitize.py --stdin --footer 0007 releases/out.pdf
```

Fully streamed on both ends (no files touched until the final redirect):

```bash
python rasterize.py --stdin --stdout --noise low < in.pdf \
  | python securitize.py --stdin --stdout --footer 0007 > out.pdf
```

Note: `rasterize.py --stdout` reading from a directory requires that directory to
contain exactly one PDF (a single stream cannot carry a batch).

## Annual detailed financial reports

- update 'Detail Financial Requests Log' on Google Sheets
- assign sequential request number
- generate the report with request number and metadata
- update the `--footer`, `--keywords`, and output file on the command, for example:

```bash
$ python ~/workspace/pdf-tools/securitize.py --footer 0007 --keywords "prepared for John Doe" --password m2gZai2x "2025 detailed financials report.pdf" ./releases/2025_0007_details.pdf
```
