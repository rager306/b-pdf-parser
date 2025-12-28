#!/usr/bin/env python3
"""
Test data generator for synthetic PDF bank statements.

This script generates realistic-looking Indonesian bank statement PDFs
using the reportlab library. It is useful for testing the PDF parser
with known input data.

Usage:
    python generate_test_pdfs.py --num=100
    python generate_test_pdfs.py --num=50 --output-dir test-pdfs

Arguments:
    --num: Number of PDFs to generate (default: 100)
    --output-dir: Output directory for generated PDFs (default: test-pdfs)
    --min-pages: Minimum pages per PDF (default: 1)
    --max-pages: Maximum pages per PDF (default: 10)
    --min-transactions: Minimum transactions per page (default: 100)
    --max-transactions: Maximum transactions per page (default: 500)
"""

import argparse
import os
import random
import string
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List

from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

# Random data for realistic PDF generation
FIRST_NAMES = [
    'Ahmad', 'Budi', 'Citra', 'Dewi', 'Eka', 'Farhan', 'Gita', 'Hendra',
    'Indah', 'Joko', 'Kiki', 'Lina', 'Mira', 'Nanda', 'Olivia', 'Putu',
    'Rina', 'Sari', 'Tomi', 'Utari', 'Vina', 'Wira', 'Yudi', 'Zahra',
]

LAST_NAMES = [
    'Susanto', 'Wijaya', 'Pratama', 'Santoso', 'Kurniawan', 'Kusuma',
    'Nugroho', 'Setyawati', 'Mahendra', 'Darmawan', 'Putri', 'Sari',
    'Hartono', 'Lestari', 'Wibowo', 'Raharjo', 'Firmawati', 'Prasetyo',
]

COMPANY_NAMES = [
    'PT Maju Bersama', 'CV Teknik Solusi', 'PT Global Digital',
    'PT Indo Niaga', 'CV Kreatif Media', 'PT Agung Elektrik',
    'PT Bina Sejahtera', 'CV Jaya Abadi', 'PT Mitra Teknologi',
    'PT Cemerlang Inti', 'PT Bangun Persada', 'CV Anugerah',
]

PRODUCT_NAMES = [
    'Rekening Koran Bisnis', 'Rekening Giro Perusahaan',
    'Rekening Tabungan Employee', 'Rekening Premium Pribadi',
    'Rekening Korporasi', 'Rekening Valas',
]

BUSINESS_UNITS = [
    'Jakarta Pusat', 'Jakarta Selatan', 'Jakarta Barat', 'Jakarta Timur',
    'Surabaya', 'Bandung', 'Medan', 'Makassar',
    'Denpasar', 'Yogyakarta', 'Semarang', 'Palembang',
]


def random_account_number() -> str:
    """Generate a realistic account number."""
    return ''.join(random.choices(string.digits, k=13))


def random_phone_number() -> str:
    """Generate a realistic phone number."""
    return "+62" + "".join(random.choices(string.digits, k=9))


def random_address() -> str:
    """Generate a random address."""
    street_num = random.randint(1, 200)
    street_names = ['Jalan Sudirman', 'Jalan Thamrin', 'Jalan Gatot Subroto',
                    'Jalan Asia Afrika', 'Jalan Veteran', 'Jalan Merdeka']
    return f"{street_num} {random.choice(street_names)}, Jakarta Pusat"


def random_transaction_description() -> str:
    """Generate a random transaction description."""
    descriptions = [
        'Transfer Masuk', 'Transfer Keluar', 'Pembayaran Listrik',
        'Pembayaran Air', 'Pembayaran Telepon', 'Pembayaran Internet',
        'Setoran Tunai', 'Penarikan Tunai', 'Pembayaran Kartu Kredit',
        'Pembayaran Asuransi', 'Investasi Reksa Dana', 'Pembelian Emas',
        'Top Up E-Wallet', 'Pembayaran Toko Online', 'Biaya Admin',
        'Bunga Tabungan', 'Denda Keterlambatan', 'Pembayaran Cicilan',
    ]
    return random.choice(descriptions)


def generate_random_transactions(
    start_date: datetime,
    num_transactions: int,
) -> List[Dict[str, str]]:
    """
    Generate random transaction data.

    Args:
        start_date: Starting date for transactions
        num_transactions: Number of transactions to generate

    Returns:
        List of transaction dicts
    """
    transactions = []
    current_date = start_date

    for _ in range(num_transactions):
        # Randomly decide transaction type
        is_credit = random.random() > 0.4  # 60% credit, 40% debit

        # Generate random amounts
        amount = random.randint(10000, 5000000)
        balance = random.randint(1000000, 100000000)

        # Transaction date (within last 30 days from start)
        days_offset = random.randint(0, 30)
        current_date = start_date + timedelta(days=days_offset)

        # Generate user name
        first_name = random.choice(FIRST_NAMES)
        last_name = random.choice(LAST_NAMES)
        user_name = f"{first_name} {last_name}"

        txn = {
            'date': current_date.strftime('%d/%m/%y %H:%M:%S'),
            'description': random_transaction_description(),
            'user': user_name,
            'debit': f"{amount:,.2f}" if not is_credit else '',
            'credit': f"{amount:,.2f}" if is_credit else '',
            'balance': f"{balance:,.2f}",
        }
        transactions.append(txn)

    # Sort by date
    transactions.sort(key=lambda x: x['date'])

    return transactions


def generate_metadata() -> Dict[str, str]:
    """
    Generate random metadata for a bank statement.

    Returns:
        Dict with account_no, business_unit, product_name, statement_date
    """
    today = datetime.now()
    statement_date = today.strftime('%d/%m/%Y')

    return {
        'account_no': random_account_number(),
        'business_unit': random.choice(BUSINESS_UNITS),
        'product_name': random.choice(PRODUCT_NAMES),
        'statement_date': statement_date,
    }


def create_pdf_content(
    metadata: Dict[str, str],
    transactions: List[Dict[str, str]],
) -> str:
    """
    Create the text content for a bank statement PDF.

    Args:
        metadata: Bank statement metadata
        transactions: List of transactions

    Returns:
        Formatted text content
    """
    lines = []

    # Header
    lines.append("INDONESIAN BANK")
    lines.append("=" * 60)
    lines.append("")
    lines.append(f"Account No      : {metadata['account_no']}")
    lines.append(f"Business Unit   : {metadata['business_unit']}")
    lines.append(f"Product Name    : {metadata['product_name']}")
    lines.append(f"Statement Date  : {metadata['statement_date']}")
    lines.append("=" * 60)
    lines.append("")
    lines.append("TRANSACTION HISTORY")
    lines.append("-" * 60)
    lines.append("")
    lines.append("Date                    Description                    User                   Debit           Credit          Balance")
    lines.append("-" * 60)

    # Transactions
    for txn in transactions:
        lines.append(
            f"{txn['date']:<22} "
            f"{txn['description']:<28} "
            f"{txn['user']:<22} "
            f"{txn['debit']:<14} "
            f"{txn['credit']:<14} "
            f"{txn['balance']}"
        )

    lines.append("-" * 60)
    lines.append("END OF STATEMENT")

    return "\n".join(lines)


def generate_single_pdf(
    output_path: str,
    num_pages: int = 1,
    transactions_per_page: int = 100,
) -> Dict[str, Any]:
    """
    Generate a single test PDF bank statement.

    Args:
        output_path: Path where PDF will be saved
        num_pages: Number of pages in the PDF
        transactions_per_page: Transactions per page

    Returns:
        Dict with generation metadata
    """
    # Generate metadata
    metadata = generate_metadata()

    # Generate transactions (split across pages)
    total_transactions = num_pages * transactions_per_page
    start_date = datetime.now() - timedelta(days=30)
    all_transactions = generate_random_transactions(start_date, total_transactions)

    # Split transactions by page
    pages_transactions = [
        all_transactions[i * transactions_per_page:(i + 1) * transactions_per_page]
        for i in range(num_pages)
    ]

    # Create PDF document
    doc = SimpleDocTemplate(
        output_path,
        pagesize=letter,
        rightMargin=72,
        leftMargin=72,
        topMargin=72,
        bottomMargin=72,
    )

    # Build content for each page
    story = []

    for page_num, page_transactions in enumerate(pages_transactions):
        if page_num > 0:
            # Add page break
            story.append(Spacer(1, 0.5 * inch))

        # Create content for this page
        content = create_pdf_content(metadata, page_transactions)

        # Add to story as paragraphs (to handle long text)
        styles = getSampleStyleSheet()
        body_style = ParagraphStyle(
            'BodyText',
            parent=styles['Normal'],
            fontSize=8,
            leading=10,
        )

        for line in content.split('\n'):
            if line.strip():
                story.append(Paragraph(line, body_style))
            else:
                story.append(Spacer(1, 6))

    # Build PDF
    doc.build(story)

    return {
        'file_path': output_path,
        'metadata': metadata,
        'transaction_count': len(all_transactions),
        'page_count': num_pages,
    }


def generate_test_pdfs(
    num_pdfs: int = 100,
    output_dir: str = 'test-pdfs',
    min_pages: int = 1,
    max_pages: int = 10,
    min_transactions: int = 100,
    max_transactions: int = 500,
) -> List[Dict[str, Any]]:
    """
    Generate multiple test PDF bank statements.

    Args:
        num_pdfs: Number of PDFs to generate
        output_dir: Output directory for PDFs
        min_pages: Minimum pages per PDF
        max_pages: Maximum pages per PDF
        min_transactions: Minimum transactions per page
        max_transactions: Maximum transactions per page

    Returns:
        List of generation results for each PDF
    """
    # Create output directory
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    results = []

    print(f"Generating {num_pdfs} test PDFs in '{output_dir}'...")

    for i in range(num_pdfs):
        # Randomize page count and transactions
        num_pages = random.randint(min_pages, max_pages)
        transactions_per_page = random.randint(min_transactions, max_transactions)

        # Generate unique filename
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        file_name = f"test_statement_{i:04d}_{timestamp}.pdf"
        output_path = os.path.join(output_dir, file_name)

        # Generate PDF
        result = generate_single_pdf(
            output_path=output_path,
            num_pages=num_pages,
            transactions_per_page=transactions_per_page,
        )

        results.append(result)

        # Progress indicator
        if (i + 1) % 10 == 0 or i + 1 == num_pdfs:
            print(f"  Generated {i + 1}/{num_pdfs} PDFs...")

    print(f"Completed! Generated {num_pdfs} PDFs in '{output_dir}'")

    return results


def main() -> None:
    """Main entry point for test data generator."""
    parser = argparse.ArgumentParser(
        description='Generate synthetic PDF bank statements for testing',
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        '--num',
        type=int,
        default=100,
        help='Number of PDFs to generate (default: 100)',
    )

    parser.add_argument(
        '--output-dir',
        type=str,
        default='test-pdfs',
        help='Output directory for generated PDFs (default: test-pdfs)',
    )

    parser.add_argument(
        '--min-pages',
        type=int,
        default=1,
        help='Minimum pages per PDF (default: 1)',
    )

    parser.add_argument(
        '--max-pages',
        type=int,
        default=10,
        help='Maximum pages per PDF (default: 10)',
    )

    parser.add_argument(
        '--min-transactions',
        type=int,
        default=100,
        help='Minimum transactions per page (default: 100)',
    )

    parser.add_argument(
        '--max-transactions',
        type=int,
        default=500,
        help='Maximum transactions per page (default: 500)',
    )

    args = parser.parse_args()

    # Generate PDFs
    results = generate_test_pdfs(
        num_pdfs=args.num,
        output_dir=args.output_dir,
        min_pages=args.min_pages,
        max_pages=args.max_pages,
        min_transactions=args.min_transactions,
        max_transactions=args.max_transactions,
    )

    # Print summary
    total_transactions = sum(r['transaction_count'] for r in results)
    total_pages = sum(r['page_count'] for r in results)

    print("\nSummary:")
    print(f"  Total PDFs: {len(results)}")
    print(f"  Total Pages: {total_pages}")
    print(f"  Total Transactions: {total_transactions}")


if __name__ == '__main__':
    main()
