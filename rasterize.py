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

        # Save the new PDF
        new_doc.save(output_pdf, garbage=4, deflate=True)
        new_doc.close()
        doc.close()
        return True, f"Successfully created: {output_pdf}"

    except Exception as e:
        logging.error(f"Failed to process {input_pdf}: {str(e)}")
        return False, f"Error processing {input_pdf}: {str(e)}"


def main():
    """
    Batch process PDFs in a directory, converting them to grayscale, non-searchable PDFs.
    """
    if len(sys.argv) < 2 or len(sys.argv) > 4:
        print("Usage: python rasterize.py <input_dir> [<output_dir>] [--jpeg]")
        sys.exit(1)

    input_dir = sys.argv[1]
    output_dir = sys.argv[2] if len(sys.argv) >= 3 else input_dir
    use_jpeg = "--jpeg" in sys.argv

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
            input_path, output_path, dpi=100, noise_level=0, use_jpeg=use_jpeg
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
