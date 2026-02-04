"""Pytest fixtures and configuration."""

import json
import os
import tempfile
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.model import Base, Ticket, TicketEmbedding, GeneratedContent


@pytest.fixture
def temp_db():
    """Create a temporary in-memory database for testing."""
    engine = create_engine('sqlite:///:memory:', echo=False)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


@pytest.fixture
def sample_ticket():
    """Create a sample ticket for testing."""
    return Ticket(
        id="TEST-123",
        jira_key="TEST-123",
        title="Test ticket title",
        description="This is a test ticket description with enough content for testing.",
        status="To Do",
        issue_type="story",
        updated_at=datetime(2024, 1, 15, 10, 30, 0),
        fetched_at=datetime(2024, 1, 15, 12, 0, 0),
        questions_generated=False,
        test_cases_generated=False,
        posted_to_jira=False
    )


@pytest.fixture
def sample_ticket_2():
    """Create a second sample ticket for testing."""
    return Ticket(
        id="TEST-456",
        jira_key="TEST-456",
        title="Another test ticket",
        description="Different description for similarity testing purposes.",
        status="In Progress",
        issue_type="bug",
        updated_at=datetime(2024, 1, 16, 10, 30, 0),
        fetched_at=datetime(2024, 1, 16, 12, 0, 0),
        questions_generated=True,
        test_cases_generated=False,
        posted_to_jira=False
    )


@pytest.fixture
def db_with_tickets(temp_db, sample_ticket, sample_ticket_2):
    """Database with sample tickets."""
    temp_db.add(sample_ticket)
    temp_db.add(sample_ticket_2)
    temp_db.commit()
    return temp_db


@pytest.fixture
def mock_embedding():
    """Create a mock embedding vector."""
    return [0.1] * 1536


@pytest.fixture
def mock_openai_embedding(mock_embedding):
    """Mock OpenAI embedding response."""
    mock_response = MagicMock()
    mock_response.data = [MagicMock(embedding=mock_embedding)]
    return mock_response


@pytest.fixture
def mock_openai_chat():
    """Mock OpenAI chat response."""
    mock_response = MagicMock()
    mock_response.choices = [
        MagicMock(message=MagicMock(content="- Question 1?\n- Question 2?\n- Question 3?"))
    ]
    return mock_response


@pytest.fixture
def mock_jira_response():
    """Mock Jira API response."""
    return {
        "issues": [
            {
                "key": "PROJ-101",
                "fields": {
                    "summary": "Test issue from Jira",
                    "description": "Description of the test issue",
                    "status": {"name": "To Do"},
                    "issuetype": {"name": "Story"},
                    "updated": "2024-01-15T10:30:00.000+0000"
                }
            },
            {
                "key": "PROJ-102",
                "fields": {
                    "summary": "Another issue",
                    "description": {"type": "doc", "content": []},
                    "status": {"name": "Done"},
                    "issuetype": {"name": "Bug"},
                    "updated": "2024-01-16T14:00:00.000+0000"
                }
            }
        ]
    }


@pytest.fixture
def temp_data_dir(tmp_path):
    """Create temporary data directories."""
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    (data_dir / "questions").mkdir()
    (data_dir / "test_cases").mkdir()
    (data_dir / "docs").mkdir()
    return data_dir
