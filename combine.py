import fitz  # PyMuPDF
import os
import sys
import logging
import argparse
from tqdm import tqdm


def add_page_numbers(doc):
    """
    Add page numbers to each page of the PDF.
    Odd pages: bottom right corner
    Even pages: bottom left corner
    Position: 0.5 inches (36 points) from bottom and side

    Args:
        doc (fitz.Document): The PDF document to add page numbers to.
    """
    for page_num in range(len(doc)):
        page = doc[page_num]
        page_number = page_num + 1  # Start numbering at 1

        # Get page dimensions
        rect = page.rect

        # Calculate position (0.5 inch = 36 points)
        margin_bottom = 36
        margin_side = 36
        font_size = 12

        # Determine position based on odd/even page
        text = str(page_number)

        # Calculate text width to adjust position for right-aligned text
        text_width = fitz.get_text_length(text, fontname="times-roman", fontsize=font_size)

        if page_number % 2 == 1:  # Odd pages: bottom right
            x_position = rect.width - margin_side - text_width
        else:  # Even pages: bottom left
            x_position = margin_side

        y_position = rect.height - margin_bottom

        # Insert text with serif font (Times-Roman)
        page.insert_text(
            (x_position, y_position),
            text,
            fontname="times-roman",
            fontsize=font_size,
            color=(0, 0, 0),  # Black color
            render_mode=0
        )


def merge_pdfs(input_dir, output_pdf, output_dir=None, add_page_nums=False):
    """
    Merge all PDF files in a directory into a single PDF, sorted by filename,
    with metadata stripped.

    Args:
        input_dir (str): Path to directory containing input PDF files.
        output_pdf (str): Name of the output PDF file (e.g., "merged.pdf").
        output_dir (str, optional): Path to output directory. Defaults to input_dir.
        add_page_nums (bool, optional): Whether to add page numbers. Defaults to False.

    Returns:
        tuple: (success: bool, message: str)
    """
    try:
        # Validate input directory
        if not os.path.isdir(input_dir):
            return False, f"Error: {input_dir} is not a valid directory"

        # Get list of PDF files, sorted by filename (case-insensitive)
        pdf_files = sorted(
            [f for f in os.listdir(input_dir) if f.lower().endswith(".pdf")],
            key=lambda x: x.lower(),
        )
        if not pdf_files:
            return False, f"No PDF files found in {input_dir}"

        # Set output path
        output_dir = output_dir or input_dir
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        output_path = os.path.join(output_dir, output_pdf)

        # Create a new empty PDF
        new_doc = fitz.open()

        # Merge PDFs with progress bar
        for file in tqdm(pdf_files, desc="Merging PDFs"):
            input_path = os.path.join(input_dir, file)
            try:
                # Open input PDF
                doc = fitz.open(input_path)
                # Insert all pages from input PDF
                new_doc.insert_pdf(doc)
                doc.close()
            except Exception as e:
                logging.error(f"Failed to merge {input_path}: {str(e)}")
                continue  # Skip problematic files

        # Check if any pages were added
        if new_doc.page_count == 0:
            new_doc.close()
            return False, "No valid PDFs were merged"

        # Strip all metadata
        new_doc.set_metadata({})
        new_doc.del_xml_metadata()

        # Add page numbers if requested
        if add_page_nums:
            add_page_numbers(new_doc)

        # Save the merged PDF
        new_doc.save(output_path, garbage=4, deflate=True)
        new_doc.close()
        return True, f"Successfully created merged PDF: {output_path}"

    except Exception as e:
        return False, f"Error: {str(e)}"


def main():
    """
    Merge all PDFs in a directory into a single PDF, sorted by filename.
    """
    parser = argparse.ArgumentParser(
        description="Merge all PDF files in a directory into a single PDF."
    )
    parser.add_argument(
        "input_dir",
        help="Path to directory containing input PDF files"
    )
    parser.add_argument(
        "output_dir",
        nargs="?",
        help="Path to output directory (defaults to input_dir)"
    )
    parser.add_argument(
        "--page-numbers",
        action="store_true",
        help="Add page numbers to the merged PDF (odd pages: bottom right, even pages: bottom left)"
    )

    args = parser.parse_args()

    input_dir = args.input_dir
    output_dir = args.output_dir if args.output_dir else args.input_dir
    output_pdf = "combined.pdf"  # Default output filename

    # Set up logging
    output_log_dir = output_dir or input_dir
    if not os.path.exists(output_log_dir):
        os.makedirs(output_log_dir)
    logging.basicConfig(
        filename=os.path.join(output_log_dir, "combined.log"),
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
    )

    # Merge PDFs
    success, message = merge_pdfs(input_dir, output_pdf, output_dir, args.page_numbers)
    print(message)


if __name__ == "__main__":
    main()
