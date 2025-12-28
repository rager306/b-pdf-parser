# Indonesian Bank Statement PDF Parser

A high-performance Python parser for Indonesian bank statements (Rekening Koran) with support for multiple PDF parsing libraries.

## Features

- Native PDF parsing (no OCR)
- Multiple parser implementations (PyMuPDF, pdfplumber, pypdf, pdfoxide)
- Multiprocessing support for batch processing (1000+ files)
- Performance benchmarking tools with ProcessPoolExecutor
- Comprehensive test suite with pytest and hypothesis property-based testing
- Synthetic test data generator for benchmark validation
- Python 3.9 compatible
- Handles both English and Indonesian bank statement formats
- UV package management for reproducible environments

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

### Basic Usage

```python
from pdfparser import parse_pdf

# Parse a single PDF (default: PyMuPDF parser)
result = parse_pdf('path/to/statement.pdf')

# Access metadata
print(result['metadata']['account_no'])
print(result['metadata']['product_name'])

# Access transactions
for txn in result['transactions']:
    print(f"{txn['date']}: {txn['description']} - {txn['balance']}")
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

| Parser | Speed | Best For |
|--------|-------|----------|
| PyMuPDF | Fastest | Column-based transaction format |
| pdfplumber | Fast | Table extraction + inline text format |
| pypdf | Medium | Portability, pure Python, multiprocessing safety |
| pdf_oxide | Fast | Rust-based, modern PDF handling |

**Note:** Both parsers handle both Indonesian and English bank statement labels automatically.

### Utility Functions

```python
from pdfparser.utils import (
    extract_metadata,
    extract_transactions,
    save_metadata_csv,
    save_transactions_csv,
    is_valid_parse,
    ensure_output_dirs,
    load_config
)

# Load configuration from .env
config = load_config()
print(f"Output directory: {config['output_dir']}")

# Extract metadata from text
metadata = extract_metadata(text)

# Extract transactions from text
transactions = extract_transactions(text)

# Save to CSV files
save_metadata_csv(metadata, 'output/metadata/statement.csv')
save_transactions_csv(transactions, 'output/transactions/statement.csv')

# Validate parsing quality
if is_valid_parse(metadata, transactions):
    print("Parse successful")

# Ensure output directories exist (with config)
ensure_output_dirs(config)

# Or let it auto-load config
ensure_output_dirs()  # Uses load_config() internally
```

## Output Format

### Metadata CSV

| Field | Value |
|-------|-------|
| Account No | 041901001548309 |
| Business Unit | KC Kalimalang |
| Product Name | Giro Umum-IDR |
| Statement Date | 01/11/2023 - 30/11/2023 |

### Transactions CSV

| Date | Description | User | Debit | Credit | Balance |
|------|-------------|------|-------|--------|---------|
| 03/11/23 04:14:59 | NBMB UJANG SUMARWAN TO... | 8888083 | 0.00 | 25,000.00 | 269,897,497.00 |

## Configuration

### Requirements

```
PyMuPDF==1.26.5          # Python 3.9 compatible version
pdfplumber>=0.10.0       # Tested on Python 3.9
pypdf>=3.0.0             # Pure Python, 3.9 compatible
pdf-oxide>=0.2.2         # Rust-based PDF parsing
reportlab>=4.0.0         # For generating synthetic PDFs
tabulate>=0.9.0          # For formatted benchmark tables
python-dotenv>=1.0.0     # Environment variable management
```

**Note:** PyMuPDF is pinned to 1.26.5 for Python 3.9 compatibility. Newer versions require Python 3.10+.

## Environment Variables

The parser uses environment variables for path configuration. Create a `.env` file in the project root (copy from `.env.example`):

```bash
cp .env.example .env
```

### Available Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `SOURCE_PDF_DIR` | `source-pdf` | Directory containing source PDF bank statements |
| `OUTPUT_DIR` | `output` | Directory where parsed CSV files are saved |
| `TEST_PDFS_DIR` | `test-pdfs` | Directory for synthetic test PDFs (benchmarking) |

### Usage Example

```python
from pdfparser import load_config, ensure_output_dirs

# Load configuration from .env
config = load_config()
print(config['output_dir'])  # 'output' or custom value from .env

# Create output directories using config
ensure_output_dirs(config)

# Or let it auto-load config
ensure_output_dirs()  # Uses load_config() internally
```

### Custom Paths

To use custom paths, create `.env`:

```
SOURCE_PDF_DIR=/data/bank-statements
OUTPUT_DIR=/results/parsed
TEST_PDFS_DIR=/tmp/test-data
```

**Note:** Paths can be relative (to project root) or absolute.

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

### Performance

- Target: <2 seconds per page
- Tested on: 19/152 CPU, 258 GB RAM
- Accuracy: 90%+ success rate on Indonesian bank statements

## Benchmarking

Compare parser performance:

```bash
python benchmark.py --parsers all --test-dir test-pdfs --max-files 1000 --max-workers 8
```

Options:

- `--parsers`: `all`, `pymupdf`, `pdfplumber`, `pypdf`, `pdfoxide`
- `--test-dir`: Directory containing PDF files
- `--max-files`: Maximum number of files to test
- `--max-workers`: Number of parallel workers

Results saved to `benchmark_results.csv` with metrics:
- Parse time per file and per page
- Success rate (using is_valid_parse)
- Transaction extraction counts

### Generate Test Data

Create synthetic bank statement PDFs for benchmarking:

```bash
# Generate 100 test PDFs (default)
python generate_test_pdfs.py

# Generate 50 PDFs with custom settings
python generate_test_pdfs.py --num=50 --min-pages 2 --max-pages 5 --min-transactions 200 --max-transactions 400

# Custom output directory
python generate_test_pdfs.py --num=100 --output-dir /path/to/test-pdfs
```

Options:

- `--num`: Number of PDFs to generate (default: 100)
- `--output-dir`: Output directory (default: test-pdfs)
- `--min-pages`/`--max-pages`: Pages per PDF (default: 1-10)
- `--min-transactions`/`--max-transactions`: Transactions per page (default: 100-500)

## API Reference

### parse_pdf(path: str, parser: str = 'pymupdf') -> dict

Parse a PDF bank statement file.

**Parameters:**
- `path`: Path to PDF file
- `parser`: Parser to use ('pymupdf', 'pdfplumber', 'pypdf', 'pdfoxide')

**Returns:** dict with 'metadata' and 'transactions' keys

**Raises:**
- `ValueError`: If parser name is invalid
- `FileNotFoundError`: If PDF file doesn't exist

### extract_metadata(text: str) -> dict

Extract metadata fields from bank statement text.

**Parameters:**
- `text`: Full text extracted from PDF first page

**Returns:** dict with keys: account_no, business_unit, product_name, statement_date

### extract_transactions(text: str) -> list[dict]

Extract transaction rows from bank statement text.

**Parameters:**
- `text`: Full text extracted from all PDF pages

**Returns:** list of dicts with keys: date, description, user, debit, credit, balance

### is_valid_parse(metadata: dict, transactions: list[dict]) -> bool

Validate parsing success based on minimum data quality requirements.

**Returns:** True if parse is valid, False otherwise

### batch_parse(paths: list[str], parser_name: str = 'pymupdf', max_workers: int = None, output_dir: str = None) -> dict

Process multiple PDF files in parallel using ProcessPoolExecutor.

**Parameters:**
- `paths`: List of paths to PDF files
- `parser_name`: Parser to use ('pymupdf', 'pdfplumber', 'pypdf', 'pdfoxide')
- `max_workers`: Number of parallel workers (default: CPU count)
- `output_dir`: Output directory for CSVs (default: from config)

**Returns:** dict with keys:
- `total`: Total files processed
- `successful`: Number of successful parses
- `failed`: Number of failed parses
- `success_rate`: Percentage of successful parses
- `results`: List of individual file results

### batch_parse_from_directory(directory: str, parser_name: str = 'pymupdf', max_workers: int = None, output_dir: str = None, pattern: str = '**/*.pdf') -> dict

Process all PDF files in a directory and its subdirectories.

**Parameters:**
- `directory`: Directory to search for PDFs
- `parser_name`: Parser to use
- `max_workers`: Number of parallel workers
- `output_dir`: Output directory for CSVs
- `pattern`: Glob pattern for file discovery

**Returns:** dict with same keys as batch_parse()

## Project Structure

```
b-pdf-parser/
├── pdfparser/              # Main parser module
│   ├── __init__.py        # Public API, parse_pdf() dispatcher
│   ├── batch.py           # Batch processing module (ProcessPoolExecutor)
│   ├── pymupdf_parser.py  # PyMuPDF implementation (fast, column-based parsing)
│   ├── pdfplumber_parser.py # pdfplumber implementation (table extraction + text fallback)
│   ├── pypdf_parser.py    # pypdf implementation (pure Python, portable)
│   ├── pdfoxide_parser.py # pdf_oxide implementation (Rust-based)
│   └── utils.py           # Shared utilities (regex, CSV, validation)
├── tests/                  # Test suite with pytest and hypothesis
│   ├── __init__.py        # Test module with shared fixtures
│   ├── test_parsers.py    # Parser integration tests (44 tests)
│   └── test_utils.py      # Utility function tests with property-based testing
├── source-pdf/            # Sample PDFs for testing
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
- `tests/test_parsers.py`: Parser integration tests (TestPdfoxideParser, TestAllParsersConsistency, TestIsValidParse, TestReportlabPdfGeneration)
- `tests/test_utils.py`: Utility function tests with hypothesis property-based testing (TestExtractMetadata, TestExtractTransactions, TestTransactionDatePattern, TestMetadataPatterns, TestEdgeCases)

**44 tests total** with parametrized test cases covering all 4 parsers.

### Code Quality

```bash
# Lint with ruff
uv run ruff check pdfparser/ tests/ benchmark.py generate_test_pdfs.py

# Type check with pyrefly
uv run pyrefly check pdfparser/ tests/ benchmark.py generate_test_pdfs.py

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
