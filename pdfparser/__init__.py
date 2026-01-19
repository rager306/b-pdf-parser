"""
PDF Parser for Indonesian Bank Statements (Rekening Koran)

This module provides functions to parse PDF bank statements and extract:
- Metadata (Account No, Business Unit, Product Name, Statement Date)
- Transactions (Date, Description, User, Debit, Credit, Balance)
- Turnover verification (optional)

Usage:
    # Function interface
    from pdfparser import parse_pdf
    result = parse_pdf('statement.pdf')

    # Class interface
    from pdfparser import PDFParser
    parser = PDFParser(parser='pymupdf', verify_turnover=False)
    result = parser.parse('statement.pdf')
"""

from typing import Dict, List, Optional, Union

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
from pdfparser.utils import (
    verify_turnover as verify_turnover_func,
)


class PDFParser:
    """
    Class-based interface for parsing Indonesian bank statement PDFs.

    Provides the same functionality as parse_pdf() function but with
    configurable state.

    Attributes:
        parser: PDF parsing library to use ('pymupdf', 'pdfplumber', 'pypdf', 'pdfoxide')
        verify_turnover: Whether to verify turnover totals (True/False/None for .env default)

    Example:
        from pdfparser import PDFParser

        # Create parser with default settings
        parser = PDFParser()
        result = parser.parse('statement.pdf')

        # Custom parser settings
        parser = PDFParser(parser='pymupdf', verify_turnover=True)
        result = parser.parse('statement.pdf')
    """

    VALID_PARSERS = ("pymupdf", "pdfplumber", "pypdf", "pdfoxide")

    def __init__(self, parser: str = "pymupdf", verify_turnover: Optional[bool] = None):
        """
        Initialize PDFParser with specified settings.

        Args:
            parser: PDF parsing library to use. Options: 'pymupdf' (default, fastest),
                'pdfplumber' (table extraction), 'pypdf' (pure Python), 'pdfoxide' (Rust-based)
            verify_turnover: Whether to verify turnover totals against PDF summary.
                True = enable, False = disable, None = use VERIFY_TURNOVER from .env

        Raises:
            ValueError: If parser name is invalid
        """
        if parser not in self.VALID_PARSERS:
            raise ValueError(
                f"Invalid parser: {parser}. Choose from: {', '.join(self.VALID_PARSERS)}"
            )
        self.parser = parser
        self.verify_turnover = verify_turnover

    def parse(self, path: str) -> Dict[str, Union[Dict, List, None]]:
        """
        Parse a PDF bank statement file.

        Args:
            path: Path to PDF file

        Returns:
            Dictionary with keys:
                - 'metadata': dict with extracted fields (account_no, business_unit,
                  product_name, statement_date, valuta, unit_address, transaction_period,
                  total_debit, total_credit, opening_balance, closing_balance)
                - 'transactions': list of transaction dicts with fields
                  (date, description, user, debit, credit, balance)
                - 'verification': dict with turnover verification results (if enabled)

        Raises:
            FileNotFoundError: If PDF file doesn't exist
            ValueError: If parser name is invalid
        """
        return parse_pdf(path, parser=self.parser, verify_turnover=self.verify_turnover)

    def __repr__(self) -> str:
        return f"PDFParser(parser='{self.parser}', verify_turnover={self.verify_turnover})"


def parse_pdf(path: str, parser: str = "pymupdf", verify_turnover: Optional[bool] = None) -> dict:
    """
    Parse a PDF bank statement file.

    Args:
        path: Path to PDF file
        parser: Parser to use ('pymupdf', 'pdfplumber', 'pypdf', 'pdfoxide')
        verify_turnover: Whether to verify turnover totals against summary.
            True = enable verification, False = disable, None = use .env setting

    Returns:
        dict with keys:
            - 'metadata': dict of metadata fields
            - 'transactions': list of transaction dicts
            - 'verification': dict of verification results (if enabled)

    Raises:
        ValueError: If parser name is invalid
        FileNotFoundError: If PDF file doesn't exist
    """
    # Determine if verification should be enabled
    if verify_turnover is None:
        config = load_config()
        should_verify = config.get("verify_turnover", "").lower() == "true"
    else:
        should_verify = verify_turnover

    # Parse the PDF based on selected parser
    if parser == "pymupdf":
        result = parse_pdf_pymupdf(path)
    elif parser == "pdfplumber":
        result = parse_pdf_pdfplumber(path)
    elif parser == "pypdf":
        result = parse_pdf_pypdf(path)
    elif parser == "pdfoxide":
        result = parse_pdf_pdfoxide(path)
    else:
        raise ValueError(
            f"Invalid parser: {parser}. Choose 'pymupdf', 'pdfplumber', 'pypdf', or 'pdfoxide'"
        )

    # Add verification if enabled
    if should_verify:
        full_text = result.get("full_text", "")
        result["verification"] = verify_turnover_func(
            result.get("transactions", []), summary_text=full_text
        )

    # Remove full_text from result to keep output clean
    result.pop("full_text", None)

    return result


__all__ = [
    "parse_pdf",
    "PDFParser",
    "parse_pdf_pymupdf",
    "parse_pdf_pdfplumber",
    "parse_pdf_pypdf",
    "parse_pdf_pdfoxide",
    "batch_parse",
    "batch_parse_from_directory",
    "extract_metadata",
    "extract_transactions",
    "save_metadata_csv",
    "save_transactions_csv",
    "is_valid_parse",
    "ensure_output_dirs",
    "load_config",
]
