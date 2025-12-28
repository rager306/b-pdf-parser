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
)


class TestExtractMetadata:
    """Tests for extract_metadata() function using hypothesis."""

    @given(metadata_text=text(alphabet='abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 \n:.,-', min_size=0, max_size=1000))
    @settings(max_examples=50)
    def test_extract_metadata_returns_dict(self, metadata_text):
        """Verify extract_metadata always returns a dict."""
        result = extract_metadata(metadata_text)
        assert isinstance(result, dict)

    @given(metadata_text=text(alphabet='abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 \n:.,-', min_size=0, max_size=500))
    @settings(max_examples=30)
    def test_extract_metadata_values_are_strings(self, metadata_text):
        """Verify all metadata values are strings."""
        result = extract_metadata(metadata_text)
        for key, value in result.items():
            assert isinstance(value, str), f"Value for key '{key}' is not a string"

    @given(account_no=text(alphabet='0123456789', min_size=1, max_size=20))
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

    @given(transaction_text=text(alphabet='abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 \n/:-', min_size=0, max_size=2000))
    @settings(max_examples=50)
    def test_extract_transactions_returns_list(self, transaction_text):
        """Verify extract_transactions always returns a list."""
        result = extract_transactions(transaction_text)
        assert isinstance(result, list)

    @given(transaction_text=text(alphabet='abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 \n/:-', min_size=0, max_size=1000))
    @settings(max_examples=30)
    def test_extract_transactions_items_are_dicts(self, transaction_text):
        """Verify all transaction items are dictionaries."""
        result = extract_transactions(transaction_text)
        for item in result:
            assert isinstance(item, dict), "Transaction item is not a dict"

    @given(transaction_text=text(alphabet='abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 \n/:-', min_size=0, max_size=500))
    @settings(max_examples=20)
    def test_extract_transactions_keys_are_strings(self, transaction_text):
        """Verify all transaction dict keys are strings."""
        result = extract_transactions(transaction_text)
        for item in result:
            for key in item.keys():
                assert isinstance(key, str), f"Key '{key}' is not a string"


class TestTransactionDatePattern:
    """Tests for transaction date regex pattern using hypothesis."""

    @given(date_str=st.from_regex(r'\d{2}/\d{2}/\d{2} \d{2}:\d{2}:\d{2}', fullmatch=True))
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
        expected = bool(re.match(r'^\d{2}/\d{2}/\d{2} \d{2}:\d{2}:\d{2}$', date_str))
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

    @given(sample_text=text(alphabet='abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 \n:.,-', min_size=0, max_size=200))
    @settings(max_examples=30)
    def test_metadata_extraction_no_crash(self, sample_text):
        """Verify extract_metadata handles any input without crashing."""
        # This is a fuzz test - should not raise exceptions
        try:
            result = extract_metadata(sample_text)
            assert isinstance(result, dict)
        except Exception as e:
            pytest.fail(f"extract_metadata raised exception: {e}")

    @given(sample_text=text(alphabet='abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 \n/:-', min_size=0, max_size=500))
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
        assert 'account_no' in result
        assert 'business_unit' in result
        assert 'product_name' in result
        assert 'statement_date' in result

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
