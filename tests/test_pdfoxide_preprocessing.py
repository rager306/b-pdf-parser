import pytest
from pdfparser.pdfoxide_parser import preprocess_text

def test_preprocess_smashed_amounts_simple():
    """Test separating two smashed amounts."""
    text = "Value: 0.0026,000.00 End"
    # Expect newline separation because parser expects fields on separate lines
    expected = "Value: 0.00\n26,000.00 End"
    assert preprocess_text(text) == expected

def test_preprocess_smashed_amounts_triple():
    """Test separating three smashed amounts (requires multiple passes)."""
    # 0.00 + 100.00 + 200.00 smashed
    text = "0.00100.00200.00"
    expected = "0.00\n100.00\n200.00"
    assert preprocess_text(text) == expected

def test_preprocess_smashed_amounts_with_commas():
    """Test smashed amounts that contain commas."""
    # 1,234.56 + 7,890.00
    text = "1,234.567,890.00"
    expected = "1,234.56\n7,890.00"
    assert preprocess_text(text) == expected

def test_preprocess_no_change():
    """Test text that doesn't need changes."""
    text = "Normal text 100.00\n200.00"
    assert preprocess_text(text) == text

def test_preprocess_multiline():
    """Test processing on multiple lines."""
    text = "Line 1\n0.0026,000.00\nLine 3"
    expected = "Line 1\n0.00\n26,000.00\nLine 3"
    assert preprocess_text(text) == expected
