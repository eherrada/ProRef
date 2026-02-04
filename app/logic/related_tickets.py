"""Find related tickets using embedding similarity."""

from typing import List, Tuple

from app.db.model import SessionLocal, Ticket
from app.db.embedding import get_all_embeddings
from app.logic.embedder import cosine_similarity


def find_related_tickets(
    ticket_id: str,
    threshold: float = 0.8,
    top_k: int = 5
) -> List[Tuple[Ticket, float]]:
    """
    Find tickets similar to the given ticket using embeddings.

    Args:
        ticket_id: The ID of the ticket to find related tickets for
        threshold: Minimum similarity score (0-1) to include a ticket
        top_k: Maximum number of related tickets to return

    Returns:
        List of (Ticket, similarity_score) tuples, sorted by similarity
    """
    all_embeddings = get_all_embeddings()

    # Find the embedding for the target ticket
    target_vector = None
    for ticket, vector in all_embeddings:
        if ticket.id == ticket_id:
            target_vector = vector
            break

    if target_vector is None:
        return []

    # Calculate similarity with all other tickets
    related = []
    for ticket, vector in all_embeddings:
        if ticket.id == ticket_id:
            continue  # Skip self

        score = cosine_similarity(target_vector, vector)
        if score >= threshold:
            related.append((ticket, score))

    # Sort by similarity (highest first) and limit
    related.sort(key=lambda x: x[1], reverse=True)
    return related[:top_k]


def get_related_tickets_summary(ticket_id: str, threshold: float = 0.8) -> str:
    """
    Get a formatted summary of related tickets.

    Args:
        ticket_id: The ID of the ticket to find related tickets for
        threshold: Minimum similarity score to include

    Returns:
        Formatted string with related ticket information
    """
    related = find_related_tickets(ticket_id, threshold=threshold)

    if not related:
        return "No closely related tickets found."

    lines = ["Related Tickets:"]
    for ticket, score in related:
        lines.append(f"  - {ticket.jira_key}: {ticket.title} ({score:.0%} similar)")

    return "\n".join(lines)
