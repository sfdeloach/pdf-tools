import argparse
import fitz  # PyMuPDF
import io
import numpy
import os
from PIL import Image
import re
import sys
import time
import uuid
from tqdm import tqdm  # For progress bar
import logging


# Named noise presets mapped to Gaussian std-dev values.
# "none" (the default) produces a clean copy: an image-only PDF with no added noise.
NOISE_LEVELS = {"none": 0, "low": 8, "medium": 15, "high": 25}


def add_noise_to_image(pix, noise_level=0):
    """
    Add random pixel noise to a PyMuPDF Pixmap in grayscale.

    Args:
        pix (fitz.Pixmap): The Pixmap object from PyMuPDF (in grayscale).
        noise_level (float): Standard deviation of Gaussian noise (higher = more noise).

    Returns:
        PIL.Image: The grayscale image with added random pixel noise.
    """
    # Ensure Pixmap is in grayscale colorspace
    if pix.n != 1:  # If not grayscale (e.g., RGB or CMYK), convert to grayscale
        pix = fitz.Pixmap(fitz.csGRAY, pix)

    # Create PIL Image from Pixmap's samples (grayscale mode "L")
    img = Image.frombytes("L", (pix.width, pix.height), pix.samples)

    # Convert image to NumPy array for manipulation
    img_array = numpy.array(img, dtype=numpy.float32)

    # Generate random Gaussian noise for grayscale (single channel)
    noise = numpy.random.normal(0, noise_level, img_array.shape)

    # Add noise and clip to valid grayscale range (0–255)
    img_array = numpy.clip(img_array + noise, 0, 255).astype(numpy.uint8)

    # Convert back to PIL Image
    return Image.fromarray(img_array)


def rasterize_document(doc, dpi=300, noise_level=0, use_jpeg=False):
    """
    Rasterize an open PDF document into a new grayscale, image-only PDF with
    optional random pixel noise, stripping all metadata.

    This is the I/O-agnostic core shared by the path-based batch mode and the
    stdin/stdout stream mode: it takes an already-open input document and
    returns the freshly built output document (caller is responsible for
    persisting and closing both).

    Args:
        doc (fitz.Document): Open input document.
        dpi (int): Resolution for rendering pages (higher = better quality, larger file).
        noise_level (float): Standard deviation of Gaussian noise (higher = more noise).
        use_jpeg (bool): Use JPEG compression instead of PNG for smaller files.

    Returns:
        fitz.Document: The new image-only document (open; caller must close it).
    """
    # Create a new empty PDF
    new_doc: fitz.Document = fitz.open()

    for page in doc:
        # Render the page as a grayscale high-resolution image (pixmap)
        pix: fitz.Pixmap = page.get_pixmap(dpi=dpi, colorspace=fitz.csGRAY)

        # Add noise to the image
        img = add_noise_to_image(pix, noise_level)

        # Convert PIL Image back to bytes for PyMuPDF
        img_bytes = io.BytesIO()
        if use_jpeg:
            img.save(img_bytes, format="JPEG", quality=85)
        else:
            img.save(img_bytes, format="PNG")
        img_data = img_bytes.getvalue()

        # Create a new page in the output PDF with the same dimensions
        new_page: fitz.Page = new_doc.new_page(
            width=page.rect.width, height=page.rect.height
        )

        # Insert the noised grayscale image onto the new page
        new_page.insert_image(new_page.rect, stream=img_data)

    # Strip all metadata from the output PDF
    new_doc.set_metadata({})
    new_doc.del_xml_metadata()  # Remove XMP metadata if present

    return new_doc


def stream_to_image_pdf(input_data, dpi=300, noise_level=0, use_jpeg=False):
    """
    Rasterize a PDF given as raw bytes and return the result as raw bytes.

    Used by stream mode (--stdin/--stdout) so the tool can participate in a
    Unix pipe. Metadata is stripped, matching the path-based batch mode.

    Args:
        input_data (bytes): Raw bytes of the input PDF.

    Returns:
        bytes: Raw bytes of the rasterized, image-only output PDF.
    """
    doc: fitz.Document = fitz.open(stream=input_data, filetype="pdf")
    new_doc = rasterize_document(doc, dpi, noise_level, use_jpeg)
    out_bytes = new_doc.tobytes(garbage=4, deflate=True)
    new_doc.close()
    doc.close()
    return out_bytes


def text_to_image_pdf(input_pdf, output_pdf, dpi=300, noise_level=0, use_jpeg=False):
    """
    Convert a text-based PDF to a grayscale image-based PDF with random pixel noise,
    stripping all metadata.

    Args:
        input_pdf (str): Path to input PDF file.
        output_pdf (str): Path to output PDF file.
        dpi (int): Resolution for rendering pages (higher = better quality, larger file).
        noise_level (float): Standard deviation of Gaussian noise (higher = more noise).
        use_jpeg (bool): Use JPEG compression instead of PNG for smaller files.
    """
    try:
        # Open the input PDF
        doc: fitz.Document = fitz.open(input_pdf)
        new_doc = rasterize_document(doc, dpi, noise_level, use_jpeg)

        # Save the new PDF
        new_doc.save(output_pdf, garbage=4, deflate=True)
        new_doc.close()
        doc.close()
        return True, f"Successfully created: {output_pdf}"

    except Exception as e:
        logging.error(f"Failed to process {input_pdf}: {str(e)}")
        return False, f"Error processing {input_pdf}: {str(e)}"


def run_stream_mode(args, noise_level, use_jpeg):
    """
    Process exactly one PDF for pipe use (--stdin / --stdout).

    Input is a single PDF (from stdin, or the lone PDF in the input directory)
    and output is a single PDF (to stdout, or one generated file in the output
    directory). All human-readable messages and logging go to stderr so they
    never corrupt the PDF byte stream written to stdout.
    """
    # Route logging to stderr; no .log file is written in stream mode.
    logging.basicConfig(
        stream=sys.stderr,
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
    )

    # Resolve the single input PDF as raw bytes.
    if args.stdin:
        input_data = sys.stdin.buffer.read()
        source_name = "<stdin>"
    else:
        # --stdout only: read the lone PDF from the input directory.
        if not args.input_dir or not os.path.isdir(args.input_dir):
            print(f"Error: {args.input_dir!r} is not a valid directory", file=sys.stderr)
            sys.exit(1)
        pdf_files = sorted(
            f for f in os.listdir(args.input_dir) if f.lower().endswith(".pdf")
        )
        if len(pdf_files) != 1:
            print(
                f"Error: --stdout requires exactly one input PDF, but found "
                f"{len(pdf_files)} in {args.input_dir}",
                file=sys.stderr,
            )
            sys.exit(1)
        source_name = os.path.join(args.input_dir, pdf_files[0])
        with open(source_name, "rb") as fh:
            input_data = fh.read()

    # Rasterize the single document.
    try:
        out_bytes = stream_to_image_pdf(
            input_data, dpi=args.dpi, noise_level=noise_level, use_jpeg=use_jpeg
        )
    except Exception as e:
        logging.error(f"Failed to process {source_name}: {str(e)}")
        print(f"Error processing {source_name}: {str(e)}", file=sys.stderr)
        sys.exit(1)

    # Resolve the output destination.
    if args.stdout:
        sys.stdout.buffer.write(out_bytes)
        sys.stdout.buffer.flush()
    else:
        # --stdin only: write one generated file into the output directory.
        output_dir = args.output_dir
        if not output_dir:
            print(
                "Error: an output directory is required with --stdin unless "
                "--stdout is used",
                file=sys.stderr,
            )
            sys.exit(1)
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        elif not os.path.isdir(output_dir):
            print(f"Error: {output_dir} is not a valid directory", file=sys.stderr)
            sys.exit(1)
        suffix = f"{int(time.time())}-{str(uuid.uuid4())[:8]}"
        output_path = os.path.join(output_dir, f"stream_{suffix}.pdf")
        with open(output_path, "wb") as fh:
            fh.write(out_bytes)
        print(f"Successfully created: {output_path}", file=sys.stderr)


def main():
    """
    Batch process PDFs in a directory, converting them to grayscale, non-searchable PDFs.
    """
    parser = argparse.ArgumentParser(
        description=(
            "Convert text-based PDFs into grayscale, image-only PDFs whose text "
            "cannot be copied or searched, stripping all metadata."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s input/                          Clean copy (no noise) into input/
  %(prog)s input/ output/                  Clean copy into output/
  %(prog)s input/ output/ --noise medium   Add moderate anti-OCR noise
  %(prog)s input/ output/ --noise high --dpi 150 --jpeg
  %(prog)s input/ --stdout --noise medium | python securitize.py --stdin out.pdf

A clean copy is the default: pages are rasterized to images, so the text is not
selectable. The --noise presets add Gaussian pixel noise to further resist OCR.

Stream mode (--stdin / --stdout) processes exactly one PDF, letting rasterize
participate in a Unix pipe (e.g. rasterize | securitize).
        """,
    )
    parser.add_argument(
        "input_dir",
        nargs="?",
        help="Path to directory containing input PDF files (omit when using --stdin)",
    )
    parser.add_argument(
        "output_dir",
        nargs="?",
        help="Path to output directory (defaults to input_dir; ignored with --stdout)",
    )
    parser.add_argument(
        "--stdin",
        action="store_true",
        help="Read a single input PDF from standard input instead of a directory",
    )
    parser.add_argument(
        "--stdout",
        action="store_true",
        help="Write a single output PDF to standard output instead of a directory",
    )
    parser.add_argument(
        "--noise",
        choices=list(NOISE_LEVELS),
        default="none",
        help="Amount of anti-OCR noise to add (default: none = clean copy)",
    )
    parser.add_argument(
        "--dpi",
        type=int,
        default=300,
        help="Rendering resolution; higher = better quality, larger files (default: 300)",
    )
    parser.add_argument(
        "--jpeg",
        action="store_true",
        help="Use JPEG compression instead of PNG for smaller files",
    )

    args = parser.parse_args()

    # With --stdin the input comes from the stream, so a lone positional is meant
    # as the OUTPUT directory. argparse binds it to input_dir (the first
    # positional) by default, so re-map it here to keep the CLI natural.
    if (
        args.stdin
        and not args.stdout
        and args.output_dir is None
        and args.input_dir is not None
    ):
        args.input_dir, args.output_dir = None, args.input_dir

    use_jpeg = args.jpeg
    noise_level = NOISE_LEVELS[args.noise]

    # Stream mode: participate in a Unix pipe via --stdin / --stdout. Entered
    # whenever either flag is set; processes exactly one PDF and returns.
    if args.stdin or args.stdout:
        run_stream_mode(args, noise_level, use_jpeg)
        return

    # --- Batch (directory) mode below: behavior unchanged ---
    if not args.input_dir:
        parser.error("input_dir is required unless --stdin or --stdout is used")

    input_dir = args.input_dir
    output_dir = args.output_dir if args.output_dir else args.input_dir

    # Validate directories
    if not os.path.isdir(input_dir):
        print(f"Error: {input_dir} is not a valid directory")
        sys.exit(1)
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    elif not os.path.isdir(output_dir):
        print(f"Error: {output_dir} is not a valid directory")
        sys.exit(1)

    # Set up logging
    logging.basicConfig(
        filename=os.path.join(output_dir, "rasterize.log"),
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
    )

    # Get list of PDF files
    pdf_files = [f for f in os.listdir(input_dir) if f.lower().endswith(".pdf")]
    if not pdf_files:
        print(f"No PDF files found in {input_dir}")
        sys.exit(1)

    # Process PDFs with progress bar
    failed_files = []
    for file in tqdm(pdf_files, desc="Processing PDFs"):
        input_path = os.path.join(input_dir, file)

        # Extract prefix or use filename base
        prefix_match = re.findall(r"\d+_\d+", file)
        prefix = prefix_match[0] if prefix_match else os.path.splitext(file)[0]

        # Use timestamp + UUID for unique suffix
        suffix = f"{int(time.time())}-{str(uuid.uuid4())[:8]}"
        output_filename = f"{prefix}_{suffix}.pdf"
        output_path = os.path.join(output_dir, output_filename)

        # Process the PDF
        success, message = text_to_image_pdf(
            input_path,
            output_path,
            dpi=args.dpi,
            noise_level=noise_level,
            use_jpeg=use_jpeg,
        )
        print(message)
        if not success:
            failed_files.append(file)

    # Report summary
    if failed_files:
        print(
            f"\nFailed to process {len(failed_files)} file(s): {', '.join(failed_files)}"
        )
        print(f"See {os.path.join(output_dir, 'rasterize.log')} for details")
    else:
        print("\nAll files processed successfully")


if __name__ == "__main__":
    main()
