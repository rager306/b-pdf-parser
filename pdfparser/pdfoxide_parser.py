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

# Compiled regex patterns for preprocessing
_SMASHED_AMOUNT_PATTERN = re.compile(r"(\.\d{2})(\d)")
_SMASHED_TEXT_NUM_PATTERN = re.compile(r"([a-zA-Z])(\d)")
_SMASHED_HEADER_PATTERN = re.compile(r"([a-z])([A-Z])")
_SMASHED_COLON_PATTERN = re.compile(r"(:)([^0-9\s])")
_DATE_NEWLINE_PATTERN = re.compile(r"(\d{2}/\d{2}/\d{2}\s+\d{1,2}:\d{2}:\d{2})\s+")
_USER_ID_NEWLINE_PATTERN = re.compile(r"\s+(\d{6,8})\s+")
_AMOUNT_NEWLINE_PATTERN = re.compile(r"\s+([\d,.]+\.\d{2})\b")

# Metadata labels for newline insertion
_METADATA_LABELS = [
    "Unit Kerja",
    "Business Unit",
    "Nama Produk",
    "Product Name",
    "Alamat Unit Kerja",
    "Business Unit Address",
    "Valuta",
    "Currency",
    "Tanggal Laporan",
    "Statement Date",
    "Periode Transaksi",
    "Transaction Period",
    "No. Rekening",
    "Account No",
]
# Sort by length desc to match longest first
_METADATA_LABELS.sort(key=len, reverse=True)
_METADATA_LABEL_PATTERN = re.compile(
    r"(?i)(?<!\n)\b(" + "|".join(map(re.escape, _METADATA_LABELS)) + r")\b"
)


def preprocess_text(text: str) -> str:
    """
    Preprocess raw text from pdf_oxide to fix layout and spacing issues.

    pdf_oxide often smashes text columns together and misses newlines.
    This function inserts spaces and newlines to reconstruct structure
    expected by regex patterns.

    Args:
        text: Raw extracted text

    Returns:
        Cleaned text with better layout
    """
    if not text:
        return ""

    # 1. Fix amounts smashed together (e.g. 0.001,000,000.00)
    text = _SMASHED_AMOUNT_PATTERN.sub(r"\1 \2", text)

    # 2. Fix text smashed with numbers (e.g. ATM2,500.00, BRImo8888049)
    text = _SMASHED_TEXT_NUM_PATTERN.sub(r"\1 \2", text)

    # 3. Fix smashed headers (CamelCase)
    text = _SMASHED_HEADER_PATTERN.sub(r"\1 \2", text)

    # 4. Fix smashed colons (but preserve time like 09:38)
    text = _SMASHED_COLON_PATTERN.sub(r"\1 \2", text)

    # 5. Insert newlines before known metadata labels
    text = _METADATA_LABEL_PATTERN.sub(r"\n\1", text)

    # 6. Reconstruct transaction table structure
    # Insert newline after date (and time)
    text = _DATE_NEWLINE_PATTERN.sub(r"\1\n", text)

    # Insert newline before User ID (8888...)
    text = _USER_ID_NEWLINE_PATTERN.sub(r"\n\1\n", text)

    # Insert newline before amounts (at end of lines/transactions)
    text = _AMOUNT_NEWLINE_PATTERN.sub(r"\n\1", text)

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
            all_text += preprocess_text(page_text) + "\n"
        transactions = extract_transactions(all_text)

        # Extract summary totals and add to metadata
        # Note: preprocess_text might have shifted summary labels to new lines, which is good
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
