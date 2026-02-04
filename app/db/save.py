import hashlib
import json
from datetime import datetime
from app.db.model import Ticket, SessionLocal


def _compute_content_hash(title: str, description: str) -> str:
    """Compute hash of ticket content for change detection."""
    content = f"{title or ''}|{description or ''}"
    return hashlib.md5(content.encode()).hexdigest()


def save_or_update_ticket(ticket_data):
    """Save or update a ticket from Jira data."""
    session = SessionLocal()
    existing = session.query(Ticket).filter_by(jira_key=ticket_data['jira_key']).first()

    # Compute hash for change detection
    new_hash = _compute_content_hash(
        ticket_data.get('title', ''),
        ticket_data.get('description', '')
    )

    if existing:
        incoming_updated = ticket_data.get('updated_at')
        local_updated = existing.updated_at

        # Check if content changed
        old_hash = existing.content_hash
        content_changed = old_hash is not None and old_hash != new_hash

        # Remove tzinfo for clean comparison (both without timezone)
        should_update = False
        if incoming_updated and local_updated:
            if incoming_updated.replace(tzinfo=None) > local_updated.replace(tzinfo=None):
                should_update = True
        else:
            should_update = True

        if should_update:
            for k, v in ticket_data.items():
                setattr(existing, k, v)
            existing.fetched_at = datetime.utcnow()
            existing.content_hash = new_hash

            if content_changed:
                existing.content_changed = True
                # Don't reset questions_generated, just mark as changed
            else:
                existing.questions_generated = False
    else:
        ticket = Ticket(
            **ticket_data,
            fetched_at=datetime.utcnow(),
            questions_generated=False,
            content_hash=new_hash,
            content_changed=False
        )
        session.add(ticket)

    session.commit()
    session.close()


def save_quality_score(ticket_id: str, score_data: dict):
    """Save quality score for a ticket."""
    session = SessionLocal()
    try:
        ticket = session.query(Ticket).filter_by(id=ticket_id).first()
        if ticket:
            ticket.quality_score = score_data.get('score')
            ticket.quality_summary = score_data.get('summary', '')
            ticket.quality_issues = json.dumps(score_data.get('issues', []))
            ticket.quality_suggestions = json.dumps(score_data.get('suggestions', []))
            ticket.quality_scored_at = datetime.utcnow()
            session.commit()
    finally:
        session.close()


def mark_content_reviewed(ticket_id: str):
    """Mark that content change has been reviewed."""
    session = SessionLocal()
    try:
        ticket = session.query(Ticket).filter_by(id=ticket_id).first()
        if ticket:
            ticket.content_changed = False
            session.commit()
    finally:
        session.close()


def reset_ticket_for_regeneration(ticket_id: str, reset_questions: bool = True, reset_tests: bool = True):
    """Reset a ticket's generation flags for regeneration."""
    session = SessionLocal()
    try:
        ticket = session.query(Ticket).filter_by(id=ticket_id).first()
        if ticket:
            if reset_questions:
                ticket.questions_generated = False
            if reset_tests:
                ticket.test_cases_generated = False
            ticket.content_changed = False
            session.commit()
    finally:
        session.close()
