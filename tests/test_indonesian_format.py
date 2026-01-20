
import pytest
from pdfparser.utils import extract_transactions

class TestIndonesianFormat:
    """Tests for Indonesian number format extraction."""

    def test_extract_indonesian_format_transactions(self):
        """Verify extraction of transactions with Indonesian number format."""
        text = """
01/01/23 10:00:00
Transfer
User123
10.000,00
0,00
1.000.000,00
"""
        transactions = extract_transactions(text)

        assert len(transactions) == 1
        txn = transactions[0]

        # In this specific text layout, User123 is treated as description because
        # it is not on the same line as amount and doesn't match User ID pattern.
        # But crucially, '10.000,00' should be identified as DEBIT amount,
        # not mistakenly as User ID.

        assert txn["debit"] == "10.000,00"
        assert txn["credit"] == "0,00"
        assert txn["balance"] == "1.000.000,00"

        # Ensure it wasn't misclassified as User
        # (If misclassified, user would be "10.000,00" and debit would be empty)
        assert txn["user"] != "10.000,00"

    def test_extract_indonesian_format_no_user_id(self):
        """Verify extraction when User ID is missing and amounts are Indonesian format."""
        text = """
01/01/23 10:00:00
Transfer
10.000,00
0,00
1.000.000,00
"""
        transactions = extract_transactions(text)

        assert len(transactions) == 1
        txn = transactions[0]

        assert txn["debit"] == "10.000,00"
        assert txn["credit"] == "0,00"
        assert txn["balance"] == "1.000.000,00"

        # Verify it wasn't misclassified as User
        assert txn["user"] == ""

    def test_extract_us_format_transactions(self):
        """Verify extraction of transactions with US number format (sanity check)."""
        text = """
01/01/23 10:00:00
Transfer
User123
10000.00
0.00
1000000.00
"""
        transactions = extract_transactions(text)

        assert len(transactions) == 1
        txn = transactions[0]

        assert txn["debit"] == "10000.00"
        assert txn["credit"] == "0.00"
        assert txn["balance"] == "1000000.00"
