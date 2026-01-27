"""
pdf_oxide-based parser for Indonesian bank statement PDFs.

This implementation uses the pdf_oxide library for text extraction.
It is optimized for performance and multiprocessing safety.
"""

import re
from pathlib import Path
from typing import Any, Dict

from pdf_oxide import PdfDocument

from pdfparser.utils import extract_metadata, extract_summary_totals, extract_transactions


def preprocess_text(text: str) -> str:
    """
    Preprocess raw text from pdf_oxide to fix smashed fields.

    pdf_oxide often extracts text line-by-line without preserving layout,
    resulting in merged fields (e.g. "AmountAmount" or "UserAmount").
    This function uses regex to insert spaces or newlines where appropriate.

    Args:
        text: Raw extracted text

    Returns:
        Cleaned text with better field separation
    """
    if not text:
        return ""

    # Fix transaction lines

    # Split Date-Time from Description
    # 02/05/25 09:38:58 Transfer -> 02/05/25 09:38:58\nTransfer
    text = re.sub(r'(\d{2}:\d{2}:\d{2})\s+(?!AM|PM)', r'\1\n', text)

    # Split Amount-Amount (smashed)
    # Pattern: End of one amount (.00) followed immediately by start of next (digit/comma)
    # 0.0026,000.00 -> 0.00\n26,000.00
    # Run twice to handle chains of 3+ amounts (e.g., A.00B.00C.00) because regex consumes the overlap
    text = re.sub(r'(\.\d{2})([\d,]+\.\d{2})', r'\1\n\2', text)
    text = re.sub(r'(\.\d{2})([\d,]+\.\d{2})', r'\1\n\2', text)

    # Split Amount-Amount (space separated)
    # 0.00 26,000.00 -> 0.00\n26,000.00
    # Run twice to handle chains of 3+ amounts
    text = re.sub(r'([\d,]+\.\d{2})\s+([\d,]+\.\d{2})', r'\1\n\2', text)
    text = re.sub(r'([\d,]+\.\d{2})\s+([\d,]+\.\d{2})', r'\1\n\2', text)

    # Split User-Amount (smashed)
    # User ID is 6-8 digits, followed by amount
    # 88886280.00 -> 8888628\n0.00
    text = re.sub(r'(\d{6,8})([\d,]+\.\d{2})', r'\1\n\2', text)

    # Split Description-User (smashed)
    # ...BMRIIDJA8888628 -> ...BMRIIDJA\n8888628
    # User ID starts with digit. Only apply if followed by space (end of line or next field)
    # to avoid splitting inside description too aggressively.
    text = re.sub(r'([a-zA-Z])(\d{6,8})\s', r'\1\n\2 ', text)

    # Split Description-User (space separated)
    # Ensure User ID is on its own line if surrounded by spaces
    text = re.sub(r'\s+(\d{6,8})\s', r'\n\1\n', text)

    # Split Description-Amount (smashed)
    # Ends with letter, followed by Amount
    # ATM6,500.00 -> ATM\n6,500.00
    text = re.sub(r'([a-zA-Z])([\d,]+\.\d{2})', r'\1\n\2', text)

    # Split Description-Amount (space separated)
    # ATM 6,500.00 -> ATM\n6,500.00
    text = re.sub(r'([a-zA-Z])\s+([\d,]+\.\d{2})', r'\1\n\2', text)

    # Fix Metadata

    # Account No / Unit Kerja
    # No. Rekening : 109701000638306Unit KerjaKC Sibuhuan -> ...306\nUnit...
    text = re.sub(
        r'(No\.?\s*Rekening\s*:?\s*[0-9]*)(Unit\s+Kerja)',
        r'\1\n\2',
        text,
        flags=re.IGNORECASE,
    )

    # Product Name / Address
    # Nama Produk : ... Alamat Unit Kerja ...
    # Need non-greedy match for product name
    text = re.sub(
        r'(Nama\s+Produk\s*:\s*.*?)(Alamat\s+Unit\s+Kerja)',
        r'\1\n\2',
        text,
        flags=re.IGNORECASE,
    )

    # Valuta / Currency
    # Valuta: IDR Currency
    text = re.sub(
        r'(Valuta:?\s*[A-Z]{3})\s*(Currency)', r'\1\n\2', text, flags=re.IGNORECASE
    )

    return text


def parse_pdf_pdfoxide(path: str) -> Dict[str, Any]:
    """
    Parse Indonesian bank statement PDF using pdf_oxide.

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
        doc = PdfDocument(str(path))

        # Handle empty document
        page_count = doc.page_count()
        if page_count == 0:
            raise ValueError(f"PDF has no pages: {path}")

        # Extract metadata from first page
        header_text = doc.extract_text(0)  # type: ignore[attr-defined]
        header_text = header_text or ""
        header_text = preprocess_text(header_text)
        metadata = extract_metadata(header_text)

        # Fallback: extract account_no from filename if not found in text
        if not metadata.get("account_no"):
            import re

            acct_match = re.search(r"(\d{10,16})", path_obj.stem)
            if acct_match:
                metadata["account_no"] = acct_match.group(1)

        # Extract transactions from all pages
        all_text = ""
        for page_num in range(page_count):
            page_text = doc.extract_text(page_num)  # type: ignore[attr-defined] or ""
            all_text += page_text + "\n"

        all_text = preprocess_text(all_text)
        transactions = extract_transactions(all_text)

        # Extract summary totals and add to metadata
        summary = extract_summary_totals(all_text)
        if summary.get("total_debit"):
            metadata["total_debit"] = summary["total_debit"]
        if summary.get("total_credit"):
            metadata["total_credit"] = summary["total_credit"]
        if summary.get("opening_balance"):
            metadata["opening_balance"] = summary["opening_balance"]
        if summary.get("closing_balance"):
            metadata["closing_balance"] = summary["closing_balance"]

        return {"metadata": metadata, "transactions": transactions, "full_text": all_text}

    except FileNotFoundError:
        raise
    except ValueError:
        raise
    except Exception as e:
        raise RuntimeError(f"Failed to parse PDF with pdf_oxide: {path}") from e
