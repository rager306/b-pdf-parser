"""
pypdf-based parser for Indonesian bank statement PDFs.

This implementation uses the pure Python pypdf library for text extraction.
It is optimized for portability and multiprocessing safety.
"""

from pathlib import Path
from typing import Any, Dict

from pypdf import PdfReader
from pypdf.errors import PdfReadError

from pdfparser.utils import extract_metadata, extract_summary_totals, extract_transactions


def parse_pdf_pypdf(path: str) -> Dict[str, Any]:
    """
    Parse Indonesian bank statement PDF using pypdf.

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
        ValueError: If PDF is corrupted, invalid, or has no pages
        RuntimeError: For other PDF processing errors
    """
    # Convert to Path for validation
    path_obj = Path(path)

    # Validate file existence
    if not path_obj.exists():
        raise FileNotFoundError(f"PDF file not found: {path}")
    if not path_obj.is_file():
        raise FileNotFoundError(f"Path is not a file: {path}")

    try:
        # Open PDF document
        reader = PdfReader(str(path))

        # Handle empty document
        if len(reader.pages) == 0:
            raise ValueError(f"PDF has no pages: {path}")

        # Extract metadata from first page
        header_text = reader.pages[0].extract_text()
        header_text = header_text or ""
        metadata = extract_metadata(header_text)

        # Fallback: extract account_no from filename if not found in text
        if not metadata.get('account_no'):
            import re
            acct_match = re.search(r'(\d{10,16})', path_obj.stem)
            if acct_match:
                metadata['account_no'] = acct_match.group(1)

        # Extract transactions from all pages
        all_text = ""
        for page in reader.pages:
            page_text = page.extract_text() or ""
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
    except PdfReadError as e:
        raise ValueError(f"Corrupted or invalid PDF: {path}") from e
    except Exception as e:
        raise RuntimeError(f"Failed to parse PDF with pypdf: {path}") from e
