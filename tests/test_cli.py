"""Tests for app/cli.py - Integration tests with mocked dependencies."""

import pytest
from unittest.mock import patch, MagicMock
from typer.testing import CliRunner

from app.cli import app
from app.db.model import Ticket, GeneratedContent


runner = CliRunner()


class TestStatusCommand:
    """Test the status command."""

    @patch('app.cli.SessionLocal')
    def test_status_shows_counts(self, mock_session_class):
        """Should display ticket and publication counts."""
        mock_session = MagicMock()
        mock_session_class.return_value = mock_session

        # Mock query results
        mock_session.query.return_value.count.return_value = 10
        mock_session.query.return_value.filter.return_value.count.return_value = 5

        result = runner.invoke(app, ["status"])

        assert result.exit_code == 0
        assert "ProRef Status" in result.output
        assert "Tickets:" in result.output


class TestFetchCommand:
    """Test the fetch command."""

    @patch('app.cli.fetch_backlog')
    def test_fetch_calls_fetcher(self, mock_fetch):
        """Should call fetch_backlog function."""
        mock_fetch.return_value = 5

        result = runner.invoke(app, ["fetch"])

        assert result.exit_code == 0
        mock_fetch.assert_called_once_with(verbose=True)
        assert "Done!" in result.output


class TestEmbedCommand:
    """Test the embed command."""

    @patch('app.cli.save_embedding')
    @patch('app.cli.get_embedding')
    @patch('app.cli.SessionLocal')
    def test_embed_processes_all_tickets(self, mock_session_class, mock_get_emb, mock_save_emb):
        """Should embed all tickets."""
        mock_session = MagicMock()
        mock_session_class.return_value = mock_session

        # Create mock tickets
        ticket1 = MagicMock(id="T1", jira_key="T1", title="Title 1", description="Desc 1")
        ticket2 = MagicMock(id="T2", jira_key="T2", title="Title 2", description="Desc 2")
        mock_session.query.return_value.all.return_value = [ticket1, ticket2]

        mock_get_emb.return_value = [0.1] * 1536

        result = runner.invoke(app, ["embed"])

        assert result.exit_code == 0
        assert mock_get_emb.call_count == 2
        assert mock_save_emb.call_count == 2


class TestQuestionsCommand:
    """Test the questions command."""

    @patch('app.cli.get_related_tickets_summary')
    @patch('app.cli.generate_questions')
    @patch('app.cli.ensure_dirs')
    @patch('app.cli.SessionLocal')
    def test_questions_generates_for_pending(
        self, mock_session_class, mock_ensure, mock_generate, mock_related
    ):
        """Should generate questions for pending tickets."""
        mock_session = MagicMock()
        mock_session_class.return_value = mock_session

        ticket = MagicMock()
        ticket.id = "T1"
        ticket.jira_key = "T1"
        ticket.title = "Test"
        ticket.issue_type = "story"
        ticket.questions_generated = False

        mock_session.query.return_value.filter.return_value.all.return_value = [ticket]
        mock_generate.return_value = ["Question 1?", "Question 2?"]
        mock_related.return_value = "No closely related tickets found."

        with patch('builtins.open', MagicMock()):
            result = runner.invoke(app, ["questions"])

        assert result.exit_code == 0
        mock_generate.assert_called_once()

    @patch('app.cli.ensure_dirs')
    @patch('app.cli.SessionLocal')
    def test_questions_no_pending(self, mock_session_class, mock_ensure):
        """Should handle no pending tickets."""
        mock_session = MagicMock()
        mock_session_class.return_value = mock_session
        mock_session.query.return_value.filter.return_value.all.return_value = []

        result = runner.invoke(app, ["questions"])

        assert result.exit_code == 0
        assert "No tickets pending" in result.output


class TestTestcasesCommand:
    """Test the testcases command."""

    @patch('app.cli.generate_test_cases')
    @patch('app.cli.ensure_dirs')
    @patch('app.cli.SessionLocal')
    def test_testcases_generates_for_pending(
        self, mock_session_class, mock_ensure, mock_generate
    ):
        """Should generate test cases for pending tickets."""
        mock_session = MagicMock()
        mock_session_class.return_value = mock_session

        ticket = MagicMock()
        ticket.id = "T1"
        ticket.jira_key = "T1"
        ticket.title = "Test"
        ticket.issue_type = "story"
        ticket.description = "Description"
        ticket.test_cases_generated = False

        mock_session.query.return_value.filter.return_value.all.return_value = [ticket]
        mock_generate.return_value = [
            "Scenario: Test",
            "Action: Do",
            "Expected behavior: Result"
        ]

        with patch('builtins.open', MagicMock()):
            result = runner.invoke(app, ["testcases"])

        assert result.exit_code == 0
        mock_generate.assert_called_once()


class TestPublishCommand:
    """Test the publish command."""

    @patch('app.cli.SessionLocal')
    def test_publish_no_pending(self, mock_session_class):
        """Should handle no pending content."""
        mock_session = MagicMock()
        mock_session_class.return_value = mock_session
        mock_session.query.return_value.filter.return_value.all.return_value = []

        result = runner.invoke(app, ["publish"])

        assert result.exit_code == 0
        assert "No pending content" in result.output

    @patch('app.cli.post_comment_to_jira')
    @patch('app.cli.format_questions_for_jira')
    @patch('app.cli.SessionLocal')
    def test_publish_with_confirmation(
        self, mock_session_class, mock_format, mock_post
    ):
        """Should publish with user confirmation."""
        mock_session = MagicMock()
        mock_session_class.return_value = mock_session

        # Create mock content
        content = MagicMock()
        content.id = 1
        content.ticket_id = "T1"
        content.content_type = "questions"
        content.content = '["Q1?", "Q2?"]'
        content.published = False

        ticket = MagicMock()
        ticket.jira_key = "PROJ-123"
        ticket.title = "Test Ticket"

        mock_session.query.return_value.filter.return_value.all.return_value = [content]
        mock_session.query.return_value.filter_by.return_value.first.return_value = ticket

        mock_format.return_value = "Formatted questions"
        mock_post.return_value = True

        # Simulate user input: P for Publish
        result = runner.invoke(app, ["publish"], input="P\n")

        assert result.exit_code == 0
        mock_post.assert_called_once()

    @patch('app.cli.SessionLocal')
    def test_publish_skip_option(self, mock_session_class):
        """Should allow skipping content."""
        mock_session = MagicMock()
        mock_session_class.return_value = mock_session

        content = MagicMock()
        content.id = 1
        content.ticket_id = "T1"
        content.content_type = "questions"
        content.content = '["Q1?"]'
        content.published = False

        ticket = MagicMock()
        ticket.jira_key = "PROJ-123"
        ticket.title = "Test"

        mock_session.query.return_value.filter.return_value.all.return_value = [content]
        mock_session.query.return_value.filter_by.return_value.first.return_value = ticket

        # Simulate user input: S for Skip
        result = runner.invoke(app, ["publish"], input="S\n")

        assert result.exit_code == 0
        assert "Skipped" in result.output

    @patch('app.cli.SessionLocal')
    def test_publish_cancel_option(self, mock_session_class):
        """Should allow cancelling all."""
        mock_session = MagicMock()
        mock_session_class.return_value = mock_session

        content = MagicMock()
        content.id = 1
        content.ticket_id = "T1"
        content.content_type = "questions"
        content.content = '["Q1?"]'
        content.published = False

        ticket = MagicMock()
        ticket.jira_key = "PROJ-123"
        ticket.title = "Test"

        mock_session.query.return_value.filter.return_value.all.return_value = [content]
        mock_session.query.return_value.filter_by.return_value.first.return_value = ticket

        # Simulate user input: C for Cancel
        result = runner.invoke(app, ["publish"], input="C\n")

        assert result.exit_code == 0
        assert "Cancelled" in result.output
