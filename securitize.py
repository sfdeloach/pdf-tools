import argparse
from PyPDF2 import PdfReader, PdfWriter, PageObject
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib.colors import Color
from io import BytesIO


def add_watermark_and_footer(page, watermark_text=None, footer_text=None):
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
    parser.add_argument("input_file", help="Path to the input PDF file")
    parser.add_argument("output_file", help="Path to the output PDF file")
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

    reader = PdfReader(args.input_file)
    writer = PdfWriter()

    for page_num in range(len(reader.pages)):
        page = reader.pages[page_num]
        modified_page = add_watermark_and_footer(page, args.watermark, args.footer)
        writer.add_page(modified_page)

    if args.keywords:
        writer.add_metadata({"/Keywords": args.keywords})

    if args.password:
        writer.encrypt(user_pwd=args.password, owner_pwd=None, use_128bit=True)

    with open(args.output_file, "wb") as output_pdf:
        writer.write(output_pdf)


if __name__ == "__main__":
    main()
