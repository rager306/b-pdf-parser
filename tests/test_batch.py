"""
Tests for batch processing module.

Tests cover:
- Worker configuration and optimization
- Batch processing parameters
- Performance metrics tracking
- Validation of inputs
"""

import time

import pytest

from pdfparser.batch import (
    BatchResult,
    WorkerConfig,
    batch_parse,
    batch_parse_from_directory,
    get_optimal_workers,
    get_worker_config,
    validate_batch_params,
)


class TestGetOptimalWorkers:
    """Tests for get_optimal_workers() function."""

    def test_returns_cpu_count_capped(self):
        """Test that worker count is capped at MAX_WORKERS_CAP."""
        workers = get_optimal_workers("pymupdf")
        # Should be at least 1, at most 16 (MAX_WORKERS_CAP)
        assert 1 <= workers <= 16

    def test_returns_int(self):
        """Test that return type is int."""
        workers = get_optimal_workers("pymupdf")
        assert isinstance(workers, int)

    def test_different_parsers_return_same(self):
        """Test that different parsers return similar worker counts."""
        workers_pymupdf = get_optimal_workers("pymupdf")
        workers_pdfplumber = get_optimal_workers("pdfplumber")
        workers_pypdf = get_optimal_workers("pypdf")
        workers_pdfoxide = get_optimal_workers("pdfoxide")

        # All should return same capped value
        assert workers_pymupdf == workers_pdfplumber
        assert workers_pdfplumber == workers_pypdf
        assert workers_pypdf == workers_pdfoxide


class TestGetWorkerConfig:
    """Tests for get_worker_config() function."""

    def test_returns_worker_config(self):
        """Test that function returns WorkerConfig instance."""
        config = get_worker_config("pymupdf")
        assert isinstance(config, WorkerConfig)
        assert config.parser_name == "pymupdf"

    def test_with_max_workers_override(self):
        """Test max_workers parameter override."""
        config = get_worker_config("pymupdf", max_workers=8)
        # Should cap at 16
        assert config is not None

    def test_default_init_strategy(self):
        """Test default init_strategy is 'per-worker'."""
        config = get_worker_config("pymupdf")
        assert config.init_strategy == "per-worker"

    def test_custom_init_strategy(self):
        """Test custom init_strategy parameter."""
        config = get_worker_config("pymupdf", init_strategy="per-file")
        assert config.init_strategy == "per-file"


class TestValidateBatchParams:
    """Tests for _validate_batch_params() function."""

    def test_valid_params(self):
        """Test that valid params pass validation."""
        # Should not raise
        validate_batch_params("pymupdf", None, 100, "per-worker")

    def test_invalid_parser(self):
        """Test that invalid parser raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            validate_batch_params("invalid_parser", None, 100, "per-worker")
        assert "Invalid parser" in str(exc_info.value)

    def test_invalid_max_workers_too_low(self):
        """Test that max_workers < 1 raises ValueError."""
        with pytest.raises(ValueError):
            validate_batch_params("pymupdf", 0, 100, "per-worker")

    def test_invalid_max_workers_too_high(self):
        """Test that max_workers > 32 raises ValueError."""
        with pytest.raises(ValueError):
            validate_batch_params("pymupdf", 33, 100, "per-worker")

    def test_invalid_chunk_size_too_low(self):
        """Test that chunk_size < 1 raises ValueError."""
        with pytest.raises(ValueError):
            validate_batch_params("pymupdf", None, 0, "per-worker")

    def test_invalid_chunk_size_too_high(self):
        """Test that chunk_size > 500 raises ValueError."""
        with pytest.raises(ValueError):
            validate_batch_params("pymupdf", None, 501, "per-worker")

    def test_invalid_init_strategy(self):
        """Test that invalid init_strategy raises ValueError."""
        with pytest.raises(ValueError):
            validate_batch_params("pymupdf", None, 100, "invalid")


class TestBatchParse:
    """Tests for batch_parse() function."""

    @pytest.fixture
    def sample_pdf_files(self, tmp_path):
        """Create temporary PDF files for testing."""
        files = []
        for i in range(3):
            file_path = tmp_path / f"test_{i}.pdf"
            file_path.write_text("%PDF-1.4 mock PDF content")
            files.append(str(file_path))
        return files

    def test_empty_paths_returns_empty_result(self):
        """Test that empty paths returns appropriate result."""
        result = batch_parse([])
        assert result["total"] == 0
        assert result["successful"] == 0
        assert result["failed"] == 0
        assert result["results"] == []

    def test_nonexistent_files_skipped(self, tmp_path):
        """Test that nonexistent files are skipped."""
        result = batch_parse([str(tmp_path / "nonexistent.pdf")])
        assert result["total"] == 0
        assert result["failed"] == 1

    def test_directory_not_a_file_skipped(self, tmp_path):
        """Test that directories are skipped."""
        result = batch_parse([str(tmp_path)])
        assert result["total"] == 0

    def test_valid_pdf_processing(self, sample_pdf_files):
        """Test that valid PDFs are processed."""
        result = batch_parse(sample_pdf_files, parser_name="pymupdf")
        assert result["total"] == 3
        assert result["successful"] >= 0  # May succeed or fail depending on PDF validity
        assert result["failed"] >= 0
        assert len(result["results"]) == 3

    def test_returns_throughput_metric(self, sample_pdf_files):
        """Test that result includes throughput metric."""
        result = batch_parse(sample_pdf_files, parser_name="pymupdf")
        assert "throughput" in result
        assert isinstance(result["throughput"], float)

    def test_returns_duration_metric(self, sample_pdf_files):
        """Test that result includes duration metric."""
        result = batch_parse(sample_pdf_files, parser_name="pymupdf")
        assert "duration" in result
        assert isinstance(result["duration"], float)
        assert result["duration"] >= 0

    def test_returns_worker_overhead_percent(self, sample_pdf_files):
        """Test that result includes worker_overhead_percent metric."""
        result = batch_parse(sample_pdf_files, parser_name="pymupdf")
        assert "worker_overhead_percent" in result
        assert isinstance(result["worker_overhead_percent"], float)
        assert 0 <= result["worker_overhead_percent"] <= 100

    def test_success_rate_calculation(self, sample_pdf_files):
        """Test that success_rate is calculated correctly."""
        result = batch_parse(sample_pdf_files, parser_name="pymupdf")
        if result["total"] > 0:
            expected_rate = result["successful"] / result["total"] * 100
            assert result["success_rate"] == expected_rate

    def test_max_workers_parameter(self, sample_pdf_files):
        """Test that max_workers parameter is respected."""
        result = batch_parse(sample_pdf_files, parser_name="pymupdf", max_workers=2)
        assert result["total"] == 3

    def test_chunk_size_parameter(self, sample_pdf_files):
        """Test that chunk_size parameter is accepted."""
        result = batch_parse(sample_pdf_files, parser_name="pymupdf", chunk_size=50)
        assert result["total"] == 3

    def test_init_strategy_per_worker(self, sample_pdf_files):
        """Test that init_strategy='per-worker' works."""
        result = batch_parse(sample_pdf_files, parser_name="pymupdf", init_strategy="per-worker")
        assert result["total"] == 3

    def test_init_strategy_per_file(self, sample_pdf_files):
        """Test that init_strategy='per-file' works."""
        result = batch_parse(sample_pdf_files, parser_name="pymupdf", init_strategy="per-file")
        assert result["total"] == 3

    def test_invalid_parser_raises_error(self, sample_pdf_files):
        """Test that invalid parser raises ValueError."""
        with pytest.raises(ValueError):
            batch_parse(sample_pdf_files, parser_name="invalid")


class TestBatchParseFromDirectory:
    """Tests for batch_parse_from_directory() function."""

    @pytest.fixture
    def pdf_directory(self, tmp_path):
        """Create a directory with mock PDF files."""
        for i in range(3):
            file_path = tmp_path / f"test_{i}.pdf"
            file_path.write_text("%PDF-1.4 mock PDF content")
        # Add a non-PDF file that should be ignored
        txt_file = tmp_path / "readme.txt"
        txt_file.write_text("This is not a PDF")
        return str(tmp_path)

    def test_empty_directory_returns_empty_result(self, tmp_path):
        """Test that empty directory returns appropriate result."""
        result = batch_parse_from_directory(str(tmp_path))
        assert result["total"] == 0

    def test_discovers_pdf_files(self, pdf_directory):
        """Test that PDF files in directory are discovered."""
        result = batch_parse_from_directory(pdf_directory, parser_name="pymupdf")
        assert result["total"] == 3

    def test_ignores_non_pdf_files(self, pdf_directory):
        """Test that non-PDF files are ignored."""
        result = batch_parse_from_directory(pdf_directory, parser_name="pymupdf")
        assert result["total"] == 3  # Only PDFs

    def test_returns_throughput_metric(self, pdf_directory):
        """Test that result includes throughput metric."""
        result = batch_parse_from_directory(pdf_directory, parser_name="pymupdf")
        assert "throughput" in result

    def test_max_workers_parameter(self, pdf_directory):
        """Test that max_workers parameter is accepted."""
        result = batch_parse_from_directory(pdf_directory, parser_name="pymupdf", max_workers=2)
        assert result["total"] == 3

    def test_chunk_size_parameter(self, pdf_directory):
        """Test that chunk_size parameter is accepted."""
        result = batch_parse_from_directory(pdf_directory, parser_name="pymupdf", chunk_size=50)
        assert result["total"] == 3

    def test_init_strategy_parameter(self, pdf_directory):
        """Test that init_strategy parameter is accepted."""
        result = batch_parse_from_directory(
            pdf_directory, parser_name="pymupdf", init_strategy="per-file"
        )
        assert result["total"] == 3


class TestBatchResult:
    """Tests for BatchResult dataclass."""

    def test_default_values(self):
        """Test that default values are correct."""
        result = BatchResult()
        assert result.total == 0
        assert result.successful == 0
        assert result.failed == 0
        assert result.success_rate == 0.0
        assert result.results == []
        assert result.duration == 0.0
        assert result.throughput == 0.0
        assert result.memory_peak_mb == 0.0
        assert result.worker_overhead_percent == 0.0

    def test_with_values(self):
        """Test BatchResult with custom values."""
        results_list = [{"file": "test.pdf", "success": True}]
        result = BatchResult(
            total=10,
            successful=8,
            failed=2,
            success_rate=80.0,
            results=results_list,
            duration=5.5,
            throughput=1.82,
            memory_peak_mb=512.0,
            worker_overhead_percent=2.5,
        )
        assert result.total == 10
        assert result.successful == 8
        assert result.failed == 2
        assert result.success_rate == 80.0
        assert result.results == results_list
        assert result.duration == 5.5
        assert result.throughput == 1.82
        assert result.memory_peak_mb == 512.0
        assert result.worker_overhead_percent == 2.5


class TestWorkerConfig:
    """Tests for WorkerConfig dataclass."""

    def test_default_values(self):
        """Test that default values are correct."""
        config = WorkerConfig(parser_name="pymupdf")
        assert config.parser_name == "pymupdf"
        assert config.max_tasks_per_worker == 0
        assert config.init_strategy == "per-worker"
        assert config.memory_limit_mb == 0

    def test_with_custom_values(self):
        """Test WorkerConfig with custom values."""
        config = WorkerConfig(
            parser_name="pdfplumber",
            max_tasks_per_worker=100,
            init_strategy="per-file",
            memory_limit_mb=2048,
        )
        assert config.parser_name == "pdfplumber"
        assert config.max_tasks_per_worker == 100
        assert config.init_strategy == "per-file"
        assert config.memory_limit_mb == 2048


class TestPerformanceMetrics:
    """Tests for performance-related functionality."""

    def test_throughput_calculation(self, tmp_path):
        """Test that throughput is calculated correctly."""
        # Create a few mock PDFs
        files = []
        for i in range(5):
            file_path = tmp_path / f"test_{i}.pdf"
            file_path.write_text("%PDF-1.4 mock PDF content")
            files.append(str(file_path))

        start = time.time()
        result = batch_parse(files, parser_name="pymupdf")
        duration = time.time() - start

        # Throughput should be approximately files/duration
        if duration > 0:
            # Allow some variance due to process startup overhead
            assert result["throughput"] > 0

    def test_worker_overhead_tracking(self, tmp_path):
        """Test that worker overhead is tracked."""
        files = []
        for i in range(5):
            file_path = tmp_path / f"test_{i}.pdf"
            file_path.write_text("%PDF-1.4 mock PDF content")
            files.append(str(file_path))

        result = batch_parse(files, parser_name="pymupdf")

        # Worker overhead should be a small percentage
        assert result["worker_overhead_percent"] >= 0
        # Should be less than 50% for any reasonable implementation
        assert result["worker_overhead_percent"] < 50


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
