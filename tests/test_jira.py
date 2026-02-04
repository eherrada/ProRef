"""Tests for app/jira/ modules."""

import pytest
from unittest.mock import patch, MagicMock
import requests


class TestJiraFetcher:
    """Test Jira fetcher module."""

    @patch('app.jira.fetcher._fetch_from_jira')
    @patch('app.jira.fetcher.validate_jira_config')
    @patch('app.jira.fetcher.init_db')
    @patch('app.jira.fetcher.get_jql')
    @patch('app.jira.fetcher.save_or_update_ticket')
    def test_fetch_backlog_success(
        self, mock_save, mock_jql, mock_init_db, mock_validate, mock_fetch
    ):
        """Should fetch and save tickets from Jira."""
        mock_jql.return_value = "project = TEST"
        mock_fetch.return_value = [
            {
                "key": "PROJ-101",
                "fields": {
                    "summary": "Test issue",
                    "description": "Description",
                    "status": {"name": "To Do"},
                    "issuetype": {"name": "Story"},
                    "updated": "2024-01-15T10:30:00.000+0000"
                }
            },
            {
                "key": "PROJ-102",
                "fields": {
                    "summary": "Another issue",
                    "description": "Description 2",
                    "status": {"name": "Done"},
                    "issuetype": {"name": "Bug"},
                    "updated": "2024-01-16T14:00:00.000+0000"
                }
            }
        ]

        from app.jira.fetcher import fetch_backlog

        count = fetch_backlog(verbose=False)

        assert count == 2
        assert mock_save.call_count == 2

    @patch('app.jira.fetcher._fetch_from_jira')
    @patch('app.jira.fetcher.validate_jira_config')
    @patch('app.jira.fetcher.init_db')
    @patch('app.jira.fetcher.get_jql')
    def test_fetch_backlog_skips_spikes(
        self, mock_jql, mock_init_db, mock_validate, mock_fetch
    ):
        """Should skip tickets with issue type 'spike'."""
        mock_jql.return_value = "project = TEST"
        mock_fetch.return_value = [
            {
                "key": "PROJ-101",
                "fields": {
                    "summary": "A Spike",
                    "description": "Research task",
                    "status": {"name": "To Do"},
                    "issuetype": {"name": "Spike"},
                    "updated": "2024-01-15T10:30:00.000+0000"
                }
            }
        ]

        from app.jira.fetcher import fetch_backlog

        with patch('app.jira.fetcher.save_or_update_ticket') as mock_save:
            count = fetch_backlog(verbose=False)

        assert count == 0
        mock_save.assert_not_called()

    @patch('app.jira.fetcher._fetch_from_jira')
    @patch('app.jira.fetcher.validate_jira_config')
    @patch('app.jira.fetcher.init_db')
    @patch('app.jira.fetcher.get_jql')
    def test_fetch_backlog_handles_api_error(
        self, mock_jql, mock_init_db, mock_validate, mock_fetch
    ):
        """Should handle API errors gracefully."""
        mock_jql.return_value = "project = TEST"
        mock_fetch.side_effect = requests.RequestException("API Error")

        from app.jira.fetcher import fetch_backlog

        count = fetch_backlog(verbose=False)

        assert count == 0


class TestJiraPublisher:
    """Test Jira publisher module."""

    @patch('app.jira.publisher.requests.post')
    @patch('app.jira.publisher.validate_jira_config')
    def test_post_comment_success(self, mock_validate, mock_post):
        """Should post comment to Jira."""
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_response

        with patch('app.jira.publisher.JIRA_BASE_URL', 'https://test.atlassian.net'):
            with patch('app.jira.publisher.JIRA_USER', 'user'):
                with patch('app.jira.publisher.JIRA_API_TOKEN', 'token'):
                    from app.jira.publisher import post_comment_to_jira

                    result = post_comment_to_jira("TEST-123", "Test comment")

        assert result is True
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        assert "TEST-123" in call_args[0][0]

    @patch('app.jira.publisher.requests.post')
    @patch('app.jira.publisher.validate_jira_config')
    def test_post_comment_uses_adf_format(self, mock_validate, mock_post):
        """Should use ADF format for comment body."""
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_response

        with patch('app.jira.publisher.JIRA_BASE_URL', 'https://test.atlassian.net'):
            with patch('app.jira.publisher.JIRA_USER', 'user'):
                with patch('app.jira.publisher.JIRA_API_TOKEN', 'token'):
                    from app.jira.publisher import post_comment_to_jira

                    post_comment_to_jira("TEST-123", "My comment")

        call_args = mock_post.call_args
        json_data = call_args.kwargs.get('json') or call_args[1].get('json')
        assert json_data['body']['type'] == 'doc'
        assert json_data['body']['version'] == 1

    def test_format_questions_for_jira(self):
        """Should format questions as ADF bullet list."""
        from app.jira.publisher import format_questions_for_jira

        questions = ["Question 1?", "Question 2?", "Question 3?"]
        result = format_questions_for_jira(questions)

        # Check it's a valid ADF document
        assert result["type"] == "doc"
        assert result["version"] == 1

        # Check content structure
        content = result["content"]
        assert len(content) >= 2

        # First should be heading
        assert content[0]["type"] == "heading"
        assert "Refinement Questions" in content[0]["content"][0]["text"]

        # Second should be bullet list
        assert content[1]["type"] == "bulletList"
        assert len(content[1]["content"]) == 3

    def test_format_test_cases_for_jira(self):
        """Should format test cases as ADF document."""
        from app.jira.publisher import format_test_cases_for_jira

        test_cases = [
            {
                "id": "1",
                "title": "Happy path",
                "pre": "User logged in",
                "steps": "1. Click button\n2. Fill form",
                "expected": "Success message"
            }
        ]
        result = format_test_cases_for_jira(test_cases)

        # Check it's a valid ADF document
        assert result["type"] == "doc"
        assert result["version"] == 1

        # Check content structure
        content = result["content"]
        assert len(content) >= 1

        # First should be heading
        assert content[0]["type"] == "heading"
        assert "Test Cases" in content[0]["content"][0]["text"]

    def test_format_test_cases_handles_old_format(self):
        """Should handle old string format for backwards compatibility."""
        from app.jira.publisher import format_test_cases_for_jira

        test_cases = ["Scenario: Test", "Action: Do something", "Expected: Result"]
        result = format_test_cases_for_jira(test_cases)

        # Should still produce valid ADF
        assert result["type"] == "doc"
        assert result["version"] == 1
