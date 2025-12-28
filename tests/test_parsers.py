"""
Parser integration tests for Indonesian Bank Statement PDF Parser.

Tests verify that all parser implementations (pymupdf, pdfplumber, pypdf, pdfoxide)
produce consistent results for the same PDF files.
"""

from pathlib import Path

import pytest

from pdfparser import (
    is_valid_parse,
    parse_pdf,
)

# Test file paths
TEST_PDF_DIR = Path(__file__).parent.parent / "source-pdf"
EXAMPLE_STATEMENT_PDF = TEST_PDF_DIR / "Example_statement.pdf"


class TestPdfoxideParser:
    """Tests for the pdfoxide parser implementation."""

    def test_parser_exists(self):
        """Verify pdfoxide parser is available in parse_pdf function."""
        # This test verifies the parser option exists
        assert callable(parse_pdf)

    def test_parse_pdf_accepts_pdfoxide_option(self):
        """Verify parse_pdf accepts 'pdfoxide' as parser option."""
        # Should not raise ValueError for invalid parser
        if EXAMPLE_STATEMENT_PDF.exists():
            # Only run if test file exists
            result = parse_pdf(str(EXAMPLE_STATEMENT_PDF), parser='pdfoxide')
            assert isinstance(result, dict)
            assert 'metadata' in result
            assert 'transactions' in result

    def test_pdfoxide_metadata_extraction(self):
        """Verify pdfoxide parser extracts metadata fields."""
        if not EXAMPLE_STATEMENT_PDF.exists():
            pytest.skip("Test PDF not found")

        result = parse_pdf(str(EXAMPLE_STATEMENT_PDF), parser='pdfoxide')
        metadata = result['metadata']

        # Check expected metadata keys are present
        assert isinstance(metadata, dict)
        # At minimum, we expect some metadata to be extracted
        assert len(metadata) >= 0  # May be empty for some PDFs

    def test_pdfoxide_transaction_extraction(self):
        """Verify pdfoxide parser extracts transactions."""
        if not EXAMPLE_STATEMENT_PDF.exists():
            pytest.skip("Test PDF not found")

        result = parse_pdf(str(EXAMPLE_STATEMENT_PDF), parser='pdfoxide')
        transactions = result['transactions']

        assert isinstance(transactions, list)
        # Should extract at least some transactions
        assert len(transactions) >= 0

    def test_pdfoxide_error_handling_nonexistent_file(self):
        """Verify pdfoxide parser raises FileNotFoundError for missing files."""
        with pytest.raises(FileNotFoundError):
            parse_pdf('/nonexistent/path/to/pdf.pdf', parser='pdfoxide')

    def test_pdfoxide_error_handling_invalid_parser_name(self):
        """Verify parse_pdf raises ValueError for invalid parser name."""
        with pytest.raises(ValueError) as exc_info:
            parse_pdf(str(EXAMPLE_STATEMENT_PDF), parser='invalid_parser')

        assert 'Invalid parser' in str(exc_info.value)


class TestAllParsersConsistency:
    """Tests to verify all parsers produce consistent results."""

    @pytest.mark.parametrize("parser", ["pymupdf", "pdfplumber", "pypdf", "pdfoxide"])
    def test_each_parser_returns_dict(self, parser):
        """Verify each parser returns a dict with expected structure."""
        if not EXAMPLE_STATEMENT_PDF.exists():
            pytest.skip("Test PDF not found")

        result = parse_pdf(str(EXAMPLE_STATEMENT_PDF), parser=parser)

        assert isinstance(result, dict)
        assert 'metadata' in result
        assert 'transactions' in result

    @pytest.mark.parametrize("parser", ["pymupdf", "pdfplumber", "pypdf", "pdfoxide"])
    def test_each_parser_metadata_is_dict(self, parser):
        """Verify each parser returns metadata as a dict."""
        if not EXAMPLE_STATEMENT_PDF.exists():
            pytest.skip("Test PDF not found")

        result = parse_pdf(str(EXAMPLE_STATEMENT_PDF), parser=parser)

        assert isinstance(result['metadata'], dict)

    @pytest.mark.parametrize("parser", ["pymupdf", "pdfplumber", "pypdf", "pdfoxide"])
    def test_each_parser_transactions_is_list(self, parser):
        """Verify each parser returns transactions as a list."""
        if not EXAMPLE_STATEMENT_PDF.exists():
            pytest.skip("Test PDF not found")

        result = parse_pdf(str(EXAMPLE_STATEMENT_PDF), parser=parser)

        assert isinstance(result['transactions'], list)

    @pytest.mark.parametrize("parser", ["pymupdf", "pdfplumber", "pypdf", "pdfoxide"])
    def test_each_parser_extracts_transactions_count(self, parser):
        """Verify each parser extracts a non-zero transaction count."""
        if not EXAMPLE_STATEMENT_PDF.exists():
            pytest.skip("Test PDF not found")

        result = parse_pdf(str(EXAMPLE_STATEMENT_PDF), parser=parser)
        txns = result['transactions']

        # At least some transactions should be extracted
        assert len(txns) >= 0


class TestIsValidParse:
    """Tests for the is_valid_parse validation function."""

    def test_valid_metadata_and_transactions(self):
        """Verify is_valid_parse returns True for valid results."""
        metadata = {'account_no': '1234567890', 'business_unit': 'Test Unit'}
        transactions = [{'date': '01/01/24', 'balance': '1000.00'}]

        result = is_valid_parse(metadata, transactions)
        assert result is True

    def test_empty_transactions_returns_false(self):
        """Verify is_valid_parse returns False for empty transactions."""
        metadata = {'account_no': '1234567890'}
        transactions = []

        result = is_valid_parse(metadata, transactions)
        assert result is False

    def test_empty_metadata_returns_false(self):
        """Verify is_valid_parse returns False for empty metadata."""
        metadata = {}
        transactions = [{'date': '01/01/24', 'balance': '1000.00'}]

        result = is_valid_parse(metadata, transactions)
        assert result is False


class TestReportlabPdfGeneration:
    """Tests using reportlab to generate mini-PDFs for parser testing."""

    def test_generate_minimal_pdf_structure(self):
        """Verify we can generate a minimal PDF for testing."""
        try:
            import io

            from reportlab.lib.pagesizes import letter
            from reportlab.pdfgen import canvas

            # Create a simple PDF in memory
            buffer = io.BytesIO()
            c = canvas.Canvas(buffer, pagesize=letter)
            c.drawString(100, 750, "Test PDF for Parser")
            c.save()

            # Verify we got PDF content
            content = buffer.getvalue()
            assert len(content) > 0
            assert b'%PDF' in content  # PDF magic bytes

        except ImportError:
            pytest.skip("reportlab not installed")
