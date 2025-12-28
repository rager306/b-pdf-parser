# Indonesian Bank Statement PDF Parser

A high-performance Python parser for Indonesian bank statements (Rekening Koran) with support for multiple PDF parsing libraries, turnover verification, and batch processing.

## Features

- **Native PDF parsing** (no OCR) - Supports PyMuPDF, pdfplumber, pypdf, and pdf_oxide
- **Multiple parser implementations** with automatic fallback
- **Turnover verification** - Compares PDF summary totals against calculated transaction sums
- **Extended metadata extraction** - account_no, business_unit, product_name, statement_date, valuta, unit_address, transaction_period, opening_balance, closing_balance, total_debit, total_credit
- **Multiprocessing support** for batch processing (2,000+ files tested)
- **Performance benchmarking** - ~468 docs/sec with PyMuPDF (2,000 files, 10 workers)
- **Regex optimization** - Pre-compiled patterns for 3% performance improvement
- **Comprehensive test suite** with 72+ tests
- **Handles both English and Indonesian** bank statement formats
- **UV package management** for reproducible environments

## Installation

### Requirements

- Python 3.9+
- UV (recommended)

### Setup with UV

```bash
# Install UV if not available
curl -LsSf https://astral.sh/uv/install.sh | sh

# Clone and setup
git clone <repo-url>
cd b-pdf-parser

# Sync dependencies (creates .venv with Python 3.9)
uv sync --python python3.9

# Activate virtual environment
source .venv/bin/activate  # On Linux/macOS
# or: .venv\Scripts\activate  # On Windows
```

### Alternative Setup with pip

```bash
# Create virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate  # On Linux/macOS

# Install dependencies
pip install -r requirements.txt
```

## Usage

### Function Interface

```python
from pdfparser import parse_pdf

# Parse a single PDF (default: PyMuPDF parser)
result = parse_pdf('path/to/statement.pdf')

# Access metadata
print(result['metadata']['account_no'])
print(result['metadata']['business_unit'])
print(result['metadata']['valuta'])  # Currency (IDR)
print(result['metadata']['transaction_period'])  # Date range

# Access summary totals
print(result['metadata']['total_debit'])
print(result['metadata']['total_credit'])
print(result['metadata']['opening_balance'])
print(result['metadata']['closing_balance'])

# Access transactions
for txn in result['transactions']:
    print(f"{txn['date']}: {txn['description']} - {txn['balance']}")
```

### Class Interface

```python
from pdfparser import PDFParser

# Create parser with default settings (PyMuPDF parser)
parser = PDFParser()
result = parser.parse('statement.pdf')

# Custom parser settings
parser = PDFParser(parser='pymupdf', verify_turnover=True)
result = parser.parse('statement.pdf')

# Access results
print(result['metadata']['account_no'])
print(f"Transactions: {len(result['transactions'])}")
```

### Choosing a Parser

The library supports multiple PDF parsing backends:

```python
# Use PyMuPDF (default, fastest for column-based format)
result = parse_pdf('statement.pdf', parser='pymupdf')

# Use pdfplumber (better table extraction, text fallback)
result = parse_pdf('statement.pdf', parser='pdfplumber')

# Use pypdf (pure Python, no external dependencies)
result = parse_pdf('statement.pdf', parser='pypdf')

# Use pdf_oxide (Rust-based PDF parsing)
result = parse_pdf('statement.pdf', parser='pdfoxide')
```

| Parser | Speed (2000 files) | Avg Time/File | Best For |
|--------|-------------------|---------------|----------|
| PyMuPDF | **~468 docs/sec** | 0.0208s | Column-based transaction format |
| pypdf | ~15 docs/sec | 0.3978s | Portability, pure Python |
| pdf_oxide | ~22 docs/sec | 0.0463s | Rust-based, modern PDF handling |
| pdfplumber | ~9 docs/sec | 0.6639s | Table extraction + inline text format |

### Turnover Verification

Enable automatic verification of transaction totals:

```python
# Enable via .env: VERIFY_TURNOVER=true
# Or via parameter
result = parse_pdf('statement.pdf', verify_turnover=True)

# Verification results
if 'verification' in result:
    print(f"Passed: {result['verification']['passed']}")
    print(f"Debit match: {result['verification']['debit_match']}")
    print(f"Credit match: {result['verification']['credit_match']}")
```

Or use directly:

```python
from pdfparser.utils import verify_turnover

verification = verify_turnover(transactions, summary_text=full_text)
print(verification['status'])  # 'passed', 'failed', 'not_available'
```

### Utility Functions

```python
from pdfparser.utils import (
    extract_metadata,
    extract_transactions,
    extract_summary_totals,
    verify_turnover,
    save_metadata_csv,
    save_transactions_csv,
    is_valid_parse,
    ensure_output_dirs,
    load_config
)

# Load configuration from .env
config = load_config()
print(f"Output directory: {config['output_dir']}")
print(f"Verify turnover: {config['verify_turnover']}")

# Extract metadata from text
metadata = extract_metadata(text)
# Returns: account_no, business_unit, product_name, statement_date,
#          valuta, unit_address, transaction_period, opening_balance,
#          closing_balance, total_debit, total_credit

# Extract transactions from text
transactions = extract_transactions(text)

# Extract summary totals
summary = extract_summary_totals(text)
# Returns: opening_balance, total_debit, total_credit, closing_balance

# Verify turnover
verification = verify_turnover(transactions, summary_text=text)

# Save to CSV files
save_metadata_csv(metadata, 'output/metadata/statement.csv')
save_transactions_csv(transactions, 'output/transactions/statement.csv')

# Validate parsing quality
if is_valid_parse(metadata, transactions):
    print("Parse successful")
```

## Output Format

CSV files use semicolon (;) as delimiter and standard number format (without thousand separators).

### Metadata CSV (metadata.csv)

```csv
Field;Value
account_no;041901001548309
business_unit;KC Kalimalang
product_name;Giro Umum
statement_date;08/12/23
valuta;IDR
unit_address;Jl. Kalimalang Blok C3 No.6 Rt.011 Rw.07 Kec. Duren Sawit, Jakarta Timur
transaction_period;01/11/23 - 30/11/23
opening_balance;269872497.00
closing_balance;297930854.00
total_debit;47104.00
total_credit;28105461.00
```

### Transactions CSV (transactions.csv)

```csv
Date;Description;User;Debit;Credit;Balance
03/11/23 04:14:59;NBMB UJANG SUMARWAN TO...;8888083;0.00;25000.00;269897497.00
03/11/23 04:15:30;Transfer Via BRImo;8888123;150000.00;0.00;269747497.00
```

**Number Format:** Indonesian format (1.000.000,00) is converted to standard format (1000000.00) without thousand separators.

## Configuration

### Environment Variables

Create a `.env` file in the project root:

```bash
cp .env.example .env
```

### Available Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `SOURCE_PDF_DIR` | `source-pdf` | Directory containing source PDF bank statements |
| `OUTPUT_DIR` | `output` | Directory where parsed CSV files are saved |
| `TEST_PDFS_DIR` | `test-pdfs` | Directory for synthetic test PDFs (benchmarking) |
| `VERIFY_TURNOVER` | `false` | Enable turnover verification ('true' or 'false') |

### Custom Paths

To use custom paths, create `.env`:

```
SOURCE_PDF_DIR=/data/bank-statements
OUTPUT_DIR=/results/parsed
TEST_PDFS_DIR=/tmp/test-data
VERIFY_TURNOVER=true
```

## Multiprocessing

For processing large batches (1000+ files):

```python
from pdfparser import batch_parse, batch_parse_from_directory

# Process multiple specific files in parallel
pdf_files = ['file1.pdf', 'file2.pdf', ...]
results = batch_parse(
    paths=pdf_files,
    parser_name='pymupdf',
    max_workers=8,  # Use 8 CPU cores
    output_dir='output'
)

# Process all PDFs in a directory
results = batch_parse_from_directory(
    directory='/path/to/pdfs',
    parser_name='pymupdf',
    max_workers=8
)
```

**Output:** Results are saved to CSV files:
- `output/metadata/{filename}_metadata.csv`
- `output/transactions/{filename}_transactions.csv`

**Returns:** Dict with `total`, `successful`, `failed`, `success_rate`, and `results` list.

## Benchmarking

Run performance benchmarks to compare all PDF parsers against your test dataset.

### Quick Start

```bash
# Benchmark all parsers with 100 PDFs (default)
uv run python benchmark.py --test-dir source-pdf

# Benchmark only PyMuPDF parser with 1000 PDFs
uv run python benchmark.py --test-dir source-pdf --parsers=pymupdf --max-files 1000

# Compare all parsers with 500 PDFs using 8 workers
uv run python benchmark.py --test-dir source-pdf --max-files 500 --max-workers 8
```

### Generate Test Data

Create synthetic bank statement PDFs for benchmarking:

```bash
# Generate 100 test PDFs (default)
python generate_test_pdfs.py

# Generate 1000 PDFs with custom settings
python generate_test_pdfs.py --num=1000 --min-pages 2 --max-pages 5 --min-transactions 200 --max-transactions 400

# Generate 20000 PDFs for full benchmark
python generate_test_pdfs.py --num=20000 --output-dir source-pdf
```

### Benchmark Options

| Option | Description | Default |
|--------|-------------|---------|
| `--parsers` | Comma-separated parser list: pymupdf, pdfplumber, pypdf, pdfoxide, all | all |
| `--test-dir` | Directory containing PDF files | **Required** |
| `--max-files` | Maximum number of PDFs to process | All files |
| `--max-workers` | Number of parallel workers | 4 |

### Example Commands

```bash
# Quick test with 50 PDFs
uv run python benchmark.py --test-dir source-pdf --max-files 50

# Compare PyMuPDF vs pdf_oxide with 500 PDFs
uv run python benchmark.py --test-dir source-pdf --parsers=pymupdf,pdfoxide --max-files 500

# Full benchmark with all parsers and 2000 PDFs using 10 workers
uv run python benchmark.py --test-dir source-pdf --max-files 2000 --max-workers 10
```

### Performance Results (2,000 PDFs, 10 Workers)

Benchmark run: 2025-12-28 | Workers: 10 | Files: 2,000

| Parser | Time (total) | Speed | Avg Time/File | Success Rate |
|--------|--------------|-------|---------------|--------------|
| **PyMuPDF** | ~4.3s | **~468 docs/sec** | 0.0208s | 100% |
| pypdf | ~136s | ~15 docs/sec | 0.3978s | 100% |
| pdf_oxide | ~93s | ~22 docs/sec | 0.0463s | 0% (validation fails) |
| pdfplumber | ~226s | ~9 docs/sec | 0.6639s | 100% |

**Key Findings:**
- PyMuPDF is **~32x faster** than pdfplumber and **~20x faster** than pypdf
- PyMuPDF achieves **0.0208s average** per file with 10 workers
- All parsers (except pdfoxide) achieve 100% success rate on test dataset
- pdf_oxide parses successfully but fails validation (structure mismatch)
- Regex optimization: Pre-compiled patterns provide ~3% improvement

### Recommended Configuration

For optimal performance on production workloads:
- **Parser**: PyMuPDF (default)
- **Workers**: 8-10 (match CPU cores)
- **Expected throughput**: 400-500 docs/sec (varies by PDF complexity)

### Output Files

Benchmark results are saved to:
- `output/benchmark_results.csv` - Detailed per-file results

### Interpreting Results

The benchmark outputs:
- **Files**: Total PDFs processed
- **Success/Failed**: Parse outcomes
- **Success Rate**: Percentage of valid parses
- **Avg Time/File**: Average parsing time per document
- **Avg Txns/File**: Average transactions extracted per file

## API Reference

### parse_pdf(path: str, parser: str = 'pymupdf', verify_turnover: bool = None) -> dict

Parse a PDF bank statement file.

**Parameters:**
- `path`: Path to PDF file
- `parser`: Parser to use ('pymupdf', 'pdfplumber', 'pypdf', 'pdfoxide')
- `verify_turnover`: Enable turnover verification (overrides .env setting)

**Returns:** dict with 'metadata', 'transactions', and optionally 'verification' keys

### PDFParser

Class-based interface for parsing Indonesian bank statement PDFs.

```python
from pdfparser import PDFParser

# Create parser
parser = PDFParser(parser='pymupdf', verify_turnover=None)

# Parse PDF
result = parser.parse('statement.pdf')
```

**Constructor Parameters:**
- `parser`: Parser to use ('pymupdf', 'pdfplumber', 'pypdf', 'pdfoxide')
- `verify_turnover`: Enable turnover verification (True/False/None for .env default)

**Methods:**
- `parse(path: str) -> dict`: Parse a PDF file (returns same result as parse_pdf())

### batch_parse(paths: list[str], parser_name: str = 'pymupdf', max_workers: int = None, output_dir: str = None) -> dict

Process multiple PDF files in parallel using ProcessPoolExecutor.

**Returns:** dict with keys:
- `total`: Total files processed
- `successful`: Number of successful parses
- `failed`: Number of failed parses
- `success_rate`: Percentage of successful parses
- `results`: List of individual file results

## Project Structure

```
b-pdf-parser/
├── pdfparser/              # Main parser module
│   ├── __init__.py        # Public API, parse_pdf() dispatcher
│   ├── batch.py           # Batch processing module (ProcessPoolExecutor)
│   ├── pymupdf_parser.py  # PyMuPDF implementation (fastest)
│   ├── pdfplumber_parser.py # pdfplumber implementation
│   ├── pypdf_parser.py    # pypdf implementation (pure Python)
│   ├── pdfoxide_parser.py # pdf_oxide implementation (Rust-based)
│   └── utils.py           # Shared utilities (regex, CSV, verification)
├── tests/                  # Test suite with pytest
│   ├── test_parsers.py    # Parser integration tests
│   └── test_utils.py      # Utility function tests (72+ tests)
├── source-pdf/            # Sample PDFs (21,000+ files for benchmarking)
├── test-pdfs/             # Generated test dataset
├── output/                # Parsed results
│   ├── metadata/         # Metadata CSV outputs
│   └── transactions/     # Transaction CSV outputs
├── .venv/                 # Virtual environment (UV)
├── pyproject.toml         # Project configuration (UV)
├── requirements.txt       # Dependencies
├── benchmark.py           # Performance benchmarking tool
├── generate_test_pdfs.py  # Synthetic test PDF generator
├── README.md             # This file
└── CHANGELOG.md          # Version history
```

## Testing

### Run Tests

```bash
uv run pytest tests/ -v
```

**Test Coverage:**
- `tests/test_parsers.py`: Parser integration tests
- `tests/test_utils.py`: Utility function tests with property-based testing

**72+ tests** with parametrized test cases covering all 4 parsers.

### Code Quality

```bash
# Lint with ruff
uv run ruff check pdfparser/ tests/

# Type check with pyrefly
uv run pyrefly check pdfparser/

# Fix linting issues automatically
uv run ruff check --fix pdfparser/
```

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Contributing

Contributions welcome! Please ensure:

- Python 3.9 compatibility
- English documentation and comments
- Unit tests for new features
- All linters pass (ruff, pyrefly)
