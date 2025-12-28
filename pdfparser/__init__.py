"""
PDF Parser for Indonesian Bank Statements (Rekening Koran)

This module provides functions to parse PDF bank statements and extract:
- Metadata (Account No, Business Unit, Product Name, Statement Date)
- Transactions (Date, Description, User, Debit, Credit, Balance)
"""

from pdfparser.batch import batch_parse, batch_parse_from_directory
from pdfparser.pdfoxide_parser import parse_pdf_pdfoxide
from pdfparser.pdfplumber_parser import parse_pdf_pdfplumber
from pdfparser.pymupdf_parser import parse_pdf_pymupdf
from pdfparser.pypdf_parser import parse_pdf_pypdf
from pdfparser.utils import (
    ensure_output_dirs,
    extract_metadata,
    extract_transactions,
    is_valid_parse,
    load_config,
    save_metadata_csv,
    save_transactions_csv,
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
    elif parser == 'pdfoxide':
        return parse_pdf_pdfoxide(path)
    else:
        raise ValueError(f"Invalid parser: {parser}. Choose 'pymupdf', 'pdfplumber', 'pypdf', or 'pdfoxide'")


__all__ = [
    'parse_pdf',
    'parse_pdf_pymupdf',
    'parse_pdf_pdfplumber',
    'parse_pdf_pypdf',
    'parse_pdf_pdfoxide',
    'batch_parse',
    'batch_parse_from_directory',
    'extract_metadata',
    'extract_transactions',
    'save_metadata_csv',
    'save_transactions_csv',
    'is_valid_parse',
    'ensure_output_dirs',
    'load_config'
]
