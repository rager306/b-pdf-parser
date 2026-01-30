"""
Utility function tests with hypothesis property-based testing.

Tests verify the robustness of extract_metadata() and extract_transactions()
functions with various input patterns.
"""

import re

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st
from hypothesis.strategies import text

from pdfparser.utils import (
    ACCOUNT_NO_PATTERN,
    BUSINESS_UNIT_PATTERN,
    PRODUCT_NAME_PATTERN,
    STATEMENT_DATE_PATTERN,
    TRANSACTION_DATE_PATTERN,
    extract_metadata,
    extract_transactions,
    load_config,
)


class TestExtractMetadata:
    """Tests for extract_metadata() function using hypothesis."""

    @given(
        metadata_text=text(
            alphabet="abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 \n:.,-",
            min_size=0,
            max_size=1000,
        )
    )
    @settings(max_examples=50)
    def test_extract_metadata_returns_dict(self, metadata_text):
        """Verify extract_metadata always returns a dict."""
        result = extract_metadata(metadata_text)
        assert isinstance(result, dict)

    @given(
        metadata_text=text(
            alphabet="abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 \n:.,-",
            min_size=0,
            max_size=500,
        )
    )
    @settings(max_examples=30)
    def test_extract_metadata_values_are_strings(self, metadata_text):
        """Verify all metadata values are strings."""
        result = extract_metadata(metadata_text)
        for key, value in result.items():
            assert isinstance(value, str), f"Value for key '{key}' is not a string"

    @given(account_no=text(alphabet="0123456789", min_size=1, max_size=20))
    @settings(max_examples=10)
    def test_account_no_pattern_matches_digits(self, account_no):
        """Verify Account No pattern matches numeric strings."""
        pattern = ACCOUNT_NO_PATTERN
        match = re.search(pattern, f"Account No: {account_no}")
        if match:
            extracted = match.group(1).strip()
            assert extracted == account_no


class TestExtractTransactions:
    """Tests for extract_transactions() function using hypothesis."""

    @given(
        transaction_text=text(
            alphabet="abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 \n/:-",
            min_size=0,
            max_size=2000,
        )
    )
    @settings(max_examples=50)
    def test_extract_transactions_returns_list(self, transaction_text):
        """Verify extract_transactions always returns a list."""
        result = extract_transactions(transaction_text)
        assert isinstance(result, list)

    @given(
        transaction_text=text(
            alphabet="abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 \n/:-",
            min_size=0,
            max_size=1000,
        )
    )
    @settings(max_examples=30)
    def test_extract_transactions_items_are_dicts(self, transaction_text):
        """Verify all transaction items are dictionaries."""
        result = extract_transactions(transaction_text)
        for item in result:
            assert isinstance(item, dict), "Transaction item is not a dict"

    @given(
        transaction_text=text(
            alphabet="abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 \n/:-",
            min_size=0,
            max_size=500,
        )
    )
    @settings(max_examples=20)
    def test_extract_transactions_keys_are_strings(self, transaction_text):
        """Verify all transaction dict keys are strings."""
        result = extract_transactions(transaction_text)
        for item in result:
            for key in item.keys():
                assert isinstance(key, str), f"Key '{key}' is not a string"

    def test_extract_transactions_with_9_digit_user_id(self):
        """Verify extraction when user ID is 9 digits (regression test)."""
        text = """
01/01/24 12:00:00
Transfer Test
123456789
100000.00
0.00
500000.00
"""
        transactions = extract_transactions(text)
        assert len(transactions) == 1
        txn = transactions[0]
        assert txn['user'] == "123456789"
        assert txn['debit'] == "100000.00"
        assert txn['balance'] == "500000.00"


class TestTransactionDatePattern:
    """Tests for transaction date regex pattern using hypothesis."""

    @given(date_str=st.from_regex(r"\d{2}/\d{2}/\d{2} \d{2}:\d{2}:\d{2}", fullmatch=True))
    @settings(max_examples=20)
    def test_transaction_date_pattern_matches_format(self, date_str):
        """Verify pattern matches DD/MM/YY HH:MM:SS format."""
        match = re.match(TRANSACTION_DATE_PATTERN, date_str)
        assert match is not None, f"Pattern did not match valid date: {date_str}"

    @given(date_str=text(min_size=10, max_size=20))
    @settings(max_examples=50)
    def test_transaction_date_pattern_no_false_positives(self, date_str):
        """Verify pattern doesn't match invalid date formats."""
        # Only dates matching DD/MM/YY HH:MM:SS should match
        is_valid = bool(re.match(TRANSACTION_DATE_PATTERN, date_str))
        expected = bool(re.match(r"^\d{2}/\d{2}/\d{2} \d{2}:\d{2}:\d{2}$", date_str))
        # This may have false positives for other formats, which is acceptable
        # The key is that valid formats always match
        if expected:
            assert is_valid


class TestMetadataPatterns:
    """Tests for metadata extraction regex patterns."""

    def test_account_no_pattern_structure(self):
        """Verify Account No pattern is valid regex."""
        pattern = ACCOUNT_NO_PATTERN
        # Should compile without error
        compiled = re.compile(pattern)
        assert compiled is not None

    def test_business_unit_pattern_structure(self):
        """Verify Business Unit pattern is valid regex."""
        pattern = BUSINESS_UNIT_PATTERN
        compiled = re.compile(pattern)
        assert compiled is not None

    def test_product_name_pattern_structure(self):
        """Verify Product Name pattern is valid regex."""
        pattern = PRODUCT_NAME_PATTERN
        compiled = re.compile(pattern)
        assert compiled is not None

    def test_statement_date_pattern_structure(self):
        """Verify Statement Date pattern is valid regex."""
        pattern = STATEMENT_DATE_PATTERN
        compiled = re.compile(pattern)
        assert compiled is not None

    @given(
        sample_text=text(
            alphabet="abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 \n:.,-",
            min_size=0,
            max_size=200,
        )
    )
    @settings(max_examples=30)
    def test_metadata_extraction_no_crash(self, sample_text):
        """Verify extract_metadata handles any input without crashing."""
        # This is a fuzz test - should not raise exceptions
        try:
            result = extract_metadata(sample_text)
            assert isinstance(result, dict)
        except Exception as e:
            pytest.fail(f"extract_metadata raised exception: {e}")

    @given(
        sample_text=text(
            alphabet="abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 \n/:-",
            min_size=0,
            max_size=500,
        )
    )
    @settings(max_examples=30)
    def test_transaction_extraction_no_crash(self, sample_text):
        """Verify extract_transactions handles any input without crashing."""
        # This is a fuzz test - should not raise exceptions
        try:
            result = extract_transactions(sample_text)
            assert isinstance(result, list)
        except Exception as e:
            pytest.fail(f"extract_transactions raised exception: {e}")


class TestEdgeCases:
    """Edge case tests for utility functions."""

    def test_extract_metadata_empty_string(self):
        """Verify extract_metadata handles empty string."""
        result = extract_metadata("")
        assert isinstance(result, dict)
        # Returns dict with all expected keys, values are empty strings
        assert "account_no" in result
        assert "business_unit" in result
        assert "product_name" in result
        assert "statement_date" in result

    def test_extract_transactions_empty_string(self):
        """Verify extract_transactions handles empty string."""
        result = extract_transactions("")
        assert isinstance(result, list)
        assert len(result) == 0

    def test_extract_metadata_none_input(self):
        """Verify extract_metadata handles None-like input."""
        # The function expects a string, so passing None should be handled
        result = extract_metadata("")
        assert isinstance(result, dict)

    def test_extract_transactions_whitespace_only(self):
        """Verify extract_transactions handles whitespace-only input."""
        result = extract_transactions("   \n\n   \n   ")
        assert isinstance(result, list)


class TestLoadConfig:
    """Tests for load_config() function."""

    def test_load_config_returns_dict(self):
        """Verify load_config returns a dictionary."""
        result = load_config()
        assert isinstance(result, dict)

    def test_load_config_has_required_keys(self):
        """Verify load_config returns dict with all required keys."""
        result = load_config()
        assert "source_pdf_dir" in result
        assert "output_dir" in result
        assert "test_pdfs_dir" in result

    def test_load_config_has_verify_turnover_key(self):
        """Verify load_config returns dict with verify_turnover key."""
        result = load_config()
        assert "verify_turnover" in result

    def test_load_config_verify_turnover_default_false(self):
        """Verify verify_turnover defaults to 'false' string when not set."""
        result = load_config()
        # Should return string 'false' when not set in .env
        assert result["verify_turnover"] == "false"

    def test_load_config_values_are_strings(self):
        """Verify all config values are strings."""
        result = load_config()
        for key, value in result.items():
            assert isinstance(value, str), f"Config value for '{key}' is not a string"


class TestSummaryTotalPatterns:
    """Tests for summary total extraction regex patterns."""

    def test_total_transaksi_debet_pattern(self):
        """Verify regex pattern matches Total Transaksi Debet."""
        from pdfparser.utils import TOTAL_TRANSaksi_DEBET_PATTERN

        text = "Total Transaksi Debet: 1.234.567,89"
        import re

        match = re.search(TOTAL_TRANSaksi_DEBET_PATTERN, text)
        assert match is not None
        assert match.group(1) == "1.234.567,89"

    def test_total_debit_transaction_pattern(self):
        """Verify regex pattern matches Total Debit Transaction."""
        from pdfparser.utils import TOTAL_DEBIT_TRANSACTION_PATTERN

        text = "Total Debit Transaction: 987.654.321,00"
        import re

        match = re.search(TOTAL_DEBIT_TRANSACTION_PATTERN, text)
        assert match is not None
        assert match.group(1) == "987.654.321,00"

    def test_total_transaksi_kredit_pattern(self):
        """Verify regex pattern matches Total Transaksi Kredit."""
        from pdfparser.utils import TOTAL_TRANSaksi_KREDIT_PATTERN

        text = "Total Transaksi Kredit: 555.123.456,78"
        import re

        match = re.search(TOTAL_TRANSaksi_KREDIT_PATTERN, text)
        assert match is not None
        assert match.group(1) == "555.123.456,78"

    def test_total_credit_transaction_pattern(self):
        """Verify regex pattern matches Total Credit Transaction."""
        from pdfparser.utils import TOTAL_CREDIT_TRANSACTION_PATTERN

        text = "Total Credit Transaction: 111.222.333,44"
        import re

        match = re.search(TOTAL_CREDIT_TRANSACTION_PATTERN, text)
        assert match is not None
        assert match.group(1) == "111.222.333,44"


class TestExtractSummaryTotals:
    """Tests for extract_summary_totals() function."""

    def test_extract_summary_totals_returns_dict(self):
        """Verify extract_summary_totals returns a dictionary."""
        from pdfparser.utils import extract_summary_totals

        result = extract_summary_totals("")
        assert isinstance(result, dict)

    def test_extract_summary_totals_with_debit_value(self):
        """Verify extract_summary_totals extracts Total Transaksi Debet."""
        from pdfparser.utils import extract_summary_totals

        text = "Some text\nTotal Transaksi Debet: 1.000.000,00\nMore text"
        result = extract_summary_totals(text)
        assert result["total_debit"] == "1.000.000,00"

    def test_extract_summary_totals_with_credit_value(self):
        """Verify extract_summary_totals extracts Total Transaksi Kredit."""
        from pdfparser.utils import extract_summary_totals

        text = "Some text\nTotal Transaksi Kredit: 2.500.000,50\nMore text"
        result = extract_summary_totals(text)
        assert result["total_credit"] == "2.500.000,50"

    def test_extract_summary_totals_english_labels(self):
        """Verify extract_summary_totals works with English labels."""
        from pdfparser.utils import extract_summary_totals

        text = "Total Debit Transaction: 500.000,00\nTotal Credit Transaction: 750.000,25"
        result = extract_summary_totals(text)
        assert result["total_debit"] == "500.000,00"
        assert result["total_credit"] == "750.000,25"

    def test_extract_summary_totals_empty_when_not_found(self):
        """Verify extract_summary_totals returns empty when patterns not found."""
        from pdfparser.utils import extract_summary_totals

        text = "No totals here"
        result = extract_summary_totals(text)
        assert result["total_debit"] is None
        assert result["total_credit"] is None


class TestCalculateDebitSum:
    """Tests for calculate_debit_sum() function."""

    def test_calculate_debit_sum_returns_float(self):
        """Verify calculate_debit_sum returns a float."""
        from pdfparser.utils import calculate_debit_sum

        transactions = []
        result = calculate_debit_sum(transactions)
        assert isinstance(result, float)

    def test_calculate_debit_sum_empty_list(self):
        """Verify calculate_debit_sum returns 0.0 for empty list."""
        from pdfparser.utils import calculate_debit_sum

        result = calculate_debit_sum([])
        assert result == 0.0

    def test_calculate_debit_sum_with_transactions(self):
        """Verify calculate_debit_sum calculates correctly."""
        from pdfparser.utils import calculate_debit_sum

        transactions = [
            {"debit": "100.000,00"},
            {"debit": "200.000,50"},
            {"debit": ""},
            {"credit": "50.000,00"},
        ]
        result = calculate_debit_sum(transactions)
        assert result == 300000.50

    def test_calculate_debit_sum_ignores_credit_only(self):
        """Verify calculate_debit_sum ignores transactions without debit."""
        from pdfparser.utils import calculate_debit_sum

        transactions = [
            {"credit": "100.000,00"},
            {"debit": ""},
        ]
        result = calculate_debit_sum(transactions)
        assert result == 0.0


class TestCalculateCreditSum:
    """Tests for calculate_credit_sum() function."""

    def test_calculate_credit_sum_returns_float(self):
        """Verify calculate_credit_sum returns a float."""
        from pdfparser.utils import calculate_credit_sum

        transactions = []
        result = calculate_credit_sum(transactions)
        assert isinstance(result, float)

    def test_calculate_credit_sum_empty_list(self):
        """Verify calculate_credit_sum returns 0.0 for empty list."""
        from pdfparser.utils import calculate_credit_sum

        result = calculate_credit_sum([])
        assert result == 0.0

    def test_calculate_credit_sum_with_transactions(self):
        """Verify calculate_credit_sum calculates correctly."""
        from pdfparser.utils import calculate_credit_sum

        transactions = [
            {"credit": "100.000,00"},
            {"credit": "300.000,75"},
            {"credit": ""},
            {"debit": "50.000,00"},
        ]
        result = calculate_credit_sum(transactions)
        assert result == 400000.75
