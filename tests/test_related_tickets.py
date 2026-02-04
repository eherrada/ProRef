"""Tests for app/logic/related_tickets.py"""

import pytest
from unittest.mock import patch, MagicMock

from app.db.model import Ticket


class TestFindRelatedTickets:
    """Test find_related_tickets function."""

    @patch('app.logic.related_tickets.get_all_embeddings')
    def test_returns_empty_if_ticket_not_found(self, mock_get_embeddings):
        """Should return empty list if target ticket has no embedding."""
        mock_get_embeddings.return_value = []

        from app.logic.related_tickets import find_related_tickets

        result = find_related_tickets("NONEXISTENT-123")

        assert result == []

    @patch('app.logic.related_tickets.get_all_embeddings')
    @patch('app.logic.related_tickets.cosine_similarity')
    def test_filters_by_threshold(self, mock_similarity, mock_get_embeddings):
        """Should filter out tickets below threshold."""
        ticket1 = Ticket(id="T1", jira_key="T1", title="Target")
        ticket2 = Ticket(id="T2", jira_key="T2", title="Similar")
        ticket3 = Ticket(id="T3", jira_key="T3", title="Different")

        mock_get_embeddings.return_value = [
            (ticket1, [0.1] * 1536),
            (ticket2, [0.1] * 1536),
            (ticket3, [0.9] * 1536),
        ]

        # T1 to T2: high similarity, T1 to T3: low similarity
        def similarity_side_effect(v1, v2):
            if v1 == v2:
                return 1.0
            # Assuming T2 is similar, T3 is different
            return 0.9 if v2 == [0.1] * 1536 else 0.5

        mock_similarity.side_effect = similarity_side_effect

        from app.logic.related_tickets import find_related_tickets

        result = find_related_tickets("T1", threshold=0.8)

        # Should only include T2 (score 0.9 >= 0.8)
        ticket_ids = [t.id for t, _ in result]
        assert "T2" in ticket_ids
        assert "T3" not in ticket_ids

    @patch('app.logic.related_tickets.get_all_embeddings')
    @patch('app.logic.related_tickets.cosine_similarity')
    def test_excludes_self(self, mock_similarity, mock_get_embeddings):
        """Should not include the target ticket itself."""
        ticket1 = Ticket(id="T1", jira_key="T1", title="Target")

        mock_get_embeddings.return_value = [
            (ticket1, [0.1] * 1536),
        ]
        mock_similarity.return_value = 1.0

        from app.logic.related_tickets import find_related_tickets

        result = find_related_tickets("T1", threshold=0.8)

        assert len(result) == 0

    @patch('app.logic.related_tickets.get_all_embeddings')
    @patch('app.logic.related_tickets.cosine_similarity')
    def test_limits_results(self, mock_similarity, mock_get_embeddings):
        """Should limit results to top_k."""
        tickets = [
            Ticket(id=f"T{i}", jira_key=f"T{i}", title=f"Ticket {i}")
            for i in range(10)
        ]
        mock_get_embeddings.return_value = [
            (t, [0.1] * 1536) for t in tickets
        ]
        mock_similarity.return_value = 0.9

        from app.logic.related_tickets import find_related_tickets

        result = find_related_tickets("T0", threshold=0.8, top_k=3)

        assert len(result) <= 3

    @patch('app.logic.related_tickets.get_all_embeddings')
    @patch('app.logic.related_tickets.cosine_similarity')
    def test_sorts_by_similarity(self, mock_similarity, mock_get_embeddings):
        """Should sort results by similarity score (descending)."""
        ticket1 = Ticket(id="T1", jira_key="T1", title="Target")
        ticket2 = Ticket(id="T2", jira_key="T2", title="Most similar")
        ticket3 = Ticket(id="T3", jira_key="T3", title="Less similar")

        mock_get_embeddings.return_value = [
            (ticket1, [1.0, 0.0]),
            (ticket2, [0.9, 0.1]),
            (ticket3, [0.8, 0.2]),
        ]

        call_count = [0]

        def similarity_side_effect(v1, v2):
            call_count[0] += 1
            if v2 == [0.9, 0.1]:
                return 0.95
            elif v2 == [0.8, 0.2]:
                return 0.85
            return 1.0

        mock_similarity.side_effect = similarity_side_effect

        from app.logic.related_tickets import find_related_tickets

        result = find_related_tickets("T1", threshold=0.8)

        if len(result) >= 2:
            assert result[0][1] >= result[1][1]


class TestGetRelatedTicketsSummary:
    """Test get_related_tickets_summary function."""

    @patch('app.logic.related_tickets.find_related_tickets')
    def test_returns_message_when_no_related(self, mock_find):
        """Should return appropriate message when no related tickets."""
        mock_find.return_value = []

        from app.logic.related_tickets import get_related_tickets_summary

        result = get_related_tickets_summary("T1")

        assert "No closely related" in result

    @patch('app.logic.related_tickets.find_related_tickets')
    def test_formats_related_tickets(self, mock_find):
        """Should format related tickets as summary."""
        ticket = Ticket(id="T2", jira_key="PROJ-456", title="Related ticket")
        mock_find.return_value = [(ticket, 0.85)]

        from app.logic.related_tickets import get_related_tickets_summary

        result = get_related_tickets_summary("T1")

        assert "Related Tickets:" in result
        assert "PROJ-456" in result
        assert "Related ticket" in result
        assert "85%" in result
