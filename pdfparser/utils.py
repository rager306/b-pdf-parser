"""
Shared utilities for PDF bank statement parsing.

This module provides regex patterns and utility functions for extracting
metadata and transactions from Indonesian bank statements (Rekening Koran).
"""

import csv
import os
import re
from functools import lru_cache
from pathlib import Path
from typing import Dict, List, Optional, Pattern

from dotenv import load_dotenv

# =============================================================================
# COMPILED REGEX PATTERNS - Pre-compiled at module level for performance
# =============================================================================

# Metadata extraction patterns (label-based)
# Format varies: either "Label:\nValue" or "Label\nLabel\n:\nValue"
ACCOUNT_NO_PATTERN: Pattern = re.compile(
    r'No\.?\s*Rekening\s*\n(?:Account\s+No\s*\n)?\s*:?\s*([0-9]+)',
    re.IGNORECASE
)
BUSINESS_UNIT_PATTERN: Pattern = re.compile(
    r'(?:Unit\s+Kerja\s*\n)?Business\s+Unit\s*\n\s*:\s*\n\s*([^\n]+)',
    re.IGNORECASE
)
PRODUCT_NAME_PATTERN: Pattern = re.compile(
    r'(?:Nama\s+Produk\s*\n)?Product\s+Name\s*[:\s]*([A-Za-z0-9]+(?:\s+[A-Za-z0-9]+)*(?:\.[A-Za-z]+)?)',
    re.IGNORECASE
)
STATEMENT_DATE_PATTERN: Pattern = re.compile(
    r'Statement\s+Date\s*[:\s]*([^\n]+)',
    re.IGNORECASE
)
VALUTA_PATTERN: Pattern = re.compile(
    r'(?:Valuta|Currency)\s*\n(?:Currency|Valuta)?\s*\n\s*:?\s*([A-Z]{3})',
    re.IGNORECASE
)
TRANSACTION_PERIOD_PATTERN: Pattern = re.compile(
    r'(?:Periode\s+Transaksi|Transaction\s+Period)\s*\n(?:Transaction\s+Periode|Transaction\s+Period)?\s*\n\s*:\s*\n\s*([^\n]+)',
    re.IGNORECASE
)
UNIT_ADDRESS_PATTERN: Pattern = re.compile(
    r'(?:Alamat\s+Unit\s+Kerja|Business\s+Unit\s+Address)\s*\n\s*:\s*\n\s*([A-Za-z][^\n]*(?:\s+[A-Za-z][^\n]*)?)',
    re.IGNORECASE
)

# Transaction row pattern - date anchor (DD/MM/YY format, not YYYY)
TRANSACTION_DATE_PATTERN: Pattern = re.compile(r'^\d{2}/\d{2}/\d{2}\s+\d{2}:\d{2}:\d{2}')

# Full transaction line pattern - parses inline transaction rows
# Captures: date, description, user, debit (optional), credit (optional), balance
TRANSACTION_LINE_PATTERN: Pattern = re.compile(
    r'^(\d{2}/\d{2}/\d{2})\s+(.+?)\s+(\w+)\s+([\d,.]+)?\s+([\d,.]+)?\s+([\d,.]+)'
)

# Summary total patterns for turnover verification
# Matches Indonesian format: thousands separator '.', decimal separator ','
TOTAL_TRANSaksi_DEBET_PATTERN: Pattern = re.compile(
    r'Total\s+Transaksi\s+Debet\s*[:\s]*([\d\.,]+)',
    re.IGNORECASE
)
TOTAL_DEBIT_TRANSACTION_PATTERN: Pattern = re.compile(
    r'Total\s+Debit\s+Transaction\s*[:\s]*([\d\.,]+)',
    re.IGNORECASE
)
TOTAL_TRANSaksi_KREDIT_PATTERN: Pattern = re.compile(
    r'Total\s+Transaksi\s+Kredit\s*[:\s]*([\d\.,]+)',
    re.IGNORECASE
)
TOTAL_CREDIT_TRANSACTION_PATTERN: Pattern = re.compile(
    r'Total\s+Credit\s+Transaction\s*[:\s]*([\d\.,]+)',
    re.IGNORECASE
)

# Additional compiled patterns for faster lookups
_WHITESPACE_PATTERN: Pattern = re.compile(r'\s+')
_NUMERIC_LINE_PATTERN: Pattern = re.compile(r'^[\d,.]+\s*$')
_NUMERIC_ONLY_PATTERN: Pattern = re.compile(r'^[\d,.]*$')
_AMOUNT_PATTERN: Pattern = re.compile(r'^[\d,]+\.\d{2}$')
_USER_ID_PATTERN: Pattern = re.compile(r'^\d{6,8}$')

# Summary section label patterns (compiled for extract_summary_totals)
_SALDO_AWAL_PATTERN: Pattern = re.compile(r'^Saldo\s+Awal$|^Opening\s+Balance$', re.IGNORECASE)
_TOTAL_DEBIT_LABEL_PATTERN: Pattern = re.compile(r'^Total\s+Transaksi\s+Debet$|^Total\s+Debit\s+Transaction$', re.IGNORECASE)
_TOTAL_CREDIT_LABEL_PATTERN: Pattern = re.compile(r'^Total\s+Transaksi\s+Kredit$|^Total\s+Credit\s+Transaction$', re.IGNORECASE)
_SALDO_AKHIR_PATTERN: Pattern = re.compile(r'^Saldo\s+Akhir$|^Closing\s+Balance$', re.IGNORECASE)

# Summary label patterns mapping
_SUMMARY_LABEL_PATTERNS: List[tuple] = [
    (_SALDO_AWAL_PATTERN, 'opening_balance'),
    (_TOTAL_DEBIT_LABEL_PATTERN, 'total_debit'),
    (_TOTAL_CREDIT_LABEL_PATTERN, 'total_credit'),
    (_SALDO_AKHIR_PATTERN, 'closing_balance'),
]


@lru_cache(maxsize=128)
def get_cached_pattern(pattern: str, flags: int = 0) -> Pattern:
    """
    Get or create cached compiled pattern.

    This is a fallback for dynamically generated patterns.
    Most patterns should be pre-compiled at module level.

    Args:
        pattern: Regex pattern string
        flags: Regex flags (re.IGNORECASE, etc.)

    Returns:
        Compiled regex Pattern object
    """
    return re.compile(pattern, flags)


def load_config() -> Dict[str, str]:
    """
    Load configuration from environment variables.

    Reads from .env file if present, otherwise uses defaults.
    Environment variables:
        - SOURCE_PDF_DIR: Directory containing source PDF files
        - OUTPUT_DIR: Directory for output CSV files
        - TEST_PDFS_DIR: Directory for test/benchmark PDF files
        - VERIFY_TURNOVER: Enable turnover verification ('true' or 'false')

    Returns:
        Dict with keys: source_pdf_dir, output_dir, test_pdfs_dir, verify_turnover
    """
    # Load .env file if it exists (silent if missing)
    load_dotenv()

    return {
        'source_pdf_dir': os.getenv('SOURCE_PDF_DIR', 'source-pdf'),
        'output_dir': os.getenv('OUTPUT_DIR', 'output'),
        'test_pdfs_dir': os.getenv('TEST_PDFS_DIR', 'test-pdfs'),
        'verify_turnover': os.getenv('VERIFY_TURNOVER', 'false')
    }


# Old pattern strings (kept for reference, but compiled versions are used)
# ACCOUNT_NO_PATTERN = r'No\.?\s*Rekening\s*\n(?:Account\s+No\s*\n)?\s*:?\s*([0-9]+)'
# ... etc (patterns are now compiled at module level above)


def extract_metadata(text: str) -> Dict[str, str]:
    """
    Extract metadata fields from bank statement text.

    Args:
        text: Full text extracted from PDF first page (header section)

    Returns:
        Dict containing keys: account_no, business_unit, product_name, statement_date, valuta, unit_address, transaction_period
    """
    metadata = {}

    # Labels that indicate this is a label, not a value
    # Using frozenset for faster membership testing (O(1) vs O(n))
    _LABEL_INDICATORS = frozenset([
        'unit kerja', 'nama produk', 'alamat unit', 'valuta', 'currency',
        'tanggal transaksi', 'uraian transaksi', 'teller', 'user id',
        'debet', 'kredit', 'saldo', 'transaction date', 'transaction description'
    ])

    # Cache local functions for hot path optimization
    _is_likely_label = _LABEL_INDICATORS.__contains__
    _sub_whitespace = _WHITESPACE_PATTERN.sub

    def is_likely_label(value: str) -> bool:
        """Check if value looks like a field label rather than actual data."""
        return _is_likely_label(value.lower().strip())

    # Extract Account No
    account_match = ACCOUNT_NO_PATTERN.search(text)
    account_no = account_match.group(1).strip() if account_match else ''
    # Validate: if it looks like a label, treat as empty
    if is_likely_label(account_no):
        account_no = ''
    metadata['account_no'] = account_no

    # Extract Business Unit
    business_match = BUSINESS_UNIT_PATTERN.search(text)
    metadata['business_unit'] = business_match.group(1).strip() if business_match else ''

    # Extract Product Name
    product_match = PRODUCT_NAME_PATTERN.search(text)
    product_name = product_match.group(1).strip() if product_match else ''
    if is_likely_label(product_name):
        product_name = ''
    # Strip currency suffix if present (e.g., "Britama-IDR" -> "Britama")
    if product_name.endswith('-IDR'):
        product_name = product_name[:-4]
    metadata['product_name'] = product_name

    # Extract Statement Date
    date_match = STATEMENT_DATE_PATTERN.search(text)
    metadata['statement_date'] = date_match.group(1).strip() if date_match else ''

    # Extract Valuta (Currency)
    valuta_match = VALUTA_PATTERN.search(text)
    metadata['valuta'] = valuta_match.group(1).strip() if valuta_match else ''

    # Extract Unit Address (combines multiple lines)
    address_match = UNIT_ADDRESS_PATTERN.search(text)
    if address_match:
        # Get the address and clean up whitespace
        address = address_match.group(1).strip()
        # Replace newlines with spaces and clean up using compiled pattern
        address = _sub_whitespace(' ', address)
        # Skip if it looks like a label
        if not is_likely_label(address):
            metadata['unit_address'] = address
        else:
            metadata['unit_address'] = ''
    else:
        metadata['unit_address'] = ''

    # Extract Transaction Period
    period_match = TRANSACTION_PERIOD_PATTERN.search(text)
    metadata['transaction_period'] = period_match.group(1).strip() if period_match else ''

    return metadata


def extract_transactions(text: str) -> List[Dict[str, str]]:
    """
    Extract transaction rows from bank statement text.

    Parses column-based transaction rows where each field is on a separate line:
    - Line 1: Date and time (DD/MM/YY HH:MM:SS)
    - Line 2: Description (may span multiple lines)
    - Line 3: User/Teller ID (optional - some PDFs skip this)
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

    # Cache compiled patterns for hot loop optimization
    _txn_date_match = TRANSACTION_DATE_PATTERN.match
    _amount_match = _AMOUNT_PATTERN.match
    _user_id_match = _USER_ID_PATTERN.match
    _numeric_line_match = _NUMERIC_LINE_PATTERN.match
    _date_only_match = re.compile(r'^(\d{2}/\d{2}/\d{2})').match

    while i < len(lines):
        line = lines[i].strip()

        # Skip empty lines
        if not line:
            i += 1
            continue

        # Check if line starts with date pattern (new transaction) using compiled pattern
        if _txn_date_match(line):
            # Extract date from the line (may include time)
            date_match = _date_only_match(line)
            if date_match:
                date = line  # Keep the full date+time string

                # Collect description lines until we hit numeric fields
                i += 1
                description_lines = []
                while i < len(lines):
                    next_line = lines[i].strip()
                    # Stop if we hit another transaction date
                    if _txn_date_match(next_line):
                        break
                    # Stop if we hit a numeric amount line (debit/credit/balance)
                    if _numeric_line_match(next_line):
                        break
                    if next_line:
                        description_lines.append(next_line)
                    i += 1
                description = ' '.join(description_lines)

                # Move to next field (could be user ID or debit)
                while i < len(lines) and not lines[i].strip():
                    i += 1
                if i >= len(lines):
                    break

                next_field = lines[i].strip()

                # Check if this is user ID (numeric but with 6-8 digits) or debit (0.00 format)
                # User IDs are typically 6-8 digit numbers without decimals
                # Debit/credit amounts have decimal format (0.00)
                is_user_id = bool(_user_id_match(next_field))
                is_amount = bool(_amount_match(next_field))

                if is_user_id:
                    # Format with user ID
                    user = next_field
                    i += 1
                    # Skip to debit
                    while i < len(lines) and not lines[i].strip():
                        i += 1
                    debit = lines[i].strip() if i < len(lines) else ''
                    i += 1
                    while i < len(lines) and not lines[i].strip():
                        i += 1
                    credit = lines[i].strip() if i < len(lines) else ''
                    i += 1
                    while i < len(lines) and not lines[i].strip():
                        i += 1
                    balance = lines[i].strip() if i < len(lines) else ''
                elif is_amount:
                    # Format without user ID - next field is debit
                    user = ''
                    debit = next_field
                    i += 1
                    while i < len(lines) and not lines[i].strip():
                        i += 1
                    credit = lines[i].strip() if i < len(lines) else ''
                    i += 1
                    while i < len(lines) and not lines[i].strip():
                        i += 1
                    balance = lines[i].strip() if i < len(lines) else ''
                else:
                    # Fallback - assume user ID
                    user = next_field
                    debit = ''
                    credit = ''
                    balance = ''

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


def _format_number_for_csv(value: str) -> str:
    """
    Format number value for CSV output.

    Converts Indonesian format (1.000.000,00) or US format (1,000,000.00)
    to standard format (1000000.00) without thousand separators.

    Args:
        value: Number string in Indonesian, US, or standard format

    Returns:
        Clean number string without thousand separators
    """
    if not value or not value.strip():
        return ''

    # Check if it looks like a number (contains digits and optionally . or ,)
    if not any(c.isdigit() for c in value):
        return value

    # Detect format and parse accordingly
    original = value.strip()

    # Check if both comma and period present
    if ',' in original and '.' in original:
        # Determine which is decimal separator by position
        comma_pos = original.rfind(',')
        period_pos = original.rfind('.')

        if comma_pos > period_pos:
            # Comma is after period - comma is decimal separator (Indonesian format)
            # Example: 1.234.567,89
            parsed = parse_indonesian_number(original)
        else:
            # Period is after comma - period is decimal separator (US format)
            # Example: 1,234,567.89
            # Remove commas (thousand separators)
            cleaned = original.replace(',', '')
            try:
                parsed = float(cleaned)
            except ValueError:
                return original
    elif ',' in original:
        # Only comma present - US format with comma as thousand separator
        # Example: 1,000,000
        cleaned = original.replace(',', '')
        try:
            parsed = float(cleaned)
        except ValueError:
            return original
    else:
        # No comma - already in standard format (or Indonesian without decimal)
        try:
            parsed = float(original)
        except ValueError:
            return original

    # Format as standard number without thousand separators
    # Remove trailing .00 if it was an integer
    formatted = f'{parsed:.2f}'
    if formatted.endswith('.00'):
        formatted = formatted[:-3]
    return formatted


def save_metadata_csv(metadata: Dict[str, str], output_path: str) -> None:
    """
    Write metadata dict to CSV file with Field and Value columns.

    Uses semicolon (;) as delimiter and formats numbers without thousand separators.

    Args:
        metadata: Dict of metadata fields
        output_path: Path where CSV file will be written
    """
    with open(output_path, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.writer(csvfile, delimiter=';')
        writer.writerow(['Field', 'Value'])
        for field, value in metadata.items():
            # Format numeric values
            formatted_value = _format_number_for_csv(value) if value else ''
            writer.writerow([field, formatted_value])


def save_transactions_csv(transactions: List[Dict[str, str]], output_path: str) -> None:
    """
    Write transactions list to CSV file.

    Uses semicolon (;) as delimiter and formats numbers without thousand separators.
    Output columns: Date, Description, User, Debit, Credit, Balance

    Args:
        transactions: List of transaction dicts
        output_path: Path where CSV file will be written
    """
    if not transactions:
        # Write empty CSV with headers
        with open(output_path, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile, delimiter=';')
            writer.writerow(['Date', 'Description', 'User', 'Debit', 'Credit', 'Balance'])
        return

    fieldnames = ['Date', 'Description', 'User', 'Debit', 'Credit', 'Balance']

    with open(output_path, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames, delimiter=';')
        writer.writeheader()

        for txn in transactions:
            writer.writerow({
                'Date': txn.get('date', ''),
                'Description': txn.get('description', ''),
                'User': txn.get('user', ''),
                'Debit': _format_number_for_csv(txn.get('debit', '')),
                'Credit': _format_number_for_csv(txn.get('credit', '')),
                'Balance': _format_number_for_csv(txn.get('balance', ''))
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


def parse_indonesian_number(value: str) -> float:
    """
    Parse Indonesian number format to float.

    Indonesian format uses '.' as thousands separator and ',' as decimal separator.
    Examples: "1.000.000,00" -> 1000000.00, "123,45" -> 123.45

    Args:
        value: String containing number in Indonesian format

    Returns:
        Float representation of the number
    """
    if not value or not value.strip():
        return 0.0

    # Remove thousands separators (dots) and replace decimal comma with dot
    cleaned = value.strip().replace('.', '').replace(',', '.')
    try:
        return float(cleaned)
    except ValueError:
        return 0.0


def extract_summary_totals(text: str) -> Dict[str, Optional[str]]:
    """
    Extract summary total values from bank statement text.

    Searches for Indonesian and English total labels:
    - Total Transaksi Debet / Total Debit Transaction (debit total)
    - Total Transaksi Kredit / Total Credit Transaction (credit total)
    - Saldo Awal / Opening Balance (opening balance)
    - Saldo Akhir / Closing Balance (closing balance)

    The values may be on the same line as the label (with :) or on subsequent lines.

    Args:
        text: Full text extracted from PDF (may include summary section)

    Returns:
        Dict with keys:
            - total_debit: Value from PDF summary or None if not found
            - total_credit: Value from PDF summary or None if not found
            - opening_balance: Value from PDF summary or None if not found
            - closing_balance: Value from PDF summary or None if not found
    """
    result: Dict[str, Optional[str]] = {
        'total_debit': None,
        'total_credit': None,
        'opening_balance': None,
        'closing_balance': None,
    }

    lines = text.split('\n')
    n = len(lines)

    # Cache compiled patterns for hot loop optimization
    _numeric_only_match = _NUMERIC_ONLY_PATTERN.match
    _numeric_line_match = _NUMERIC_LINE_PATTERN.match

    # Find positions of unique summary labels (deduplicate)
    # Track which label types we've already found
    found_types = set()
    all_labels = []
    for i, line in enumerate(lines):
        line_clean = line.strip()
        for pattern, label_type in _SUMMARY_LABEL_PATTERNS:
            if pattern.match(line_clean):
                if label_type not in found_types:
                    all_labels.append((label_type, i))
                    found_types.add(label_type)
                break

    # Find the summary section values (numbers after labels)
    if all_labels:
        # Start from the first label position
        start_search = min(pos for _, pos in all_labels)

        # Find all consecutive number lines (values section)
        values = []
        for i in range(start_search, n):
            line = lines[i].strip()
            if _numeric_line_match(line):
                values.append((i, line))
            elif not _numeric_only_match(line):
                # If we hit a non-number line, might be end of values section
                if len(values) >= 2:
                    break

        # Map labels to values based on order
        # Each label gets the next value in sequence
        if values and len(values) >= len(all_labels):
            # Direct mapping: label[i] -> value[i]
            for (label_type, _), (_, val_line) in zip(all_labels, values):
                result[label_type] = val_line
        elif values:
            # Fallback: find values that come after each label
            for label_type, label_idx in all_labels:
                for val_idx, val_line in values:
                    if val_idx > label_idx:
                        result[label_type] = val_line
                        break

    # Fallback: try original patterns for inline format (now using compiled patterns)
    if result['total_debit'] is None:
        match = TOTAL_TRANSaksi_DEBET_PATTERN.search(text)
        if match:
            result['total_debit'] = match.group(1).strip()
        else:
            match = TOTAL_DEBIT_TRANSACTION_PATTERN.search(text)
            if match:
                result['total_debit'] = match.group(1).strip()

    if result['total_credit'] is None:
        match = TOTAL_TRANSaksi_KREDIT_PATTERN.search(text)
        if match:
            result['total_credit'] = match.group(1).strip()
        else:
            match = TOTAL_CREDIT_TRANSACTION_PATTERN.search(text)
            if match:
                result['total_credit'] = match.group(1).strip()

    return result


def calculate_debit_sum(transactions: List[Dict[str, str]]) -> float:
    """
    Calculate the sum of all debit amounts from transactions.

    Args:
        transactions: List of transaction dicts with 'debit' field

    Returns:
        Sum of all debit amounts as float
    """
    total = 0.0
    for txn in transactions:
        debit = txn.get('debit', '')
        total += parse_indonesian_number(debit)
    return total


def calculate_credit_sum(transactions: List[Dict[str, str]]) -> float:
    """
    Calculate the sum of all credit amounts from transactions.

    Args:
        transactions: List of transaction dicts with 'credit' field

    Returns:
        Sum of all credit amounts as float
    """
    total = 0.0
    for txn in transactions:
        credit = txn.get('credit', '')
        total += parse_indonesian_number(credit)
    return total


def verify_turnover(
    transactions: List[Dict[str, str]],
    tolerance: float = 0.01,
    summary_text: str = ""
) -> Dict[str, object]:
    """
    Verify turnover totals by comparing PDF summary totals against calculated sums.

    Compares Total Transaksi Debet/Total Debit Transaction from PDF summary
    against the sum of debit column values in transactions. Similarly for credit.

    Args:
        transactions: List of transaction dicts with 'debit' and 'credit' fields
        tolerance: Maximum allowed discrepancy for floating-point comparison (default: 0.01)
        summary_text: Full text from PDF containing summary totals section

    Returns:
        Dict containing verification result with keys:
            - passed: bool indicating overall verification success
            - debit_match: bool indicating debit comparison result
            - credit_match: bool indicating credit comparison result
            - total_debit_extracted: Value from PDF summary (if found)
            - total_debit_calculated: Sum from transaction debits
            - debit_discrepancy: Difference between extracted and calculated
            - total_credit_extracted: Value from PDF summary (if found)
            - total_credit_calculated: Sum from transaction credits
            - credit_discrepancy: Difference between extracted and calculated
            - status: String - "passed", "failed", or "not_available"
            - message: Human-readable description of result
    """
    # Extract summary totals from PDF text
    summary_totals = extract_summary_totals(summary_text)

    # Calculate sums from transactions
    calculated_debit = calculate_debit_sum(transactions)
    calculated_credit = calculate_credit_sum(transactions)

    # Parse extracted values
    extracted_debit = parse_indonesian_number(summary_totals['total_debit']) if summary_totals['total_debit'] else None
    extracted_credit = parse_indonesian_number(summary_totals['total_credit']) if summary_totals['total_credit'] else None

    # Compare debit totals
    debit_match = False
    debit_discrepancy = 0.0
    if extracted_debit is not None:
        debit_discrepancy = abs(extracted_debit - calculated_debit)
        debit_match = debit_discrepancy <= tolerance

    # Compare credit totals
    credit_match = False
    credit_discrepancy = 0.0
    if extracted_credit is not None:
        credit_discrepancy = abs(extracted_credit - calculated_credit)
        credit_match = credit_discrepancy <= tolerance

    # Determine overall status
    if summary_totals['total_debit'] is None and summary_totals['total_credit'] is None:
        status = 'not_available'
        message = 'Summary totals not found in PDF - verification not applicable'
    elif debit_match and credit_match:
        status = 'passed'
        message = 'All turnover totals match within tolerance'
    else:
        status = 'failed'
        mismatch_parts = []
        if extracted_debit is not None and not debit_match:
            mismatch_parts.append(f'debit discrepancy: {debit_discrepancy:,.2f}')
        if extracted_credit is not None and not credit_match:
            mismatch_parts.append(f'credit discrepancy: {credit_discrepancy:,.2f}')
        message = f'Turnover mismatch - {", ".join(mismatch_parts)}'

    return {
        'passed': status == 'passed',
        'debit_match': debit_match,
        'credit_match': credit_match,
        'total_debit_extracted': summary_totals['total_debit'],
        'total_debit_calculated': calculated_debit,
        'debit_discrepancy': debit_discrepancy,
        'total_credit_extracted': summary_totals['total_credit'],
        'total_credit_calculated': calculated_credit,
        'credit_discrepancy': credit_discrepancy,
        'status': status,
        'message': message
    }
