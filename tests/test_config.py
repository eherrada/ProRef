"""Tests for app/config.py"""

import os
import pytest
from unittest.mock import patch, MagicMock


class TestConfig:
    """Test configuration module."""

    def test_model_defaults(self):
        """Test default model values."""
        from app.config import MODEL_QUESTIONS, MODEL_TESTCASES, MODEL_CHAT, MODEL_EMBEDDING

        # These should have default values
        assert MODEL_QUESTIONS is not None
        assert MODEL_TESTCASES is not None
        assert MODEL_CHAT is not None
        assert MODEL_EMBEDDING is not None

    def test_get_jql_with_direct_jql(self):
        """get_jql should return jql if set in config."""
        from app.config import get_jql

        mock_config = {
            "jira": {
                "jql": "project = TEST",
                "project": "",
                "sprint": ""
            }
        }

        with patch('app.config.load_config', return_value=mock_config):
            result = get_jql()
            assert result == "project = TEST"

    def test_get_jql_with_project_and_sprint(self):
        """get_jql should construct JQL from project and sprint."""
        from app.config import get_jql

        mock_config = {
            "jira": {
                "jql": "",
                "project": "MYPROJ",
                "sprint": "Sprint 1"
            }
        }

        with patch('app.config.load_config', return_value=mock_config):
            result = get_jql()
            assert "project = MYPROJ" in result
            assert 'Sprint = "Sprint 1"' in result

    def test_get_jql_raises_without_config(self):
        """get_jql should raise if no JQL config is set."""
        from app.config import get_jql

        mock_config = {
            "jira": {
                "jql": "",
                "project": "",
                "sprint": ""
            }
        }

        with patch('app.config.load_config', return_value=mock_config):
            with pytest.raises(ValueError) as exc_info:
                get_jql()
            assert "JIRA_JQL" in str(exc_info.value)

    def test_validate_jira_config_raises_without_credentials(self):
        """validate_jira_config should raise if credentials missing."""
        from app.config import validate_jira_config

        mock_config = {
            "jira": {
                "base_url": "",
                "user": "user",
                "api_token": "token"
            }
        }

        with patch('app.config.load_config', return_value=mock_config):
            with pytest.raises(ValueError) as exc_info:
                validate_jira_config()
            assert "JIRA_BASE_URL" in str(exc_info.value)

    def test_validate_jira_config_passes_with_all_credentials(self):
        """validate_jira_config should pass when all credentials present."""
        from app.config import validate_jira_config

        mock_config = {
            "jira": {
                "base_url": "https://test.atlassian.net",
                "user": "user@test.com",
                "api_token": "test-token"
            }
        }

        with patch('app.config.load_config', return_value=mock_config):
            # Should not raise
            validate_jira_config()

    def test_default_config_has_required_keys(self):
        """DEFAULT_CONFIG should have all required keys."""
        from app.config import DEFAULT_CONFIG

        assert "ai_provider" in DEFAULT_CONFIG
        assert "openai" in DEFAULT_CONFIG
        assert "anthropic" in DEFAULT_CONFIG
        assert "google" in DEFAULT_CONFIG
        assert "jira" in DEFAULT_CONFIG

        # Check nested keys
        assert "api_key" in DEFAULT_CONFIG["openai"]
        assert "model_questions" in DEFAULT_CONFIG["openai"]
        assert "base_url" in DEFAULT_CONFIG["jira"]

    def test_get_model_for_task(self):
        """get_model_for_task should return correct model."""
        from app.config import get_model_for_task

        mock_config = {
            "ai_provider": "openai",
            "openai": {
                "model_questions": "gpt-4-turbo",
                "model_testcases": "gpt-3.5-turbo"
            }
        }

        with patch('app.config.load_config', return_value=mock_config):
            assert get_model_for_task("questions") == "gpt-4-turbo"
            assert get_model_for_task("testcases") == "gpt-3.5-turbo"
