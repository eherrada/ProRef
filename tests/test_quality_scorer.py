"""Tests for quality scorer module."""

import pytest
from unittest.mock import MagicMock, patch


class TestScoreTicketQuality:
    """Tests for score_ticket_quality function."""

    def test_empty_ticket_returns_min_score(self):
        """Empty ticket should return score of 1."""
        from app.logic.quality_scorer import score_ticket_quality

        ticket = MagicMock()
        ticket.title = None
        ticket.description = None
        ticket.issue_type = None

        result = score_ticket_quality(ticket)

        assert result["score"] == 1
        assert "no content" in result["summary"].lower()
        assert len(result["issues"]) >= 2

    def test_fallback_score_basic_ticket(self):
        """Basic ticket with short content gets lower score."""
        from app.logic.quality_scorer import _fallback_score

        ticket = MagicMock()
        ticket.title = "Fix bug"
        ticket.description = "There is a bug"
        ticket.issue_type = "Bug"

        result = _fallback_score(ticket)

        assert result["score"] < 5
        assert len(result["issues"]) > 0

    def test_fallback_score_good_ticket(self):
        """Well-defined ticket gets higher score."""
        from app.logic.quality_scorer import _fallback_score

        ticket = MagicMock()
        ticket.title = "Implement user authentication flow with OAuth2"
        ticket.description = """
        As a user, I want to be able to login using OAuth2.

        Acceptance Criteria:
        - User can click "Login with Google"
        - User is redirected to Google OAuth
        - After auth, user is redirected back

        Edge cases:
        - Handle invalid tokens
        - Handle network errors
        - Empty state when no user logged in
        """
        ticket.issue_type = "Story"

        result = _fallback_score(ticket)

        assert result["score"] >= 5


class TestParseScoreResponse:
    """Tests for _parse_score_response function."""

    def test_parses_valid_response(self):
        """Should parse valid AI response."""
        from app.logic.quality_scorer import _parse_score_response

        content = """SCORE: 7
SUMMARY: Good ticket with minor gaps
ISSUES:
- Missing edge cases
- No error handling mentioned
SUGGESTIONS:
- Add acceptance criteria
- Consider edge cases"""

        result = _parse_score_response(content)

        assert result["score"] == 7
        assert "Good ticket" in result["summary"]
        assert len(result["issues"]) == 2
        assert len(result["suggestions"]) == 2

    def test_handles_score_with_slash(self):
        """Should handle score format like 7/10."""
        from app.logic.quality_scorer import _parse_score_response

        content = """SCORE: 7/10
SUMMARY: Adequate ticket"""

        result = _parse_score_response(content)

        assert result["score"] == 7

    def test_clamps_score_to_valid_range(self):
        """Score should be clamped between 1 and 10."""
        from app.logic.quality_scorer import _parse_score_response

        content = """SCORE: 15
SUMMARY: Test"""

        result = _parse_score_response(content)

        assert result["score"] == 10


class TestScoreHelpers:
    """Tests for helper functions."""

    def test_get_score_color(self):
        """Should return correct color class for scores."""
        from app.logic.quality_scorer import get_score_color

        assert get_score_color(9) == "success"
        assert get_score_color(8) == "success"
        assert get_score_color(6) == "warning"
        assert get_score_color(5) == "warning"
        assert get_score_color(3) == "error"

    def test_get_score_label(self):
        """Should return correct label for scores."""
        from app.logic.quality_scorer import get_score_label

        assert get_score_label(9) == "Ready"
        assert get_score_label(6) == "Needs Work"
        assert get_score_label(3) == "Not Ready"
