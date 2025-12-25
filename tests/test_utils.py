"""Tests for utils.py"""

import pytest
import os
import json
import tempfile
import shutil
from datetime import datetime
from pathlib import Path

import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from utils import parse_datetime, json_prettify, read_file, write_file, analyze_repository_structure


class TestParseDatetime:
    """Tests for parse_datetime function."""

    def test_parse_datetime_object(self):
        """Test parsing a datetime object returns it unchanged."""
        dt = datetime(2025, 12, 25, 10, 30, 0)
        result = parse_datetime(dt)
        assert result == dt

    def test_parse_iso_format_with_z(self):
        """Test parsing ISO format string with Z timezone."""
        dt_string = "2025-12-25T10:30:00Z"
        result = parse_datetime(dt_string)
        assert isinstance(result, datetime)
        assert result.year == 2025
        assert result.month == 12
        assert result.day == 25

    def test_parse_iso_format_with_offset(self):
        """Test parsing ISO format string with timezone offset."""
        dt_string = "2025-12-25T10:30:00+00:00"
        result = parse_datetime(dt_string)
        assert isinstance(result, datetime)
        assert result.year == 2025

    def test_parse_common_format_with_z(self):
        """Test parsing common format with Z."""
        dt_string = "2025-12-25 10:30:00"
        result = parse_datetime(dt_string)
        assert isinstance(result, datetime)
        assert result.hour == 10
        assert result.minute == 30

    def test_parse_none_returns_none(self):
        """Test parsing None returns None."""
        result = parse_datetime(None)
        assert result is None

    def test_parse_invalid_string_returns_unchanged(self):
        """Test parsing invalid string returns it unchanged."""
        invalid = "not a date"
        result = parse_datetime(invalid)
        assert result == invalid


class TestJsonPrettify:
    """Tests for json_prettify function."""

    def test_prettify_simple_dict(self):
        """Test prettifying a simple dictionary."""
        data = {"key": "value", "number": 42}
        result = json_prettify(data)
        assert isinstance(result, str)
        assert "key" in result
        assert "value" in result
        # Should be indented
        assert "\n" in result

    def test_prettify_nested_dict(self):
        """Test prettifying a nested dictionary."""
        data = {"outer": {"inner": "value"}}
        result = json_prettify(data)
        assert "outer" in result
        assert "inner" in result

    def test_prettify_with_datetime(self):
        """Test prettifying data with datetime (uses default=str)."""
        data = {"timestamp": datetime(2025, 12, 25)}
        result = json_prettify(data)
        assert "timestamp" in result
        assert "2025" in result


class TestReadWriteFile:
    """Tests for read_file and write_file functions."""

    def test_write_and_read_file(self):
        """Test writing and reading a file."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
            temp_path = f.name

        try:
            content = "Hello, World!\nLine 2"
            write_file(temp_path, content)

            read_content = read_file(temp_path)
            assert read_content == content
        finally:
            os.unlink(temp_path)

    def test_read_file_with_unicode(self):
        """Test reading file with unicode characters."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, encoding='utf-8') as f:
            temp_path = f.name
            f.write("Hello 世界 🌍")

        try:
            content = read_file(temp_path)
            assert "世界" in content
            assert "🌍" in content
        finally:
            os.unlink(temp_path)

    def test_read_nonexistent_file_raises(self):
        """Test reading nonexistent file raises error."""
        with pytest.raises(FileNotFoundError):
            read_file("/nonexistent/path/file.txt")


class TestAnalyzeRepositoryStructure:
    """Tests for analyze_repository_structure function."""

    def setup_method(self):
        """Create a temporary directory structure for testing."""
        self.temp_dir = tempfile.mkdtemp()

    def teardown_method(self):
        """Clean up temporary directory."""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def test_analyze_empty_directory(self):
        """Test analyzing an empty directory."""
        result = analyze_repository_structure(self.temp_dir)
        assert result['file_count'] == 0
        assert result['dir_count'] == 0

    def test_analyze_with_files(self):
        """Test analyzing directory with files."""
        # Create some files
        Path(self.temp_dir, "file1.txt").touch()
        Path(self.temp_dir, "file2.py").touch()

        result = analyze_repository_structure(self.temp_dir)
        assert result['file_count'] == 2
        assert result['dir_count'] == 0

    def test_analyze_with_subdirectories(self):
        """Test analyzing directory with subdirectories and files."""
        # Create subdirectories
        subdir1 = Path(self.temp_dir, "subdir1")
        subdir2 = Path(self.temp_dir, "subdir2")
        subdir1.mkdir()
        subdir2.mkdir()

        # Create files in subdirectories
        Path(subdir1, "file1.txt").touch()
        Path(subdir2, "file2.txt").touch()
        Path(self.temp_dir, "root_file.txt").touch()

        result = analyze_repository_structure(self.temp_dir)
        assert result['file_count'] == 3
        assert result['dir_count'] == 2

    def test_analyze_excludes_git_directory(self):
        """Test that .git directory is excluded from analysis."""
        # Create .git directory with files
        git_dir = Path(self.temp_dir, ".git")
        git_dir.mkdir()
        Path(git_dir, "config").touch()
        Path(git_dir, "HEAD").touch()

        # Create regular files
        Path(self.temp_dir, "file.txt").touch()

        result = analyze_repository_structure(self.temp_dir)
        # Should only count the regular file, not .git contents
        assert result['file_count'] == 1
        assert result['dir_count'] == 0  # .git dir should be excluded

    def test_analyze_nested_structure(self):
        """Test analyzing deeply nested directory structure."""
        # Create nested structure: root/a/b/c
        nested = Path(self.temp_dir, "a", "b", "c")
        nested.mkdir(parents=True)

        # Create files at different levels
        Path(self.temp_dir, "root.txt").touch()
        Path(self.temp_dir, "a", "a.txt").touch()
        Path(self.temp_dir, "a", "b", "b.txt").touch()
        Path(nested, "c.txt").touch()

        result = analyze_repository_structure(self.temp_dir)
        assert result['file_count'] == 4
        assert result['dir_count'] == 3  # a, b, c
