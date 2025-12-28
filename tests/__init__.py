"""
Test module for Indonesian Bank Statement PDF Parser.

This module contains pytest fixtures and shared test utilities.
"""

from pathlib import Path

# Path to test PDF files
TEST_PDF_DIR = Path(__file__).parent.parent / "source-pdf"
EXAMPLE_STATEMENT_PDF = TEST_PDF_DIR / "Example_statement.pdf"
