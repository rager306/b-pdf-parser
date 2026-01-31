import pytest
from pdfparser.pdfoxide_parser import preprocess_text

class TestPdfoxidePreprocessing:
    def test_preprocess_text_empty(self):
        """Test preprocessing with empty input."""
        assert preprocess_text("") == ""
        assert preprocess_text(None) == ""

    def test_preprocess_text_no_change_needed(self):
        """Test preprocessing with clean text that doesn't need changes."""
        text = "Hello World\n123.45\n678.90"
        assert preprocess_text(text) == text

    def test_preprocess_text_smashed_amount_basic(self):
        """Test separating two smashed amounts (e.g., 0.0026,000.00)."""
        text = "0.0026,000.00"
        expected = "0.00\n26,000.00"
        assert preprocess_text(text) == expected

    def test_preprocess_text_chained_smashed_amounts(self):
        """Test separating three smashed amounts (requires multiple passes)."""
        text = "10.0020.0030.00"
        expected = "10.00\n20.00\n30.00"
        assert preprocess_text(text) == expected

    def test_preprocess_text_mixed_separators(self):
        """Test with comma as thousand separator (US format)."""
        # 1,234.56 followed by 7,890.12
        text = "1,234.567,890.12"
        expected = "1,234.56\n7,890.12"
        assert preprocess_text(text) == expected

    def test_preprocess_text_with_context(self):
        """Test with surrounding text."""
        text = "Balance: 1,000.002,500.00 End"
        expected = "Balance: 1,000.00\n2,500.00 End"
        assert preprocess_text(text) == expected

    def test_preprocess_text_does_not_break_standard_amounts(self):
        """Test that standard amounts are not broken."""
        text = "1,000.00"
        assert preprocess_text(text) == text

        text = "0.00"
        assert preprocess_text(text) == text
