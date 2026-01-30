# pdf-tools

```bash
python pdf_ocr.py [-h] [-o OUTPUT] [--dpi DPI] pdf_file
python combine.py <input_dir> [<output_dir>]                # without page numbers
python combine.py <input_dir> [<output_dir>] --page-numbers # with page numbers
python rasterize.py <input_dir> [<output_dir>] [--jpeg]
python securitize.py [-h] [--watermark WATERMARK] [--password PASSWORD] [--footer FOOTER] [--keywords KEYWORDS] input_file output_file
```

## Installation

First, create a virtual Python environment (if it does not already exist):

```bash
$ python -m venv .venv              # run module venv and create hidden folder .venv
$ source .venv/bin/activate         # activate virtual environment
```

...and install the required packages:

```bash
$ pip install -r requirements.txt
```

Remember to deactivate the virtual environment when finished:

```bash
$ deactivate
```

You also need Tesseract OCR installed on your system:
- **Arch Linux**: `yay -S tesseract`
- **Ubuntu/Debian**: `sudo apt-get install tesseract-ocr`

## Usage for pdf_ocr

Basic usage (creates `converted.txt` by default):

```bash
$ python pdf_ocr.py document.pdf
```

Specify output file:

```bash
python pdf_ocr.py document.pdf -o output.txt
```

Increase quality (higher DPI, slower processing):

```bash
python pdf_ocr.py document.pdf --dpi 600
```

### pdf_ocr features

- Converts each PDF page to an image and runs OCR on it
- Supports multi-page PDFs
- Progress indicator shows which page is being processed
- Adjustable DPI for quality/speed trade-off
- Adds page break markers between pages
- Error handling with helpful messages

The program uses **pytesseract** (Python wrapper for Tesseract OCR) and **pdf2image** to handle the conversion process.

## Annual detailed financial reports

- update 'Detail Financial Requests Log' on Google Sheets
- assign sequential request number
- generate the report with request number and metadata
- update the `--footer`, `--keywords`, and output file on the command, for example:

```bash
$ python ~/workspace/pdf-tools/securitize.py --footer 0007 --keywords "prepared for Jackie Husebo" --password m2gZai2x "2025 detailed financials report.pdf" ./releases/2025_0007_details.pdf
```

