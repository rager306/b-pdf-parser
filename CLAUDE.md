# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Indonesian Bank Statement PDF Parser - extracts metadata and transactions from Indonesian bank statements (Rekening Koran) using regex-based parsing. Supports multiple PDF libraries (PyMuPDF, pdfplumber, pypdf).

## Commands

```bash
# Setup
python3 -m venv venv && source venv/bin/activate && pip install -r requirements.txt

# Lint
ruff check pdfparser/

# Type check
pyrefly check pdfparser/

# Parse a PDF
python3 -c "from pdfparser import parse_pdf; result = parse_pdf('source-pdf/Example_statement.pdf')"

# Test with all samples
python3 -c "
from pdfparser import parse_pdf, is_valid_parse
for pdf in ['source-pdf/Example_statement.pdf', 'source-pdf/NEW_REKENING_KORAN_ONLINE_041901001548309_2023-11-01_2023-11-30_00291071.pdf', 'source-pdf/NEW_REKENING_KORAN_ONLINE-JAN-2024.pdf']:
    result = parse_pdf(pdf)
    print(f'{pdf}: {len(result[\"transactions\"])} txns, valid={is_valid_parse(result[\"metadata\"], result[\"transactions\"])}')
"
```

## Architecture

```
pdfparser/
├── __init__.py        # Public API, parse_pdf() dispatcher
├── utils.py           # Regex patterns, extract_metadata(), extract_transactions(), CSV I/O
└── pymupdf_parser.py  # PyMuPDF implementation (pdfplumber, pypdf pending)
```

**Data flow**: PDF → Parser library (fitz) → Text extraction → `extract_metadata()`/`extract_transactions()` → Dict output

**Output format**:
- `metadata`: {account_no, business_unit, product_name, statement_date}
- `transactions`: [{date, description, user, debit, credit, balance}]

## Key Patterns

**PDF text structure**: Metadata fields are label:value on separate lines. Transactions have date+time on one line, description on next, then user/debit/credit/balance each on separate lines.

**Regex patterns** in `utils.py` handle multiline field extraction. `TRANSACTION_DATE_PATTERN` anchors at `DD/MM/YY HH:MM:SS`.

**Validation**: `is_valid_parse()` checks metadata has 2+ non-empty fields, transactions list has entries, each has date and balance.

## Python 3.9 Compatibility

Use `List`, `Dict` from `typing` (not built-in generics). PyMuPDF pinned to 1.26.5.
