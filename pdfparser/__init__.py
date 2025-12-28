"""
PDF Parser for Indonesian Bank Statements (Rekening Koran)

This module provides functions to parse PDF bank statements and extract:
- Metadata (Account No, Business Unit, Product Name, Statement Date)
- Transactions (Date, Description, User, Debit, Credit, Balance)
"""

from pdfparser.pymupdf_parser import parse_pdf_pymupdf
from pdfparser.pdfplumber_parser import parse_pdf_pdfplumber
from pdfparser.pypdf_parser import parse_pdf_pypdf

from pdfparser.utils import (
    extract_metadata,
    extract_transactions,
    save_metadata_csv,
    save_transactions_csv,
    is_valid_parse,
    ensure_output_dirs,
    load_config
)


def parse_pdf(path: str, parser: str = 'pymupdf') -> dict:
    """
    Parse a PDF bank statement file.

    Args:
        path: Path to PDF file
        parser: Parser to use ('pymupdf', 'pdfplumber', 'pypdf')

    Returns:
        dict with keys:
            - 'metadata': dict of metadata fields
            - 'transactions': list of transaction dicts

    Raises:
        ValueError: If parser name is invalid
        FileNotFoundError: If PDF file doesn't exist
    """
    if parser == 'pymupdf':
        return parse_pdf_pymupdf(path)
    elif parser == 'pdfplumber':
        return parse_pdf_pdfplumber(path)
    elif parser == 'pypdf':
        return parse_pdf_pypdf(path)
    else:
        raise ValueError(f"Invalid parser: {parser}. Choose 'pymupdf', 'pdfplumber', or 'pypdf'")


__all__ = [
    'parse_pdf',
    'parse_pdf_pymupdf',
    'parse_pdf_pdfplumber',
    'parse_pdf_pypdf',
    'extract_metadata',
    'extract_transactions',
    'save_metadata_csv',
    'save_transactions_csv',
    'is_valid_parse',
    'ensure_output_dirs',
    'load_config'
]
