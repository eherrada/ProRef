"""Tests for app/paths.py"""

import pytest
from pathlib import Path


class TestPaths:
    """Test path configuration."""

    def test_project_root_exists(self):
        """PROJECT_ROOT should point to actual directory."""
        from app.paths import PROJECT_ROOT
        assert PROJECT_ROOT.exists()
        assert PROJECT_ROOT.is_dir()

    def test_data_dir_is_under_project_root(self):
        """DATA_DIR should be under PROJECT_ROOT."""
        from app.paths import PROJECT_ROOT, DATA_DIR
        assert DATA_DIR.parent == PROJECT_ROOT

    def test_subdirs_are_under_data_dir(self):
        """All subdirs should be under DATA_DIR."""
        from app.paths import DATA_DIR, QUESTIONS_DIR, TESTCASES_DIR, DOCS_DIR
        assert QUESTIONS_DIR.parent == DATA_DIR
        assert TESTCASES_DIR.parent == DATA_DIR
        assert DOCS_DIR.parent == DATA_DIR

    def test_db_path_is_under_data_dir(self):
        """DB_PATH should be under DATA_DIR."""
        from app.paths import DATA_DIR, DB_PATH
        assert DB_PATH.parent == DATA_DIR
        assert DB_PATH.name == "proref.db"

    def test_ensure_dirs_creates_directories(self, tmp_path, monkeypatch):
        """ensure_dirs should create all required directories."""
        # Patch the paths to use temp directory
        monkeypatch.setattr('app.paths.DATA_DIR', tmp_path / "data")
        monkeypatch.setattr('app.paths.QUESTIONS_DIR', tmp_path / "data" / "questions")
        monkeypatch.setattr('app.paths.TESTCASES_DIR', tmp_path / "data" / "test_cases")
        monkeypatch.setattr('app.paths.DOCS_DIR', tmp_path / "data" / "docs")

        from app.paths import ensure_dirs, QUESTIONS_DIR, TESTCASES_DIR, DOCS_DIR

        ensure_dirs()

        assert QUESTIONS_DIR.exists()
        assert TESTCASES_DIR.exists()
        assert DOCS_DIR.exists()
