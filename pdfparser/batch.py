"""
Batch processing module for parallel PDF parsing.

This module provides functions for processing large numbers of PDF files
in parallel using ProcessPoolExecutor. It saves results to CSV files
organized by metadata and transactions.

Usage:
    from pdfparser.batch import batch_parse

    # Parse multiple PDFs with default settings
    results = batch_parse(['file1.pdf', 'file2.pdf'], parser_name='pymupdf')

    # Parse with custom worker count
    results = batch_parse(
        paths=['file1.pdf', 'file2.pdf'],
        parser_name='pdfplumber',
        max_workers=8
    )
"""

import os
from concurrent.futures import ProcessPoolExecutor, as_completed
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


def process_single_file(args: tuple) -> Dict[str, Any]:
    """
    Process a single PDF file and return parsed results.

    This function is designed to be called by ProcessPoolExecutor
    for parallel processing. It is multiprocessing-safe with no global state.

    Args:
        args: Tuple of (file_path, parser_name)

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
    file_path, parser_name = args

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


def batch_parse(
    paths: List[str],
    parser_name: str = 'pymupdf',
    max_workers: Optional[int] = None,
    output_dir: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Parse multiple PDF files in parallel and save results to CSV.

    This function processes PDF files using the specified parser,
    validates results, and saves metadata and transactions to
    separate CSV files for each input file.

    Args:
        paths: List of paths to PDF files to process
        parser_name: Parser to use ('pymupdf', 'pdfplumber', 'pypdf', 'pdfoxide')
        max_workers: Maximum parallel workers (default: CPU count)
        output_dir: Output directory for CSV files (default: from config)

    Returns:
        Dict containing:
            - total: Total files processed
            - successful: Number of successfully parsed files
            - failed: Number of failed files
            - results: List of individual file results
            - success_rate: Percentage of successful parses
    """
    # Validate input
    if not paths:
        return {
            'total': 0,
            'successful': 0,
            'failed': 0,
            'results': [],
            'success_rate': 0.0,
        }

    valid_parsers = ['pymupdf', 'pdfplumber', 'pypdf', 'pdfoxide']
    if parser_name not in valid_parsers:
        raise ValueError(
            f"Invalid parser: {parser_name}. Choose from: {', '.join(valid_parsers)}"
        )

    # Load configuration
    config = load_config()
    if output_dir is None:
        output_dir = config.get('output_dir', 'output')

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
        }

    # Prepare tasks for parallel execution
    tasks = [(path, parser_name) for path in valid_paths]

    # Determine worker count
    if max_workers is None:
        import multiprocessing
        max_workers = multiprocessing.cpu_count()

    # Process files in parallel
    results = []
    successful = 0
    failed = 0

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

    total = len(valid_paths)

    return {
        'total': total,
        'successful': successful,
        'failed': failed,
        'results': results,
        'success_rate': (successful / total * 100) if total > 0 else 0.0,
    }


def batch_parse_from_directory(
    directory: str,
    parser_name: str = 'pymupdf',
    max_workers: Optional[int] = None,
    output_dir: Optional[str] = None,
    pattern: str = '**/*.pdf',
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
        }

    # Sort for consistent ordering
    pdf_files = sorted(pdf_files)

    # Process files
    return batch_parse(
        paths=pdf_files,
        parser_name=parser_name,
        max_workers=max_workers,
        output_dir=output_dir,
    )
