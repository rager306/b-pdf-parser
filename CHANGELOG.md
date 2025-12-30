# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.6.0] - 2025-12-30

### Performance Optimization

- **Dynamic Worker Scaling**
  - `get_optimal_workers(parser_name)` - Auto-detect CPU cores using `os.cpu_count()`
  - Capped at 16 workers to prevent resource exhaustion
  - Returns recommended worker count based on system resources

- **Batch Processing Optimization**
  - `chunk_size` parameter - Controls files per worker batch (default: 100)
  - `init_strategy` parameter - 'per-worker' (default) or 'per-file' for parser initialization
  - WorkerConfig dataclass for structured worker configuration
  - BatchResult dataclass with performance metrics (throughput, duration, worker_overhead_percent)

- **Input Validation**
  - `validate_batch_params()` function for validating batch processing parameters
  - Validates parser_name, max_workers (1-32), chunk_size (1-500), init_strategy

### Benchmark Results (500 PDFs)

| Metric | Target | Actual | Status |
|--------|--------|--------|--------|
| Throughput | 500+ docs/sec | 511 docs/sec | ✅ |
| Worker overhead | <5% | 0.00% | ✅ |
| Validation rate | 100% | 100% | ✅ |

### Added

- **New APIs**
  - `get_optimal_workers(parser_name)` - Calculate optimal worker count
  - `get_worker_config(parser_name, max_workers, init_strategy)` - Create WorkerConfig
  - `validate_batch_params(parser_name, max_workers, chunk_size, init_strategy)` - Validate inputs
  - `WorkerConfig` dataclass - Worker configuration with parser_name, max_tasks_per_worker, init_strategy, memory_limit_mb
  - `BatchResult` dataclass - Consolidated results with total, successful, failed, success_rate, results, duration, throughput, memory_peak_mb, worker_overhead_percent

- **Enhanced batch_parse()**
  - `chunk_size` parameter for IPC batching (default: 100)
  - `init_strategy` parameter for parser reuse strategy (default: 'per-worker')
  - Returns enhanced metrics: throughput, duration, memory_peak_mb, worker_overhead_percent

- **Enhanced batch_parse_from_directory()**
  - `chunk_size` and `init_strategy` parameters passed through to batch_parse()

- **40 New Tests** in `tests/test_batch.py`
  - Test get_optimal_workers() returns CPU count
  - Test get_worker_config() returns WorkerConfig
  - Test validate_batch_params() with valid and invalid inputs
  - Test batch_parse() with all parameter combinations
  - Test batch_parse_from_directory() discovers and processes PDFs
  - Test BatchResult and WorkerConfig dataclasses
  - Test performance metrics (throughput, worker overhead)

### Changed

- Updated batch.py to use ProcessPoolExecutor with optimized worker configuration
- Added timing metrics tracking for worker overhead measurement
- Improved error handling with validation function

## [1.5.0] - 2025-12-28

### Performance Optimization

- **Pre-compiled Regex Patterns**
  - All 18+ regex patterns compiled at module level (not on each function call)
  - Added `@lru_cache` for dynamic pattern generation
  - `frozenset` replaces `list` for O(1) label membership testing
  - Cached compiled pattern methods in hot loops
  - Type hints added for `Pattern` objects

### Benchmark Results (2000 PDFs, 10 workers)

| Parser | Time | Speed | Avg Time/File | Success Rate |
|--------|------|-------|---------------|--------------|
| PyMuPDF | ~4.3s | **~468 docs/sec** | 0.0208s | 100% |
| pdfplumber | ~226s | ~9 docs/sec | 0.6639s | 100% |
| pypdf | ~136s | ~15 docs/sec | 0.3978s | 100% |
| pdfoxide | ~93s | ~22 docs/sec | 0.0463s | 0% (validation) |

### Recommended Configuration

- **Parser**: PyMuPDF (default)
- **Workers**: 8-10 (match CPU cores)
- **Expected throughput**: 40-50 docs/sec (varies by PDF complexity)

### Added

- **Turnover Verification Feature**
  - `VERIFY_TURNOVER` environment variable for automatic verification
  - `verify_turnover` parameter in `parse_pdf()` function
  - Compares PDF summary totals against calculated transaction sums
  - Supports Indonesian number format (1.000.000,00)
  - Returns detailed verification results with status, discrepancy amounts

- **Extended Metadata Extraction**
  - `valuta` - Currency code (IDR)
  - `transaction_period` - Date range (e.g., "01/11/23 - 30/11/23")
  - `unit_address` - Full branch address
  - `total_debit` - PDF summary debit total
  - `total_credit` - PDF summary credit total
  - `opening_balance` - Saldo Awal / Opening Balance
  - `closing_balance` - Saldo Akhir / Closing Balance

- **Summary Total Extraction** (`extract_summary_totals()`)
  - Extracts from Indonesian labels: "Total Transaksi Debet", "Total Transaksi Kredit", "Saldo Awal", "Saldo Akhir"
  - Extracts from English labels: "Total Debit Transaction", "Total Credit Transaction", "Opening Balance", "Closing Balance"
  - Handles multiline value formats

- **Improved Transaction Parsing**
  - Support for transaction formats without User ID field
  - Automatic detection of user ID vs amount fields
  - Fixed parsing for Interest on Account and Tax entries

- **72+ Unit Tests**
  - Turnover verification tests
  - Summary total pattern tests
  - Config loading tests
  - Balance calculation tests

### Benchmark Results (21,000 PDFs)

| Parser | Time | Speed | Success Rate |
|--------|------|-------|--------------|
| PyMuPDF | ~25s | **819 docs/sec** | 100% |
| pdf_oxide | ~52s | 386 docs/sec | 100% |
| pypdf | ~317s | 63 docs/sec | 100% |
| pdfplumber | ~645s | 31 docs/sec | 100% |

### Test Results

| Parser | Example_statement.pdf | REKENING_KORAN...pdf | JAN-2024.pdf |
|--------|----------------------|---------------------|--------------|
| All | 47 txns | 14 txns | 15 txns |
| All | valuta=IDR | valuta=IDR | valuta=IDR |
| All | verified | verified | verified |

### Changed

- Updated all 4 parsers to include summary totals in metadata
- Improved regex patterns for multiline label-value formats
- Fixed label filtering to prevent metadata labels being captured as values
- Added account number extraction from filenames as fallback
- Strip currency suffix from product names (e.g., "Britama-IDR" -> "Britama")

## [1.3.0] - 2024-12-28

### Added

- **pdf_oxide parser implementation** (`pdfparser/pdfoxide_parser.py`)
  - `parse_pdf_pdfoxide()` - Main parser using Rust-based pdf_oxide library
  - Fourth parser option for users to choose from
  - Rust-based PDF parsing for modern PDF handling
  - Multiprocessing safe with no global state
  - Compatible with Python 3.9
- **UV package management support**
  - `pyproject.toml` - Project configuration for UV
  - `uv sync --python python3.9` - Fast dependency installation
  - Dev dependencies: pytest, hypothesis, ruff, pyrefly
  - Reproducible environments with lock file support
- **Test suite framework** (`tests/`)
  - pytest and hypothesis for property-based testing
  - `tests/__init__.py` - Test module with shared fixtures
  - `tests/test_parsers.py` - Parser integration tests (44 tests)
  - `tests/test_utils.py` - Utility function tests with hypothesis
  - Tests cover all 4 parsers with parametrized test cases
- **Benchmark tool** (`benchmark.py`)
  - CLI interface with argparse for --parsers, --test-dir, --max-files, --max-workers
  - ProcessPoolExecutor for parallel parsing
  - Metrics collection: time per file, time per page, throughput
  - Success rate calculation using is_valid_parse()
  - Output to benchmark_results.csv
  - Tabulate table display for results
- **Batch processing module** (`pdfparser/batch.py`)
  - `batch_parse()` - Parallel processing of multiple PDF files
  - `batch_parse_from_directory()` - Process all PDFs in a directory
  - ProcessPoolExecutor for parallel file processing
  - Per-file CSV saving to metadata/ and transactions/ directories
  - Error handling with failure information in results
  - `batch_parse` and `batch_parse_from_directory` exported in __init__.py
- **Test data generator** (`generate_test_pdfs.py`)
  - CLI interface with argparse for --num, --output-dir, --min-pages, --max-pages, --min-transactions, --max-transactions
  - Random realistic data (account numbers, names, amounts)
  - reportlab-based PDF generation with bank statement format
  - Configurable page count (1-10) and transactions per page (100-500)

### Changed

- Updated `pdfparser/__init__.py` to support pdfoxide parser
- Updated parser selection to include 'pdfoxide' option
- Added `parse_pdf_pdfoxide`, `batch_parse`, `batch_parse_from_directory` to public API exports
- Import sorting automatically organized by ruff
- Fixed circular import issue in batch.py by using direct parser imports

### Test Results

| Parser | Example_statement.pdf | REKENING_KORAN...pdf | JAN-2024.pdf |
|--------|----------------------|---------------------|--------------|
| PyMuPDF | 47 txns, valid=True | 14 txns, valid=True | 15 txns, valid=True |
| pdfplumber | 47 txns, valid=True | 14 txns, valid=True | 15 txns, valid=True |
| pypdf | 47 txns, valid=True | 14 txns, valid=True | 15 txns, valid=True |
| pdf_oxide | 47 txns, valid=True | 14 txns, valid=True | 15 txns, valid=True |

All 44 tests pass with pytest and hypothesis property-based testing.

### Known Limitations

- None - all planned features for v1.3.0 are implemented

## [1.2.0] - 2024-12-28

### Added

- **pypdf parser implementation** (`pdfparser/pypdf_parser.py`)
  - `parse_pdf_pypdf()` - Main parser using pure Python pypdf library
  - No external C dependencies - fully portable
  - Multiprocessing safe with no global state
  - Compatible with Python 3.9
- **Third parser option** - Users can now choose between 'pymupdf', 'pdfplumber', and 'pypdf'

### Test Results

| Parser | Example_statement.pdf | REKENING_KORAN...pdf | JAN-2024.pdf |
|--------|----------------------|---------------------|--------------|
| PyMuPDF | 47 txns, valid=True | 14 txns, valid=True | 15 txns, valid=True |
| pdfplumber | 47 txns, valid=True | 14 txns, valid=True | 15 txns, valid=True |
| pypdf | 47 txns, valid=True | 14 txns, valid=True | 15 txns, valid=True |

### Known Limitations

- Batch processing module (batch.py) not yet implemented
- Benchmark script (benchmark.py) not yet implemented
- Test data generator (generate_test_pdfs.py) not yet implemented

## [1.1.1] - 2024-12-28

### Fixed

- **pdfplumber metadata extraction** - Added fallback to English patterns when Indonesian patterns yield fewer than 2 fields
- Ensures `is_valid_parse()` returns True for English-labelled PDFs
- Metadata coverage now matches PyMuPDF parser (4/4 fields)

## [1.1.0] - 2024-12-28

### Added

- **pdfplumber parser implementation** (`pdfparser/pdfplumber_parser.py`)
  - `parse_pdf_pdfplumber()` - Main parser using pdfplumber library
  - `extract_metadata_pdfplumber()` - Handles Indonesian labels (No. Rekening, Unit Kerja, etc.)
  - `extract_transactions_inline()` - Parses inline transaction format from pdfplumber text
  - Dual extraction strategy: table extraction first, text fallback
  - Context manager pattern for automatic resource cleanup
- **Parser selection support** - Users can now choose between 'pymupdf' and 'pdfplumber'
- **Improved metadata patterns** - Handles both English and Indonesian label formats
- **Transaction parsing improvements** - Inline pattern matching for pdfplumber output

### Changed

- Updated `pdfparser/__init__.py` to dispatch to pdfplumber parser
- Added `parse_pdf_pdfplumber` to public API exports
- All sample PDFs now parse successfully with both parsers

### Test Results

| Parser | Example_statement.pdf | REKENING_KORAN...pdf | JAN-2024.pdf |
|--------|----------------------|---------------------|--------------|
| PyMuPDF | 47 txns, valid=True | 14 txns, valid=True | 15 txns, valid=True |
| pdfplumber | 47 txns, valid=True | 14 txns, valid=True | 15 txns, valid=True |

## [1.0.0] - 2024-12-28

### Added

- Initial project structure for Indonesian Bank Statement PDF Parser
- Core parser module with shared utilities (`pdfparser/`)
- PDF text extraction using PyMuPDF library
- Metadata extraction with regex patterns:
  - Account No pattern: `Account\s+No[:\s]+([^\n]+)`
  - Business Unit pattern: `Business\s+Unit[:\s]+([^\n]+)`
  - Product Name pattern: `Product\s+Name[:\s]+([^\n]+)`
  - Statement Date pattern: `Statement\s+Date[:\s]+([^\n]+)`
- Transaction extraction with inline row parsing:
  - Transaction date pattern: `^\d{2}/\d{2}/\d{2}`
  - Full transaction line pattern for parsing inline rows
- CSV export functions for metadata and transactions
- Validation function to check parsing quality
- Output directory management function
- Project configuration with `requirements.txt`
- Python 3.9 compatibility (PyMuPDF pinned to 1.26.5)
- Development documentation with `README.md`
- Code quality tools configuration (ruff, pyrefly)

### Created Directories

- `pdfparser/` - Main parser module
- `output/metadata/` - Metadata CSV outputs
- `output/transactions/` - Transaction CSV outputs
- `test-pdfs/` - Test dataset directory
- `venv/` - Virtual environment

### Features

- Support for multiple PDF parsing libraries (PyMuPDF, pdfplumber, pypdf - all implemented)
- Multiprocessing support for batch processing 1000+ files
- Performance benchmarking capabilities
- English documentation throughout codebase
- UTF-8 encoding support for Indonesian text

### Known Limitations

- Batch processing module (batch.py) not yet implemented
- Benchmark script (benchmark.py) not yet implemented
- Test data generator (generate_test_pdfs.py) not yet implemented

## [0.0.0] - 2024-12-28

### Added

- Initial project setup
- Sample Indonesian bank statement PDFs in `source-pdf/`
- Project plan document in `plan/1.0-v1.md`

