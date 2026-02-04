"""Tests for question and test case generators."""

import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime

from app.db.model import Ticket


class TestQuestionGenerator:
    """Test question generator module."""

    def test_empty_description_returns_empty(self):
        """Should return empty list for ticket without description."""
        from app.logic.question_generator import generate_questions

        ticket = Ticket(
            id="TEST-1",
            jira_key="TEST-1",
            title="Test",
            description=None,
            issue_type="story"
        )

        result = generate_questions(ticket)
        assert result == []

    def test_empty_title_returns_empty(self):
        """Should return empty list for ticket without title."""
        from app.logic.question_generator import generate_questions

        ticket = Ticket(
            id="TEST-1",
            jira_key="TEST-1",
            title=None,
            description="Some description",
            issue_type="story"
        )

        result = generate_questions(ticket)
        assert result == []

    def test_generates_questions_from_api(self):
        """Should parse questions from API response."""
        from app.logic.question_generator import generate_questions

        mock_config = {
            "ai_provider": "openai",
            "openai": {
                "api_key": "test-key",
                "model_questions": "gpt-4"
            }
        }

        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(message=MagicMock(content="- Question 1?\n- Question 2?\n- Question 3?"))
        ]

        ticket = Ticket(
            id="TEST-1",
            jira_key="TEST-1",
            title="Test Ticket",
            description="Test description for generating questions.",
            issue_type="story"
        )

        with patch('app.logic.question_generator.load_config', return_value=mock_config):
            with patch('app.logic.question_generator.OpenAI') as mock_openai:
                mock_client = MagicMock()
                mock_client.chat.completions.create.return_value = mock_response
                mock_openai.return_value = mock_client

                result = generate_questions(ticket)

                assert len(result) == 3
                assert "Question 1?" in result
                assert "Question 2?" in result
                assert "Question 3?" in result

    def test_strips_bullet_prefixes(self):
        """Should strip bullet points and numbers from questions."""
        from app.logic.question_generator import generate_questions

        mock_config = {
            "ai_provider": "openai",
            "openai": {
                "api_key": "test-key",
                "model_questions": "gpt-4"
            }
        }

        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(message=MagicMock(content="1. First question?\n* Second question?\n- Third question?"))
        ]

        ticket = Ticket(
            id="TEST-1",
            jira_key="TEST-1",
            title="Test",
            description="Description",
            issue_type="story"
        )

        with patch('app.logic.question_generator.load_config', return_value=mock_config):
            with patch('app.logic.question_generator.OpenAI') as mock_openai:
                mock_client = MagicMock()
                mock_client.chat.completions.create.return_value = mock_response
                mock_openai.return_value = mock_client

                result = generate_questions(ticket)

                assert "First question?" in result
                assert "Second question?" in result
                assert "Third question?" in result
                # Should not have bullet prefixes
                assert not any(q.startswith("-") or q.startswith("*") or q[0].isdigit() for q in result)

    def test_handles_api_error(self):
        """Should raise exception on API error."""
        from app.logic.question_generator import generate_questions

        mock_config = {
            "ai_provider": "openai",
            "openai": {
                "api_key": "test-key",
                "model_questions": "gpt-4"
            }
        }

        ticket = Ticket(
            id="TEST-1",
            jira_key="TEST-1",
            title="Test",
            description="Description",
            issue_type="story"
        )

        with patch('app.logic.question_generator.load_config', return_value=mock_config):
            with patch('app.logic.question_generator.OpenAI') as mock_openai:
                mock_client = MagicMock()
                mock_client.chat.completions.create.side_effect = Exception("API Error")
                mock_openai.return_value = mock_client

                with pytest.raises(Exception):
                    generate_questions(ticket)


class TestTestCaseGenerator:
    """Test test case generator module."""

    def test_empty_description_returns_empty(self):
        """Should return empty list for ticket without description."""
        from app.logic.test_case_generator import generate_test_cases

        ticket = Ticket(
            id="TEST-1",
            jira_key="TEST-1",
            title="Test",
            description=None,
            issue_type="story"
        )

        result = generate_test_cases(ticket)
        assert result == []

    def test_empty_title_returns_empty(self):
        """Should return empty list for ticket without title."""
        from app.logic.test_case_generator import generate_test_cases

        ticket = Ticket(
            id="TEST-1",
            jira_key="TEST-1",
            title=None,
            description="Some description",
            issue_type="story"
        )

        result = generate_test_cases(ticket)
        assert result == []

    def test_generates_test_cases_from_api(self):
        """Should parse test cases from API response."""
        from app.logic.test_case_generator import generate_test_cases

        mock_config = {
            "ai_provider": "openai",
            "openai": {
                "api_key": "test-key",
                "model_testcases": "gpt-4"
            }
        }

        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(message=MagicMock(content="""TC-1: Happy path login
PRE: User exists in system
STEPS:
1. Navigate to login
2. Enter credentials
3. Click submit
EXPECTED: User is logged in

TC-2: Invalid credentials
PRE: User exists
STEPS:
1. Navigate to login
2. Enter wrong password
EXPECTED: Error message shown"""))
        ]

        ticket = Ticket(
            id="TEST-1",
            jira_key="TEST-1",
            title="Test Ticket",
            description="Test description for generating test cases.",
            issue_type="story"
        )

        with patch('app.logic.test_case_generator.load_config', return_value=mock_config):
            with patch('app.logic.test_case_generator.OpenAI') as mock_openai:
                mock_client = MagicMock()
                mock_client.chat.completions.create.return_value = mock_response
                mock_openai.return_value = mock_client

                result = generate_test_cases(ticket)

                assert len(result) == 2
                assert result[0]["id"] == "1"
                assert "Happy path" in result[0]["title"]

    def test_handles_api_error(self):
        """Should raise exception on API error."""
        from app.logic.test_case_generator import generate_test_cases

        mock_config = {
            "ai_provider": "openai",
            "openai": {
                "api_key": "test-key",
                "model_testcases": "gpt-4"
            }
        }

        ticket = Ticket(
            id="TEST-1",
            jira_key="TEST-1",
            title="Test",
            description="Description",
            issue_type="story"
        )

        with patch('app.logic.test_case_generator.load_config', return_value=mock_config):
            with patch('app.logic.test_case_generator.OpenAI') as mock_openai:
                mock_client = MagicMock()
                mock_client.chat.completions.create.side_effect = Exception("API Error")
                mock_openai.return_value = mock_client

                with pytest.raises(Exception):
                    generate_test_cases(ticket)
