#!/usr/bin/env python3
"""Wrapper script for generating embeddings."""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.db.model import SessionLocal, Ticket
from app.db.embedding import save_embedding
from app.logic.embedder import get_embedding


def embed_all_tickets():
    session = SessionLocal()
    tickets = session.query(Ticket).all()

    for ticket in tickets:
        print(f"Embedding {ticket.jira_key}...")
        text = f"{ticket.title or ''}\n\n{ticket.description or ''}"
        vector = get_embedding(text)
        save_embedding(ticket.id, vector)

    session.close()
    print("Embedding completed.")


if __name__ == "__main__":
    embed_all_tickets()
