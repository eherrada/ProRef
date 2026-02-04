#!/usr/bin/env python3
"""Wrapper script for generating questions."""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.paths import QUESTIONS_DIR, ensure_dirs
from app.db.model import SessionLocal, Ticket
from app.logic.question_generator import generate_questions

ensure_dirs()

session = SessionLocal()
tickets = session.query(Ticket).filter(
    Ticket.issue_type != "Spike",
    Ticket.questions_generated != True
).all()

output_path = QUESTIONS_DIR / "questions_by_ticket.md"

with open(output_path, "a", encoding="utf-8") as f:
    for idx, ticket in enumerate(tickets, 1):
        print(f"Generating questions for {ticket.jira_key} ({idx}/{len(tickets)})")
        questions = generate_questions(ticket)

        f.write(f"## {ticket.jira_key} - {ticket.title.strip() if ticket.title else ''}\n")
        f.write(f"**Type:** {ticket.issue_type}\n\n")

        if questions:
            f.write("**Generated questions:**\n")
            for q in questions:
                f.write(f"- {q}\n")
            ticket.questions_generated = True
            session.add(ticket)
        else:
            f.write("_No questions generated._\n")

        f.write("\n---\n\n")

session.commit()
session.close()
print(f"Questions saved to: {output_path}")
