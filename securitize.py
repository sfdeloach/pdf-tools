import argparse
import sys
from PyPDF2 import PdfReader, PdfWriter, PageObject
from PyPDF2.generic import NameObject
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib.colors import Color
from io import BytesIO


def add_watermark_and_footer(page, watermark_text=None, footer_text=None):
    # Nothing to overlay: return the page unchanged. Drawing nothing on the
    # canvas would produce a 0-page overlay PDF, which then fails on pages[0].
    if not watermark_text and not footer_text:
        return page

    # Create a new PDF with ReportLab for overlay
    packet = BytesIO()
    can = canvas.Canvas(packet, pagesize=letter)

    # Get page dimensions from the original page
    page_width = float(page.mediabox.width)
    page_height = float(page.mediabox.height)
    can.setPageSize((page_width, page_height))

    # Add watermark: semi-transparent diagonal text
    if watermark_text:
        can.saveState()
        can.setFillColor(Color(0.8, 0.8, 0.8, alpha=0.3))  # Light gray, 30% opacity
        can.setFont("Times-Roman", 100)
        can.rotate(45)
        can.drawString(page_width / 4, -page_height / 4, watermark_text)
        can.restoreState()

    # Add footer text in bottom right if provided
    if footer_text:
        can.saveState()
        # can.setFillColor(Color(0, 0, 0, alpha=1))  # Black text
        can.setFillColor(Color(0.8, 0.8, 0.8, alpha=0.3))  # Light gray, 30% opacity
        can.setFont("Times-Roman", 10)
        can.drawRightString(
            page_width - 20, 20, footer_text
        )  # 20 units from bottom-right
        can.restoreState()

    can.save()
    packet.seek(0)

    # Create overlay PDF
    overlay_pdf = PdfReader(packet)
    overlay_page = overlay_pdf.pages[0]

    # Merge overlay with original page
    page.merge_page(overlay_page)
    return page


def main():
    parser = argparse.ArgumentParser(
        description="Apply security features to a PDF file."
    )
    parser.add_argument(
        "input_file",
        nargs="?",
        help="Path to the input PDF file (omit when using --stdin)",
    )
    parser.add_argument(
        "output_file",
        nargs="?",
        help="Path to the output PDF file (omit when using --stdout)",
    )
    parser.add_argument(
        "--stdin",
        action="store_true",
        help="Read the input PDF from standard input instead of input_file",
    )
    parser.add_argument(
        "--stdout",
        action="store_true",
        help="Write the output PDF to standard output instead of output_file",
    )
    parser.add_argument(
        "--watermark",
        default=None,
        help="Optional watermark message",
    )
    parser.add_argument(
        "--password", default=None, help="Optional password to encrypt the PDF"
    )
    parser.add_argument(
        "--footer",
        default=None,
        help="Optional text code for bottom right corner of each page",
    )
    parser.add_argument(
        "--keywords",
        default=None,
        help="Optional keywords metadata (comma-separated)",
    )

    args = parser.parse_args()

    # With --stdin the input comes from the stream, so a lone positional is meant
    # as the OUTPUT path. argparse binds it to input_file (the first positional)
    # by default, so re-map it here to keep the CLI natural.
    if (
        args.stdin
        and not args.stdout
        and args.output_file is None
        and args.input_file is not None
    ):
        args.input_file, args.output_file = None, args.input_file

    # Validate that a source and destination are specified (path or stream).
    if not args.stdin and not args.input_file:
        parser.error("input_file is required unless --stdin is used")
    if not args.stdout and not args.output_file:
        parser.error("output_file is required unless --stdout is used")

    # Resolve the input: a stream from stdin or a file path.
    if args.stdin:
        reader = PdfReader(BytesIO(sys.stdin.buffer.read()))
    else:
        reader = PdfReader(args.input_file)
    writer = PdfWriter()

    for page_num in range(len(reader.pages)):
        page = reader.pages[page_num]
        modified_page = add_watermark_and_footer(page, args.watermark, args.footer)
        writer.add_page(modified_page)

    # Strip all inherited metadata so the output is clean.
    # (a) Clear the document-info dictionary (/Author, /Title, /Subject, ...).
    writer.add_metadata({})
    # (b) Defensively remove any page-level XMP / private metadata streams.
    #     Catalog-level XMP is already dropped because we build a fresh writer
    #     and copy only pages; this covers the rarer page-level case.
    for page in writer.pages:
        for key in ("/Metadata", "/PieceInfo"):
            if NameObject(key) in page:
                del page[NameObject(key)]

    # Re-add only the metadata the user explicitly requested.
    if args.keywords:
        writer.add_metadata({"/Keywords": args.keywords})

    if args.password:
        writer.encrypt(user_pwd=args.password, owner_pwd=None, use_128bit=True)

    # Resolve the output: a stream to stdout or a file path.
    if args.stdout:
        writer.write(sys.stdout.buffer)
    else:
        with open(args.output_file, "wb") as output_pdf:
            writer.write(output_pdf)


if __name__ == "__main__":
    main()
