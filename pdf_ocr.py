#!/usr/bin/env python3
"""
PDF OCR Text Extractor
Converts image-based PDFs to text using OCR.
"""

import argparse
import sys
from pathlib import Path

try:
    from pdf2image import convert_from_path
    from PIL import Image
    import pytesseract
except ImportError as e:
    print(f"Error: Missing required library - {e}")
    print("\nPlease install required packages:")
    print("  pip install pdf2image pillow pytesseract")
    print("\nYou also need to install Tesseract OCR:")
    print("  - Ubuntu/Debian: sudo apt-get install tesseract-ocr")
    print("  - macOS: brew install tesseract")
    print("  - Windows: Download from https://github.com/UB-Mannheim/tesseract/wiki")
    sys.exit(1)


def extract_text_from_pdf(pdf_path, output_path="converted.txt", dpi=300):
    """
    Extract text from an image-based PDF using OCR.
    
    Args:
        pdf_path: Path to the input PDF file
        output_path: Path for the output text file
        dpi: DPI resolution for PDF to image conversion (higher = better quality)
    """
    try:
        print(f"Converting PDF to images (DPI: {dpi})...")
        images = convert_from_path(pdf_path, dpi=dpi)
        
        print(f"Processing {len(images)} page(s) with OCR...")
        extracted_text = []
        
        for i, image in enumerate(images, 1):
            print(f"  Processing page {i}/{len(images)}...", end="\r")
            text = pytesseract.image_to_string(image)
            extracted_text.append(text)
        
        print(f"\nWriting text to {output_path}...")
        full_text = "\n\n--- Page Break ---\n\n".join(extracted_text)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(full_text)
        
        print(f"✓ Successfully extracted text to {output_path}")
        print(f"  Total characters: {len(full_text)}")
        
    except FileNotFoundError:
        print(f"Error: PDF file not found: {pdf_path}")
        sys.exit(1)
    except Exception as e:
        print(f"Error during OCR processing: {e}")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description="Extract text from image-based PDFs using OCR",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s document.pdf
  %(prog)s document.pdf -o output.txt
  %(prog)s document.pdf --dpi 600
        """
    )
    
    parser.add_argument(
        'pdf_file',
        help='Path to the input PDF file'
    )
    
    parser.add_argument(
        '-o', '--output',
        default='converted.txt',
        help='Output text file path (default: converted.txt)'
    )
    
    parser.add_argument(
        '--dpi',
        type=int,
        default=300,
        help='DPI for PDF to image conversion (default: 300, higher = better quality but slower)'
    )
    
    args = parser.parse_args()
    
    # Validate input file
    if not Path(args.pdf_file).exists():
        print(f"Error: File does not exist: {args.pdf_file}")
        sys.exit(1)
    
    if not args.pdf_file.lower().endswith('.pdf'):
        print("Warning: Input file does not have .pdf extension")
    
    # Run OCR extraction
    extract_text_from_pdf(args.pdf_file, args.output, args.dpi)


if __name__ == "__main__":
    main()