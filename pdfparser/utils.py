"""
Shared utilities for PDF bank statement parsing.

This module provides regex patterns and utility functions for extracting
metadata and transactions from Indonesian bank statements (Rekening Koran).
"""

import csv
import os
import re
from pathlib import Path
from typing import List, Dict, Optional

from dotenv import load_dotenv


def load_config() -> Dict[str, str]:
    """
    Load configuration from environment variables.

    Reads from .env file if present, otherwise uses defaults.
    Environment variables:
        - SOURCE_PDF_DIR: Directory containing source PDF files
        - OUTPUT_DIR: Directory for output CSV files
        - TEST_PDFS_DIR: Directory for test/benchmark PDF files

    Returns:
        Dict with keys: source_pdf_dir, output_dir, test_pdfs_dir
    """
    # Load .env file if it exists (silent if missing)
    load_dotenv()

    return {
        'source_pdf_dir': os.getenv('SOURCE_PDF_DIR', 'source-pdf'),
        'output_dir': os.getenv('OUTPUT_DIR', 'output'),
        'test_pdfs_dir': os.getenv('TEST_PDFS_DIR', 'test-pdfs')
    }


# Metadata extraction patterns (label-based)
# Metadata extraction patterns (handles multiline: label on one line, value on next)
ACCOUNT_NO_PATTERN = r'Account\s+No\s*:\s*\n?\s*([^\n]+)'
BUSINESS_UNIT_PATTERN = r'Business\s+Unit\s*:\s*\n?\s*([^\n]+)'
PRODUCT_NAME_PATTERN = r'Product\s+Name\s*:\s*\n?\s*([^\n]+)'
STATEMENT_DATE_PATTERN = r'Statement\s+Date\s*:\s*\n?\s*([^\n]+)'

# Transaction row pattern - date anchor (DD/MM/YY format, not YYYY)
TRANSACTION_DATE_PATTERN = r'^\d{2}/\d{2}/\d{2}\s+\d{2}:\d{2}:\d{2}'

# Full transaction line pattern - parses inline transaction rows
# Captures: date, description, user, debit (optional), credit (optional), balance
TRANSACTION_LINE_PATTERN = r'^(\d{2}/\d{2}/\d{2})\s+(.+?)\s+(\w+)\s+([\d,.]+)?\s+([\d,.]+)?\s+([\d,.]+)'


def extract_metadata(text: str) -> Dict[str, str]:
    """
    Extract metadata fields from bank statement text.

    Args:
        text: Full text extracted from PDF first page (header section)

    Returns:
        Dict containing keys: account_no, business_unit, product_name, statement_date
    """
    metadata = {}

    # Extract Account No
    account_match = re.search(ACCOUNT_NO_PATTERN, text, re.IGNORECASE)
    metadata['account_no'] = account_match.group(1).strip() if account_match else ''

    # Extract Business Unit
    business_match = re.search(BUSINESS_UNIT_PATTERN, text, re.IGNORECASE)
    metadata['business_unit'] = business_match.group(1).strip() if business_match else ''

    # Extract Product Name
    product_match = re.search(PRODUCT_NAME_PATTERN, text, re.IGNORECASE)
    metadata['product_name'] = product_match.group(1).strip() if product_match else ''

    # Extract Statement Date
    date_match = re.search(STATEMENT_DATE_PATTERN, text, re.IGNORECASE)
    metadata['statement_date'] = date_match.group(1).strip() if date_match else ''

    return metadata


def extract_transactions(text: str) -> List[Dict[str, str]]:
    """
    Extract transaction rows from bank statement text.

    Parses column-based transaction rows where each field is on a separate line:
    - Line 1: Date and time (DD/MM/YY HH:MM:SS)
    - Line 2: Description (may span multiple lines)
    - Line 3: User/Teller ID
    - Line 4: Debit amount (or empty)
    - Line 5: Credit amount (or empty)
    - Line 6: Balance

    Args:
        text: Full text extracted from all PDF pages (transaction table section)

    Returns:
        List of dicts with keys: date, description, user, debit, credit, balance
    """
    transactions = []
    lines = text.split('\n')
    i = 0

    while i < len(lines):
        line = lines[i].strip()

        # Skip empty lines
        if not line:
            i += 1
            continue

        # Check if line starts with date pattern (new transaction)
        if re.match(TRANSACTION_DATE_PATTERN, line):
            # Extract date from the line (may include time)
            date_match = re.match(r'^(\d{2}/\d{2}/\d{2})', line)
            if date_match:
                date = line  # Keep the full date+time string

                # Collect description lines until we hit numeric fields
                i += 1
                description_lines = []
                while i < len(lines):
                    next_line = lines[i].strip()
                    # Stop if we hit another transaction date
                    if re.match(TRANSACTION_DATE_PATTERN, next_line):
                        break
                    # Stop if we hit a numeric amount line (debit/credit/balance)
                    if re.match(r'^[\d,.]+\s*$', next_line):
                        break
                    if next_line:
                        description_lines.append(next_line)
                    i += 1
                description = ' '.join(description_lines)

                # Move to user line
                while i < len(lines) and not lines[i].strip():
                    i += 1
                user = lines[i].strip() if i < len(lines) else ''

                # Move to debit line
                i += 1
                while i < len(lines) and not lines[i].strip():
                    i += 1
                debit = lines[i].strip() if i < len(lines) else ''

                # Move to credit line
                i += 1
                while i < len(lines) and not lines[i].strip():
                    i += 1
                credit = lines[i].strip() if i < len(lines) else ''

                # Move to balance line
                i += 1
                while i < len(lines) and not lines[i].strip():
                    i += 1
                balance = lines[i].strip() if i < len(lines) else ''

                transaction = {
                    'date': date,
                    'description': description,
                    'user': user,
                    'debit': debit,
                    'credit': credit,
                    'balance': balance
                }
                transactions.append(transaction)
            else:
                i += 1
        else:
            i += 1

    return transactions


def save_metadata_csv(metadata: Dict[str, str], output_path: str) -> None:
    """
    Write metadata dict to CSV file with Field and Value columns.

    Args:
        metadata: Dict of metadata fields
        output_path: Path where CSV file will be written
    """
    with open(output_path, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(['Field', 'Value'])
        for field, value in metadata.items():
            writer.writerow([field, value])


def save_transactions_csv(transactions: List[Dict[str, str]], output_path: str) -> None:
    """
    Write transactions list to CSV file.

    Args:
        transactions: List of transaction dicts
        output_path: Path where CSV file will be written
    """
    if not transactions:
        # Write empty CSV with headers
        with open(output_path, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(['Date', 'Description', 'User', 'Debit', 'Credit', 'Balance'])
        return

    fieldnames = ['Date', 'Description', 'User', 'Debit', 'Credit', 'Balance']

    with open(output_path, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()

        for txn in transactions:
            writer.writerow({
                'Date': txn.get('date', ''),
                'Description': txn.get('description', ''),
                'User': txn.get('user', ''),
                'Debit': txn.get('debit', ''),
                'Credit': txn.get('credit', ''),
                'Balance': txn.get('balance', '')
            })


def is_valid_parse(metadata: Dict[str, str], transactions: List[Dict[str, str]]) -> bool:
    """
    Validate parsing success based on minimum data quality requirements.

    Args:
        metadata: Extracted metadata dict
        transactions: List of extracted transactions

    Returns:
        True if parse is valid, False otherwise
    """
    # Check metadata has at least 2 non-empty fields
    non_empty_fields = sum(1 for v in metadata.values() if v and v.strip())
    if non_empty_fields < 2:
        return False

    # Check transactions list has at least 1 entry
    if not transactions:
        return False

    # Check each transaction has date and balance fields
    for txn in transactions:
        if not txn.get('date') or not txn.get('balance'):
            return False

    return True


def ensure_output_dirs(config: Optional[Dict[str, str]] = None) -> None:
    """
    Ensure output directories exist. Creates them if missing.

    Args:
        config: Configuration dict from load_config(). If None, loads config automatically.
    """
    if config is None:
        config = load_config()

    output_dir = Path(config['output_dir'])
    (output_dir / 'metadata').mkdir(parents=True, exist_ok=True)
    (output_dir / 'transactions').mkdir(parents=True, exist_ok=True)
