"""
PyMuPDF-based parser for Indonesian bank statement PDFs.

This implementation uses the PyMuPDF (fitz) library for fast text extraction.
It is optimized for performance and multiprocessing safety.
"""

from pathlib import Path
from typing import Any, Dict

import fitz  # PyMuPDF

from pdfparser.utils import extract_metadata, extract_summary_totals, extract_transactions


def parse_pdf_pymupdf(path: str) -> Dict[str, Any]:
    """
    Parse Indonesian bank statement PDF using PyMuPDF.

    Extracts metadata from first page header and transactions from all pages.
    Uses regex patterns from utils module for parsing.

    Args:
        path: Path to PDF file (string or Path-like)

    Returns:
        Dict with keys:
            - 'metadata': Dict[str, str] with account_no, business_unit,
                         product_name, statement_date
            - 'transactions': List[Dict[str, str]] with date, description,
                             user, debit, credit, balance

    Raises:
        FileNotFoundError: If PDF file doesn't exist
        fitz.FileDataError: If PDF is corrupted or invalid
        Exception: For other PDF processing errors
    """
    # Convert to Path for validation
    path_obj = Path(path)

    # Validate file existence
    if not path_obj.exists():
        raise FileNotFoundError(f"PDF file not found: {path}")
    if not path_obj.is_file():
        raise FileNotFoundError(f"Path is not a file: {path}")

    doc = None
    try:
        # Open PDF document
        doc = fitz.open(str(path))

        # Handle empty document
        if len(doc) == 0:
            raise ValueError(f"PDF has no pages: {path}")

        # Extract metadata from first page
        first_page_text = doc[0].get_text()
        metadata = extract_metadata(first_page_text)

        # Fallback: extract account_no from filename if not found in text
        # Many Indonesian bank PDFs have account number in filename (e.g., 041901001548309)
        if not metadata.get('account_no'):
            import re
            # Match 10-16 digit number in filename, but not if it looks like part of date
            acct_match = re.search(r'(\d{10,16})', path_obj.stem)
            if acct_match:
                # Verify it's not a date-like pattern (e.g., 2024-01-15)
                potential_acct = acct_match.group(1)
                if not re.match(r'^\d{4}-\d{2}-\d{2}$', potential_acct):
                    metadata['account_no'] = potential_acct

        # Extract transactions from all pages
        all_text = ""
        for page_num in range(len(doc)):
            page_text = doc[page_num].get_text()
            all_text += page_text + "\n"
        transactions = extract_transactions(all_text)

        # Extract summary totals and add to metadata
        summary = extract_summary_totals(all_text)
        if summary.get('total_debit'):
            metadata['total_debit'] = summary['total_debit']
        if summary.get('total_credit'):
            metadata['total_credit'] = summary['total_credit']
        if summary.get('opening_balance'):
            metadata['opening_balance'] = summary['opening_balance']
        if summary.get('closing_balance'):
            metadata['closing_balance'] = summary['closing_balance']

        return {
            'metadata': metadata,
            'transactions': transactions,
            'full_text': all_text
        }

    except FileNotFoundError:
        raise
    except fitz.FileDataError as e:
        raise ValueError(f"Corrupted PDF: {path}") from e
    except Exception as e:
        raise RuntimeError(f"Failed to parse PDF: {path}") from e
    finally:
        if doc is not None:
            doc.close()
