"""Tests for save module."""

import pytest
from unittest.mock import MagicMock, patch


class TestComputeContentHash:
    """Tests for _compute_content_hash function."""

    def test_computes_hash(self):
        """Should compute MD5 hash of content."""
        from app.db.save import _compute_content_hash

        hash1 = _compute_content_hash("Title", "Description")
        hash2 = _compute_content_hash("Title", "Description")

        assert hash1 == hash2
        assert len(hash1) == 32  # MD5 hash length

    def test_different_content_different_hash(self):
        """Different content should produce different hash."""
        from app.db.save import _compute_content_hash

        hash1 = _compute_content_hash("Title 1", "Description 1")
        hash2 = _compute_content_hash("Title 2", "Description 2")

        assert hash1 != hash2

    def test_handles_none_values(self):
        """Should handle None values gracefully."""
        from app.db.save import _compute_content_hash

        hash1 = _compute_content_hash(None, None)
        hash2 = _compute_content_hash("", "")

        # None treated as empty string
        assert hash1 == hash2


class TestSaveQualityScore:
    """Tests for save_quality_score function."""

    @patch('app.db.save.SessionLocal')
    def test_saves_quality_data(self, mock_session):
        """Should save all quality score fields."""
        from app.db.save import save_quality_score

        mock_ticket = MagicMock()
        mock_session_instance = MagicMock()
        mock_session.return_value = mock_session_instance
        mock_session_instance.query.return_value.filter_by.return_value.first.return_value = mock_ticket

        score_data = {
            "score": 7,
            "summary": "Good ticket",
            "issues": ["Issue 1", "Issue 2"],
            "suggestions": ["Suggestion 1"]
        }

        save_quality_score("ticket-id", score_data)

        assert mock_ticket.quality_score == 7
        assert mock_ticket.quality_summary == "Good ticket"
        mock_session_instance.commit.assert_called_once()

    @patch('app.db.save.SessionLocal')
    def test_handles_missing_ticket(self, mock_session):
        """Should handle case when ticket not found."""
        from app.db.save import save_quality_score

        mock_session_instance = MagicMock()
        mock_session.return_value = mock_session_instance
        mock_session_instance.query.return_value.filter_by.return_value.first.return_value = None

        # Should not raise error
        save_quality_score("nonexistent-id", {"score": 5})

        mock_session_instance.commit.assert_not_called()


class TestMarkContentReviewed:
    """Tests for mark_content_reviewed function."""

    @patch('app.db.save.SessionLocal')
    def test_marks_content_as_reviewed(self, mock_session):
        """Should set content_changed to False."""
        from app.db.save import mark_content_reviewed

        mock_ticket = MagicMock()
        mock_ticket.content_changed = True
        mock_session_instance = MagicMock()
        mock_session.return_value = mock_session_instance
        mock_session_instance.query.return_value.filter_by.return_value.first.return_value = mock_ticket

        mark_content_reviewed("ticket-id")

        assert mock_ticket.content_changed == False
        mock_session_instance.commit.assert_called_once()


class TestResetTicketForRegeneration:
    """Tests for reset_ticket_for_regeneration function."""

    @patch('app.db.save.SessionLocal')
    def test_resets_all_flags(self, mock_session):
        """Should reset questions and tests flags by default."""
        from app.db.save import reset_ticket_for_regeneration

        mock_ticket = MagicMock()
        mock_ticket.questions_generated = True
        mock_ticket.test_cases_generated = True
        mock_ticket.content_changed = True

        mock_session_instance = MagicMock()
        mock_session.return_value = mock_session_instance
        mock_session_instance.query.return_value.filter_by.return_value.first.return_value = mock_ticket

        reset_ticket_for_regeneration("ticket-id")

        assert mock_ticket.questions_generated == False
        assert mock_ticket.test_cases_generated == False
        assert mock_ticket.content_changed == False

    @patch('app.db.save.SessionLocal')
    def test_resets_only_questions(self, mock_session):
        """Should only reset questions when specified."""
        from app.db.save import reset_ticket_for_regeneration

        mock_ticket = MagicMock()
        mock_ticket.questions_generated = True
        mock_ticket.test_cases_generated = True

        mock_session_instance = MagicMock()
        mock_session.return_value = mock_session_instance
        mock_session_instance.query.return_value.filter_by.return_value.first.return_value = mock_ticket

        reset_ticket_for_regeneration("ticket-id", reset_questions=True, reset_tests=False)

        assert mock_ticket.questions_generated == False
        # test_cases_generated not changed when reset_tests=False
