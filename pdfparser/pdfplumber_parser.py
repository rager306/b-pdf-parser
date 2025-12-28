"""
pdfplumber-based parser for Indonesian bank statement PDFs.

This implementation uses pdfplumber library for structured table extraction.
It attempts table extraction first, falls back to text-based parsing.
Optimized for accuracy on tabular data and multiprocessing safety.
"""

import pdfplumber
import re
from typing import Dict, List, Any
from pathlib import Path

from pdfparser.utils import (
    extract_transactions,
    TRANSACTION_DATE_PATTERN,
    TRANSACTION_LINE_PATTERN
)


# Alternative metadata patterns for Indonesian bank statement labels
ACCOUNT_NO_PATTERN_ID = r'No\.\s*Rekening\s*:\s*([^\n]+)'
BUSINESS_UNIT_PATTERN_ID = r'Unit\s*Kerja\s*:\s*([^\n]+)'
PRODUCT_NAME_PATTERN_ID = r'Nama\s*Produk\s*:\s*([^\n]+)'
STATEMENT_DATE_PATTERN_ID = r'Tanggal\s*Laporan\s*:\s*([^\n]+)'


def extract_metadata_pdfplumber(text: str) -> Dict[str, str]:
    """
    Extract metadata from pdfplumber text output (handles Indonesian labels).

    Args:
        text: Full text extracted from PDF first page

    Returns:
        Dict containing keys: account_no, business_unit, product_name, statement_date
    """
    metadata = {}

    # Try Indonesian patterns first
    account_match = re.search(ACCOUNT_NO_PATTERN_ID, text, re.IGNORECASE)
    if account_match:
        metadata['account_no'] = account_match.group(1).strip()
    else:
        metadata['account_no'] = ''

    business_match = re.search(BUSINESS_UNIT_PATTERN_ID, text, re.IGNORECASE)
    if business_match:
        metadata['business_unit'] = business_match.group(1).strip()
    else:
        metadata['business_unit'] = ''

    product_match = re.search(PRODUCT_NAME_PATTERN_ID, text, re.IGNORECASE)
    if product_match:
        metadata['product_name'] = product_match.group(1).strip()
    else:
        metadata['product_name'] = ''

    date_match = re.search(STATEMENT_DATE_PATTERN_ID, text, re.IGNORECASE)
    if date_match:
        metadata['statement_date'] = date_match.group(1).strip()
    else:
        metadata['statement_date'] = ''

    return metadata


def extract_transactions_inline(text: str) -> List[Dict[str, str]]:
    """
    Extract transactions from inline text format (all fields on one line).

    Uses TRANSACTION_LINE_PATTERN to parse transaction rows where:
    - Date: DD/MM/YY HH:MM:SS
    - Description: free text (may contain spaces)
    - User: alphanumeric ID
    - Debit: optional amount
    - Credit: optional amount
    - Balance: amount

    Args:
        text: Full text extracted from PDF pages

    Returns:
        List of dicts with keys: date, description, user, debit, credit, balance
    """
    transactions = []
    lines = text.split('\n')

    for line in lines:
        line = line.strip()
        if not line:
            continue

        # Skip header lines
        if 'Tanggal Transaksi' in line or 'Transaction Date' in line:
            continue
        if 'Uraian Transaksi' in line or 'Transaction Description' in line:
            continue
        if 'Teller' in line or 'User ID' in line:
            continue
        if 'Debet' in line or 'Debit' in line:
            continue
        if 'Kredit' in line or 'Credit' in line:
            continue
        if 'Saldo' in line or 'Balance' in line:
            continue
        if 'Total Transaksi' in line or 'Opening Balance' in line:
            continue

        # Try to match inline transaction pattern
        match = re.match(TRANSACTION_LINE_PATTERN, line)
        if match:
            date, description, user, debit, credit, balance = match.groups()
            transactions.append({
                'date': date.strip(),
                'description': description.strip(),
                'user': user.strip(),
                'debit': debit.strip() if debit else '',
                'credit': credit.strip() if credit else '',
                'balance': balance.strip()
            })

    return transactions


def _parse_table_to_transactions(tables: List[List[List[str]]]) -> List[Dict[str, str]]:
    """
    Convert pdfplumber extracted tables to transaction dicts.

    Args:
        tables: List of tables from pdfplumber.extract_tables()

    Returns:
        List of transaction dicts
    """
    transactions = []
    for table in tables:
        if not table or len(table) < 2:  # Need header + at least 1 data row
            continue

        # Skip header row (index 0), process data rows
        for row in table[1:]:
            if len(row) >= 6:  # Ensure row has all columns
                # Clean None values
                row = [cell or "" for cell in row]

                # Validate date format
                if re.match(TRANSACTION_DATE_PATTERN, row[0]):
                    transaction = {
                        'date': row[0].strip(),
                        'description': row[1].strip(),
                        'user': row[2].strip(),
                        'debit': row[3].strip(),
                        'credit': row[4].strip(),
                        'balance': row[5].strip()
                    }
                    transactions.append(transaction)

    return transactions


def parse_pdf_pdfplumber(path: str) -> Dict[str, Any]:
    """
    Parse Indonesian bank statement PDF using pdfplumber.

    Extracts metadata from first page header and transactions from all pages.
    Attempts table extraction first, falls back to text-based parsing.
    Uses regex patterns from utils module for text parsing.

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
        pdfplumber.PDFSyntaxError: If PDF is corrupted or invalid
        Exception: For other PDF processing errors
    """
    # Validate file existence
    path_obj = Path(path)
    if not path_obj.exists():
        raise FileNotFoundError(f"PDF file not found: {path}")
    if not path_obj.is_file():
        raise FileNotFoundError(f"Path is not a file: {path}")

    try:
        with pdfplumber.open(str(path)) as pdf:
            # Validation
            if len(pdf.pages) == 0:
                raise ValueError(f"PDF has no pages: {path}")

            # Extract metadata using pdfplumber-specific patterns
            first_page_text = pdf.pages[0].extract_text() or ""
            metadata = extract_metadata_pdfplumber(first_page_text)

            # Try table extraction first
            transactions = []
            all_tables = []
            for page in pdf.pages:
                tables = page.extract_tables()
                if tables:
                    all_tables.extend(tables)

            if all_tables:
                transactions = _parse_table_to_transactions(all_tables)

            # Fallback to text extraction if no tables found
            if not transactions:
                all_text = ""
                for page in pdf.pages:
                    page_text = page.extract_text() or ""
                    all_text += page_text + "\n"
                # Try inline text parsing first (pdfplumber format)
                transactions = extract_transactions_inline(all_text)
                # Fall back to column-based parsing if inline fails
                if not transactions:
                    transactions = extract_transactions(all_text)

            return {
                'metadata': metadata,
                'transactions': transactions
            }

    except FileNotFoundError:
        raise
    except Exception as e:
        raise RuntimeError(f"Failed to parse PDF with pdfplumber: {path}") from e
