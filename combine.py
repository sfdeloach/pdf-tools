import fitz  # PyMuPDF
import os
import sys
import logging
from tqdm import tqdm


def merge_pdfs(input_dir, output_pdf, output_dir=None):
    """
    Merge all PDF files in a directory into a single PDF, sorted by filename,
    with metadata stripped.

    Args:
        input_dir (str): Path to directory containing input PDF files.
        output_pdf (str): Name of the output PDF file (e.g., "merged.pdf").
        output_dir (str, optional): Path to output directory. Defaults to input_dir.

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
    if len(sys.argv) < 2 or len(sys.argv) > 3:
        print("Usage: python combine.py <input_dir> [<output_dir>]")
        sys.exit(1)

    input_dir = sys.argv[1]
    output_dir = sys.argv[2] if len(sys.argv) == 3 else sys.argv[1]
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
    success, message = merge_pdfs(input_dir, output_pdf, output_dir)
    print(message)


if __name__ == "__main__":
    main()
