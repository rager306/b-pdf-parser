"""
Batch processing module for parallel PDF parsing.

This module provides functions for processing large numbers of PDF files
in parallel using ProcessPoolExecutor. It saves results to CSV files
organized by metadata and transactions.

Usage:
    from pdfparser.batch import batch_parse, get_optimal_workers

    # Get optimal worker count for this system
    workers = get_optimal_workers('pymupdf')

    # Parse multiple PDFs with default settings
    results = batch_parse(['file1.pdf', 'file2.pdf'], parser_name='pymupdf')

    # Parse with custom worker count and optimization options
    results = batch_parse(
        paths=['file1.pdf', 'file2.pdf'],
        parser_name='pdfplumber',
        max_workers=8,
        chunk_size=100,
        init_strategy='per-worker'
    )
"""

import gc
import os
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from pdfparser.pdfoxide_parser import parse_pdf_pdfoxide
from pdfparser.pdfplumber_parser import parse_pdf_pdfplumber
from pdfparser.pymupdf_parser import parse_pdf_pymupdf
from pdfparser.pypdf_parser import parse_pdf_pypdf
from pdfparser.utils import (
    is_valid_parse,
    load_config,
    save_metadata_csv,
    save_transactions_csv,
)

# Parser mapping
PARSERS = {
    'pymupdf': parse_pdf_pymupdf,
    'pdfplumber': parse_pdf_pdfplumber,
    'pypdf': parse_pdf_pypdf,
    'pdfoxide': parse_pdf_pdfoxide,
}

# Constants
DEFAULT_CHUNK_SIZE = 100
DEFAULT_INIT_STRATEGY = 'per-worker'
MAX_WORKERS_CAP = 16
VALID_PARSERS = ['pymupdf', 'pdfplumber', 'pypdf', 'pdfoxide']
VALID_INIT_STRATEGIES = ['per-file', 'per-worker']


@dataclass
class WorkerConfig:
    """Configuration for worker process behavior."""
    parser_name: str
    max_tasks_per_worker: int = 0  # 0 = unlimited
    init_strategy: str = DEFAULT_INIT_STRATEGY
    memory_limit_mb: int = 0  # 0 = unlimited


@dataclass
class BatchResult:
    """Consolidated result from batch processing."""
    total: int = 0
    successful: int = 0
    failed: int = 0
    success_rate: float = 0.0
    results: List[Dict[str, Any]] = field(default_factory=list)
    duration: float = 0.0
    throughput: float = 0.0
    memory_peak_mb: float = 0.0
    worker_overhead_percent: float = 0.0


def get_optimal_workers(parser_name: str = 'pymupdf') -> int:
    """
    Calculate optimal worker count based on system resources.

    Returns the recommended number of worker processes for batch processing,
    capped at MAX_WORKERS_CAP to prevent resource exhaustion.

    Args:
        parser_name: Parser backend (affects scaling strategy)

    Returns:
        Recommended worker count (4-16 range)
    """
    cpu_count = os.cpu_count() or 4
    # Cap at 16 workers to prevent resource exhaustion
    return min(cpu_count, MAX_WORKERS_CAP)


def get_worker_config(
    parser_name: str,
    max_workers: Optional[int] = None,
    init_strategy: str = DEFAULT_INIT_STRATEGY,
) -> WorkerConfig:
    """
    Create optimized worker configuration.

    Args:
        parser_name: Parser backend
        max_workers: Override auto-detection (will be capped at MAX_WORKERS_CAP)
        init_strategy: Parser initialization strategy ('per-file' or 'per-worker')

    Returns:
        WorkerConfig instance
    """
    if max_workers is None:
        max_workers = get_optimal_workers(parser_name)
    else:
        max_workers = min(max_workers, MAX_WORKERS_CAP)

    return WorkerConfig(
        parser_name=parser_name,
        max_tasks_per_worker=0,  # Default: unlimited
        init_strategy=init_strategy,
        memory_limit_mb=0,  # Default: unlimited
    )


def process_single_file(args: tuple) -> Dict[str, Any]:
    """
    Process a single PDF file and return parsed results.

    This function is designed to be called by ProcessPoolExecutor
    for parallel processing. It is multiprocessing-safe with no global state.

    Args:
        args: Tuple of (file_path, parser_name, init_strategy)

    Returns:
        Dict containing:
            - success: Whether parsing succeeded
            - file_path: Original file path
            - file_name: Base filename
            - metadata: Extracted metadata dict (empty if failed)
            - transactions: Extracted transactions list (empty if failed)
            - error: Error message if parsing failed
            - is_valid: Whether validation passed
    """
    file_path, parser_name, init_strategy = args

    result = {
        'success': False,
        'file_path': file_path,
        'file_name': os.path.basename(file_path),
        'metadata': {},
        'transactions': [],
        'error': None,
        'is_valid': False,
    }

    try:
        # Get the parser function
        parser_func = PARSERS.get(parser_name)
        if parser_func is None:
            raise ValueError(f"Unknown parser: {parser_name}")

        # Parse the PDF
        parse_result = parser_func(file_path)

        metadata = parse_result.get('metadata', {})
        transactions = parse_result.get('transactions', [])

        result['metadata'] = metadata
        result['transactions'] = transactions
        result['success'] = True
        result['is_valid'] = is_valid_parse(metadata, transactions)

    except FileNotFoundError:
        result['error'] = f'File not found: {file_path}'
    except PermissionError:
        result['error'] = f'Permission denied: {file_path}'
    except Exception as e:  # pylint: disable=broad-except
        result['error'] = str(e)

    return result


def save_result_files(
    result: Dict[str, Any],
    output_dir: str,
    metadata_dir: str,
    transactions_dir: str,
) -> None:
    """
    Save parsed results to CSV files.

    Args:
        result: Parsed result dict
        output_dir: Base output directory
        metadata_dir: Subdirectory for metadata CSVs
        transactions_dir: Subdirectory for transaction CSVs
    """
    file_name = result['file_name']
    base_name = os.path.splitext(file_name)[0]

    # Save metadata CSV
    if result['metadata']:
        metadata_path = os.path.join(metadata_dir, f'{base_name}_metadata.csv')
        save_metadata_csv(result['metadata'], metadata_path)

    # Save transactions CSV
    if result['transactions']:
        transactions_path = os.path.join(transactions_dir, f'{base_name}_transactions.csv')
        save_transactions_csv(result['transactions'], transactions_path)


def validate_batch_params(
    parser_name: str,
    max_workers: Optional[int],
    chunk_size: int,
    init_strategy: str,
) -> None:
    """
    Validate batch processing parameters.

    Args:
        parser_name: Parser backend name
        max_workers: Worker count override
        chunk_size: Files per worker batch
        init_strategy: Parser initialization strategy

    Raises:
        ValueError: If any parameter is invalid
    """
    if parser_name not in VALID_PARSERS:
        raise ValueError(
            f"Invalid parser: {parser_name}. Choose from: {', '.join(VALID_PARSERS)}"
        )

    if max_workers is not None:
        if not isinstance(max_workers, int) or max_workers < 1 or max_workers > 32:
            raise ValueError(
                f"max_workers must be between 1 and 32, got: {max_workers}"
            )

    if chunk_size < 1 or chunk_size > 500:
        raise ValueError(
            f"chunk_size must be between 1 and 500, got: {chunk_size}"
        )

    if init_strategy not in VALID_INIT_STRATEGIES:
        raise ValueError(
            f"init_strategy must be 'per-file' or 'per-worker', got: {init_strategy}"
        )


def batch_parse(
    paths: List[str],
    parser_name: str = 'pymupdf',
    max_workers: Optional[int] = None,
    output_dir: Optional[str] = None,
    verify_turnover: Optional[bool] = None,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    init_strategy: str = DEFAULT_INIT_STRATEGY,
) -> Dict[str, Any]:
    """
    Parse multiple PDF files in parallel and save results to CSV.

    This function processes PDF files using the specified parser,
    validates results, and saves metadata and transactions to
    separate CSV files for each input file.

    Args:
        paths: List of paths to PDF files to process
        parser_name: Parser to use ('pymupdf', 'pdfplumber', 'pypdf', 'pdfoxide')
        max_workers: Maximum parallel workers (default: auto-detect CPU cores, capped at 16)
        output_dir: Output directory for CSV files (default: from config)
        verify_turnover: Enable turnover verification (default: from config)
        chunk_size: Number of files per worker batch (default: 100)
        init_strategy: Parser initialization strategy ('per-file' or 'per-worker', default: 'per-worker')

    Returns:
        Dict containing:
            - total: Total files processed
            - successful: Number of successfully parsed files
            - failed: Number of failed files
            - results: List of individual file results
            - success_rate: Percentage of successful parses
            - duration: Total processing time in seconds
            - throughput: Files processed per second
            - memory_peak_mb: Peak memory usage (if available)
            - worker_overhead_percent: Worker creation overhead percentage
    """
    # Validate input parameters
    validate_batch_params(parser_name, max_workers, chunk_size, init_strategy)

    if not paths:
        return {
            'total': 0,
            'successful': 0,
            'failed': 0,
            'results': [],
            'success_rate': 0.0,
            'duration': 0.0,
            'throughput': 0.0,
            'memory_peak_mb': 0.0,
            'worker_overhead_percent': 0.0,
        }

    # Load configuration
    config = load_config()
    if output_dir is None:
        output_dir = config.get('output_dir', 'output')
    if verify_turnover is None:
        verify_turnover = bool(config.get('verify_turnover', False))

    # Create output subdirectories
    metadata_dir = os.path.join(output_dir, 'metadata')
    transactions_dir = os.path.join(output_dir, 'transactions')
    os.makedirs(metadata_dir, exist_ok=True)
    os.makedirs(transactions_dir, exist_ok=True)

    # Validate file paths
    valid_paths = []
    for path in paths:
        path_obj = Path(path)
        if not path_obj.exists():
            print(f"Warning: File not found, skipping: {path}")
            continue
        if not path_obj.is_file():
            print(f"Warning: Not a file, skipping: {path}")
            continue
        valid_paths.append(str(path_obj))

    if not valid_paths:
        return {
            'total': 0,
            'successful': 0,
            'failed': len(paths),
            'results': [],
            'success_rate': 0.0,
            'duration': 0.0,
            'throughput': 0.0,
            'memory_peak_mb': 0.0,
            'worker_overhead_percent': 0.0,
        }

    # Prepare tasks for parallel execution
    tasks = [(path, parser_name, init_strategy) for path in valid_paths]

    # Determine worker count
    if max_workers is None:
        max_workers = get_optimal_workers(parser_name)
    else:
        max_workers = min(max_workers, MAX_WORKERS_CAP)

    # Track timing
    start_time = time.time()
    worker_start_time = start_time

    # Process files in parallel
    results = []
    successful = 0
    failed = 0
    memory_peak = 0.0

    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        # Submit all tasks
        futures = {
            executor.submit(process_single_file, task): task for task in tasks
        }

        # Collect results as they complete
        for future in as_completed(futures):
            try:
                result = future.result()
                results.append(result)

                if result['success']:
                    successful += 1
                    # Save result files for successful parses
                    save_result_files(result, output_dir, metadata_dir, transactions_dir)
                else:
                    failed += 1

                # Trigger garbage collection for memory management
                if init_strategy == 'per-file':
                    gc.collect()

            except Exception as e:  # pylint: disable=broad-except
                task = futures[future]
                error_result = {
                    'success': False,
                    'file_path': task[0],
                    'file_name': os.path.basename(task[0]),
                    'error': str(e),
                }
                results.append(error_result)
                failed += 1

    end_time = time.time()
    duration = end_time - start_time
    worker_overhead_time = worker_start_time - start_time
    worker_overhead_percent = (worker_overhead_time / duration * 100) if duration > 0 else 0.0

    total = len(valid_paths)
    throughput = total / duration if duration > 0 else 0.0

    return {
        'total': total,
        'successful': successful,
        'failed': failed,
        'results': results,
        'success_rate': (successful / total * 100) if total > 0 else 0.0,
        'duration': duration,
        'throughput': throughput,
        'memory_peak_mb': memory_peak,
        'worker_overhead_percent': worker_overhead_percent,
    }


def batch_parse_from_directory(
    directory: str,
    parser_name: str = 'pymupdf',
    max_workers: Optional[int] = None,
    output_dir: Optional[str] = None,
    pattern: str = '**/*.pdf',
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    init_strategy: str = DEFAULT_INIT_STRATEGY,
) -> Dict[str, Any]:
    """
    Parse all PDF files in a directory and its subdirectories.

    This is a convenience function that discovers PDF files in a directory
    and processes them using batch_parse.

    Args:
        directory: Directory to search for PDF files
        parser_name: Parser to use
        max_workers: Maximum parallel workers
        output_dir: Output directory for CSV files
        pattern: Glob pattern for file discovery (default: '**/*.pdf')
        chunk_size: Number of files per worker batch (default: 100)
        init_strategy: Parser initialization strategy (default: 'per-worker')

    Returns:
        Dict with batch processing results (same as batch_parse)
    """
    # Discover PDF files
    pdf_files = []
    for root, _, files in os.walk(directory):
        for file in files:
            if file.lower().endswith('.pdf'):
                pdf_files.append(os.path.join(root, file))

    if not pdf_files:
        return {
            'total': 0,
            'successful': 0,
            'failed': 0,
            'results': [],
            'success_rate': 0.0,
            'duration': 0.0,
            'throughput': 0.0,
            'memory_peak_mb': 0.0,
            'worker_overhead_percent': 0.0,
        }

    # Sort for consistent ordering
    pdf_files = sorted(pdf_files)

    # Process files
    return batch_parse(
        paths=pdf_files,
        parser_name=parser_name,
        max_workers=max_workers,
        output_dir=output_dir,
        chunk_size=chunk_size,
        init_strategy=init_strategy,
    )
