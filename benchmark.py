#!/usr/bin/env python3
"""
Benchmark tool for comparing PDF parser performance.

This script benchmarks all available PDF parsers against a directory of test PDFs,
measuring parsing time, throughput, and success rates. Results are saved to CSV
and displayed in a formatted table.

Quick Start:
    # Benchmark all parsers with 100 PDFs
    python benchmark.py --test-dir source-pdf

    # Benchmark only PyMuPDF with 1000 PDFs
    python benchmark.py --test-dir source-pdf --parsers=pymupdf --max-files 1000

    # Compare parsers with 500 PDFs using 8 workers
    python benchmark.py --test-dir source-pdf --max-files 500 --max-workers 8

Arguments:
    --parsers: Comma-separated list of parsers to benchmark (default: all)
               Options: pymupdf, pdfplumber, pypdf, pdfoxide, all
    --test-dir: Directory containing PDF files to parse (required)
    --max-files: Maximum number of PDFs to process (default: all)
    --max-workers: Maximum parallel workers (default: 4)

Output:
    Results are saved to output/benchmark_results.csv
"""

import argparse
import csv
import glob
import os
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from typing import Any, Dict, List, Optional

from tabulate import tabulate

from pdfparser import is_valid_parse, load_config, parse_pdf

# Available parser names
PARSER_CHOICES = ['pymupdf', 'pdfplumber', 'pypdf', 'pdfoxide', 'all']


def parse_single_pdf(args: tuple) -> Dict[str, Any]:
    """
    Parse a single PDF file and return timing metrics.

    This function is designed to be called by ProcessPoolExecutor
    for parallel processing. It is multiprocessing-safe with no global state.

    Args:
        args: Tuple of (file_path, parser_name)

    Returns:
        Dict containing:
            - file_path: Path to the PDF file
            - parser: Parser name used
            - success: Whether parsing succeeded
            - transaction_count: Number of transactions extracted
            - parse_time_seconds: Time taken to parse
            - page_count: Number of pages in PDF (if available)
            - error: Error message if parsing failed
    """
    file_path, parser_name = args

    result = {
        'file_path': file_path,
        'parser': parser_name,
        'success': False,
        'transaction_count': 0,
        'parse_time_seconds': 0.0,
        'page_count': 0,
        'error': None,
    }

    try:
        start_time = time.perf_counter()

        # Parse the PDF
        parse_result = parse_pdf(file_path, parser=parser_name)

        parse_time = time.perf_counter() - start_time
        result['parse_time_seconds'] = parse_time

        # Check if parse was valid
        metadata = parse_result.get('metadata', {})
        transactions = parse_result.get('transactions', [])

        result['success'] = is_valid_parse(metadata, transactions)
        result['transaction_count'] = len(transactions)

    except FileNotFoundError:
        result['error'] = 'File not found'
    except Exception as e:  # pylint: disable=broad-except
        result['error'] = str(e)

    return result


def discover_pdfs(test_dir: str, max_files: Optional[int] = None) -> List[str]:
    """
    Discover PDF files in the specified directory.

    Args:
        test_dir: Directory path to search for PDFs
        max_files: Maximum number of files to return (None for all)

    Returns:
        List of paths to discovered PDF files
    """
    pdf_pattern = os.path.join(test_dir, '**', '*.pdf')
    pdf_files = glob.glob(pdf_pattern, recursive=True)

    # Sort for consistent ordering
    pdf_files = sorted(pdf_files)

    if max_files is not None and max_files > 0:
        pdf_files = pdf_files[:max_files]

    return pdf_files


def calculate_metrics(results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Calculate aggregate metrics from benchmark results.

    Args:
        results: List of individual parse results

    Returns:
        Dict containing aggregate metrics:
            - total_files: Number of files processed
            - successful: Number of successful parses
            - failed: Number of failed parses
            - success_rate: Percentage of successful parses
            - total_time_seconds: Sum of all parse times
            - avg_time_per_file: Average time per file
            - avg_time_per_page: Average time per page (if page count available)
            - total_transactions: Sum of all transactions extracted
            - avg_transactions_per_file: Average transactions per file
    """
    total_files = len(results)
    successful = sum(1 for r in results if r['success'])
    failed = total_files - successful

    total_time = sum(r['parse_time_seconds'] for r in results)
    total_transactions = sum(r['transaction_count'] for r in results)

    metrics = {
        'total_files': total_files,
        'successful': successful,
        'failed': failed,
        'success_rate': (successful / total_files * 100) if total_files > 0 else 0.0,
        'total_time_seconds': total_time,
        'avg_time_per_file': total_time / total_files if total_files > 0 else 0.0,
        'avg_time_per_page': 0.0,
        'total_transactions': total_transactions,
        'avg_transactions_per_file': total_transactions / total_files if total_files > 0 else 0.0,
    }

    # Calculate time per page if page counts are available
    pages_with_count = [r for r in results if r.get('page_count', 0) > 0]
    if pages_with_count:
        total_pages = sum(r.get('page_count', 0) for r in results)
        metrics['avg_time_per_page'] = total_time / total_pages if total_pages > 0 else 0.0

    return metrics


def run_benchmark(
    parsers: List[str],
    test_dir: str,
    max_files: Optional[int] = None,
    max_workers: int = 4,
) -> List[Dict[str, Any]]:
    """
    Run the benchmark across specified parsers and PDF files.

    Args:
        parsers: List of parser names to benchmark
        test_dir: Directory containing PDF files
        max_files: Maximum number of PDFs to process
        max_workers: Maximum parallel workers

    Returns:
        List of all benchmark results
    """
    # Discover PDF files
    pdf_files = discover_pdfs(test_dir, max_files)

    if not pdf_files:
        print(f"No PDF files found in {test_dir}")
        return []

    print(f"Found {len(pdf_files)} PDF files to benchmark")
    print(f"Running with {max_workers} parallel workers")

    # Prepare all (file, parser) combinations
    tasks = [(pdf, parser) for pdf in pdf_files for parser in parsers]

    all_results = []

    # Run with ProcessPoolExecutor for parallel processing
    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        # Submit all tasks
        futures = {executor.submit(parse_single_pdf, task): task for task in tasks}

        # Collect results as they complete
        for future in as_completed(futures):
            try:
                result = future.result()
                all_results.append(result)
            except Exception as e:
                task = futures[future]
                all_results.append({
                    'file_path': task[0],
                    'parser': task[1],
                    'success': False,
                    'error': str(e),
                })

    return all_results


def aggregate_by_parser(results: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    """
    Aggregate benchmark results by parser.

    Args:
        results: List of all benchmark results

    Returns:
        Dict mapping parser name to its aggregate metrics
    """
    by_parser: Dict[str, List[Dict[str, Any]]] = {}

    for result in results:
        parser = result['parser']
        if parser not in by_parser:
            by_parser[parser] = []
        by_parser[parser].append(result)

    aggregated = {}
    for parser, parser_results in by_parser.items():
        metrics = calculate_metrics(parser_results)
        metrics['parser'] = parser
        aggregated[parser] = metrics

    return aggregated


def save_results_csv(
    results: List[Dict[str, Any]],
    output_path: str,
    config: Dict[str, Any],
) -> None:
    """
    Save benchmark results to CSV file.

    Args:
        results: List of benchmark results
        output_path: Path for output CSV file
        config: Project configuration
    """
    output_dir = config.get('output_dir', 'output')

    # Ensure output directory exists
    os.makedirs(output_dir, exist_ok=True)

    full_path = os.path.join(output_dir, output_path)

    fieldnames = [
        'file_path',
        'parser',
        'success',
        'transaction_count',
        'parse_time_seconds',
        'page_count',
        'error',
    ]

    with open(full_path, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(results)

    print(f"Results saved to {full_path}")


def print_summary_table(aggregated: Dict[str, Dict[str, Any]]) -> None:
    """
    Print benchmark summary table using tabulate.

    Args:
        aggregated: Dict mapping parser name to aggregate metrics
    """
    table_data = []

    for parser, metrics in sorted(aggregated.items()):
        row = [
            parser,
            metrics['total_files'],
            metrics['successful'],
            metrics['failed'],
            f"{metrics['success_rate']:.1f}%",
            f"{metrics['avg_time_per_file']:.4f}s",
            f"{metrics['avg_transactions_per_file']:.1f}",
        ]
        table_data.append(row)

    headers = [
        'Parser',
        'Files',
        'Success',
        'Failed',
        'Success Rate',
        'Avg Time/File',
        'Avg Txns/File',
    ]

    print("\n" + tabulate(table_data, headers=headers, tablefmt='grid'))


def main() -> None:
    """Main entry point for benchmark tool."""
    parser = argparse.ArgumentParser(
        description='Benchmark PDF parser performance',
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        '--parsers',
        type=str,
        default='all',
        help='Comma-separated list of parsers (default: all)',
    )

    parser.add_argument(
        '--test-dir',
        type=str,
        required=True,
        help='Directory containing PDF files to benchmark',
    )

    parser.add_argument(
        '--max-files',
        type=int,
        default=None,
        help='Maximum number of PDFs to process (default: all)',
    )

    parser.add_argument(
        '--max-workers',
        type=int,
        default=4,
        help='Maximum parallel workers (default: 4)',
    )

    args = parser.parse_args()

    # Parse parser list
    if args.parsers.lower() == 'all':
        parsers = PARSER_CHOICES[:-1]  # Exclude 'all'
    else:
        parsers = [p.strip().lower() for p in args.parsers.split(',')]
        # Validate parser names
        valid_parsers = PARSER_CHOICES[:-1]
        for p in parsers:
            if p not in valid_parsers:
                parser.error(f"Invalid parser: {p}. Choose from: {', '.join(valid_parsers)}")

    # Load project configuration
    config = load_config()

    # Run benchmark
    print("Starting benchmark...")
    start_time = time.perf_counter()

    results = run_benchmark(
        parsers=parsers,
        test_dir=args.test_dir,
        max_files=args.max_files,
        max_workers=args.max_workers,
    )

    total_time = time.perf_counter() - start_time

    if not results:
        print("No results to display")
        return

    # Aggregate and display results
    aggregated = aggregate_by_parser(results)

    print_summary_table(aggregated)

    # Save detailed results to CSV
    save_results_csv(results, 'benchmark_results.csv', config)

    # Print overall summary
    print(f"\nBenchmark completed in {total_time:.2f} seconds")

    # Per-parser summary
    print("\nPer-parser Performance Summary:")
    for parser, metrics in sorted(aggregated.items()):
        print(f"  {parser}: {metrics['avg_time_per_file']:.4f}s/file, "
              f"{metrics['success_rate']:.1f}% success rate")


if __name__ == '__main__':
    main()
