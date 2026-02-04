"""Tests for app/db/model.py"""

import pytest
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.model import Base, Ticket, TicketEmbedding, GeneratedContent


class TestTicketModel:
    """Test Ticket model."""

    def test_create_ticket(self, temp_db):
        """Should create a ticket with all fields."""
        ticket = Ticket(
            id="TEST-001",
            jira_key="TEST-001",
            title="Test Title",
            description="Test Description",
            status="To Do",
            issue_type="story",
            updated_at=datetime.now(),
            fetched_at=datetime.now(),
            questions_generated=False,
            test_cases_generated=False,
            posted_to_jira=False
        )
        temp_db.add(ticket)
        temp_db.commit()

        saved = temp_db.query(Ticket).filter_by(id="TEST-001").first()
        assert saved is not None
        assert saved.jira_key == "TEST-001"
        assert saved.title == "Test Title"
        assert saved.questions_generated is False

    def test_ticket_unique_jira_key(self, temp_db):
        """jira_key should be unique."""
        ticket1 = Ticket(id="T1", jira_key="SAME-KEY", title="First")
        ticket2 = Ticket(id="T2", jira_key="SAME-KEY", title="Second")

        temp_db.add(ticket1)
        temp_db.commit()

        temp_db.add(ticket2)
        with pytest.raises(Exception):  # IntegrityError
            temp_db.commit()

    def test_ticket_defaults(self, temp_db):
        """Default values should be applied."""
        ticket = Ticket(
            id="TEST-002",
            jira_key="TEST-002",
            title="Minimal ticket"
        )
        temp_db.add(ticket)
        temp_db.commit()

        saved = temp_db.query(Ticket).filter_by(id="TEST-002").first()
        assert saved.questions_generated is False
        assert saved.test_cases_generated is False
        assert saved.posted_to_jira is False


class TestTicketEmbeddingModel:
    """Test TicketEmbedding model."""

    def test_create_embedding(self, temp_db, sample_ticket):
        """Should create embedding linked to ticket."""
        temp_db.add(sample_ticket)
        temp_db.commit()

        embedding = TicketEmbedding(
            ticket_id=sample_ticket.id,
            embedding=b"fake_embedding_data"
        )
        temp_db.add(embedding)
        temp_db.commit()

        saved = temp_db.query(TicketEmbedding).filter_by(ticket_id=sample_ticket.id).first()
        assert saved is not None
        assert saved.embedding == b"fake_embedding_data"

    def test_embedding_relationship(self, temp_db, sample_ticket):
        """Embedding should have relationship to ticket."""
        temp_db.add(sample_ticket)
        temp_db.commit()

        embedding = TicketEmbedding(
            ticket_id=sample_ticket.id,
            embedding=b"data"
        )
        temp_db.add(embedding)
        temp_db.commit()

        saved = temp_db.query(TicketEmbedding).filter_by(ticket_id=sample_ticket.id).first()
        assert saved.ticket.jira_key == sample_ticket.jira_key


class TestGeneratedContentModel:
    """Test GeneratedContent model."""

    def test_create_generated_content(self, temp_db, sample_ticket):
        """Should create generated content linked to ticket."""
        temp_db.add(sample_ticket)
        temp_db.commit()

        content = GeneratedContent(
            ticket_id=sample_ticket.id,
            content_type='questions',
            content='["Question 1?", "Question 2?"]',
            published=False
        )
        temp_db.add(content)
        temp_db.commit()

        saved = temp_db.query(GeneratedContent).filter_by(ticket_id=sample_ticket.id).first()
        assert saved is not None
        assert saved.content_type == 'questions'
        assert saved.published is False

    def test_content_types(self, temp_db, sample_ticket):
        """Should support both questions and test_cases types."""
        temp_db.add(sample_ticket)
        temp_db.commit()

        questions = GeneratedContent(
            ticket_id=sample_ticket.id,
            content_type='questions',
            content='[]'
        )
        test_cases = GeneratedContent(
            ticket_id=sample_ticket.id,
            content_type='test_cases',
            content='[]'
        )
        temp_db.add_all([questions, test_cases])
        temp_db.commit()

        all_content = temp_db.query(GeneratedContent).filter_by(ticket_id=sample_ticket.id).all()
        types = {c.content_type for c in all_content}
        assert types == {'questions', 'test_cases'}

    def test_created_at_default(self, temp_db, sample_ticket):
        """created_at should default to current time."""
        temp_db.add(sample_ticket)
        temp_db.commit()

        content = GeneratedContent(
            ticket_id=sample_ticket.id,
            content_type='questions',
            content='[]'
        )
        temp_db.add(content)
        temp_db.commit()

        saved = temp_db.query(GeneratedContent).first()
        assert saved.created_at is not None

    def test_relationship_to_ticket(self, temp_db, sample_ticket):
        """Generated content should link back to ticket."""
        temp_db.add(sample_ticket)
        temp_db.commit()

        content = GeneratedContent(
            ticket_id=sample_ticket.id,
            content_type='questions',
            content='[]'
        )
        temp_db.add(content)
        temp_db.commit()

        saved = temp_db.query(GeneratedContent).first()
        assert saved.ticket.jira_key == sample_ticket.jira_key
