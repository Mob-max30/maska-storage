import os
import fitz  # PyMuPDF


class PDFParser:
    """
    PDFParser

    Responsible for:
    - Opening PDF documents
    - Extracting text from every page
    - Returning structured data

    This module does NOT perform:
    - Text cleaning
    - Chunking
    - Embedding generation
    - Summarization
    - Metadata generation
    """

    def parse(self, pdf_path: str) -> dict:
        """
        Extracts text from a PDF document.

        Args:
            pdf_path (str): Path to the PDF file.

        Returns:
            dict: Structured PDF content containing
                  filename, page count and extracted text.
        """

        try:
            # Check if file exists
            if not os.path.isfile(pdf_path):
                raise FileNotFoundError(f"PDF not found: {pdf_path}")

            # Verify extension
            if not pdf_path.lower().endswith(".pdf"):
                raise ValueError("Provided file is not a PDF.")

            document = fitz.open(pdf_path)

            extracted_text = []

            for page in document:
                extracted_text.append(page.get_text())

            document.close()

            return {
                "filename": os.path.basename(pdf_path),
                "page_count": len(extracted_text),
                "text": "\n".join(extracted_text)
            }

        except FileNotFoundError as e:
            raise FileNotFoundError(e)

        except ValueError as e:
            raise ValueError(e)

        except Exception as e:
            raise RuntimeError(f"PDF Parsing Error: {e}")