#!/usr/bin/env python3
"""Wrapper script for generating test cases."""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.paths import TESTCASES_DIR, ensure_dirs
from app.db.model import SessionLocal, Ticket
from app.logic.test_case_generator import generate_test_cases

ensure_dirs()

session = SessionLocal()
tickets = session.query(Ticket).filter(
    Ticket.test_cases_generated == False,
    Ticket.description != None,
    Ticket.title != None
).all()
session.close()

output_path = TESTCASES_DIR / "test_cases_by_ticket.md"

with open(output_path, "a", encoding="utf-8") as f:
    for idx, ticket in enumerate(tickets, 1):
        print(f"Generating test cases for {ticket.jira_key} ({idx}/{len(tickets)})")
        test_cases = generate_test_cases(ticket)

        f.write(f"## {ticket.jira_key} - {ticket.title.strip()}\n")
        f.write(f"**Type:** {ticket.issue_type}\n\n")

        if test_cases:
            current_block = []
            test_case_count = 0

            for line in test_cases:
                line = line.strip()
                if not line:
                    continue

                current_block.append(line)

                if len(current_block) == 3:
                    scenario = action = expected = "(not detected)"

                    for item in current_block:
                        lower = item.lower().replace("**", "").replace("-", "").strip()
                        if lower.startswith("scenario"):
                            scenario = item.split(":", 1)[-1].strip()
                        elif lower.startswith("action"):
                            action = item.split(":", 1)[-1].strip()
                        elif "expected behavior" in lower:
                            expected = item.split(":", 1)[-1].strip()

                    test_case_count += 1
                    f.write(f"### Test Case {test_case_count}\n")
                    f.write(f"- **Scenario:** _{scenario}_\n")
                    f.write(f"- **Action:** _{action}_\n")
                    f.write(f"- **Expected behavior:** _{expected}_\n")
                    f.write("\n---\n\n")

                    current_block = []

            if test_case_count > 0:
                session = SessionLocal()
                db_ticket = session.query(Ticket).filter_by(jira_key=ticket.jira_key).first()
                db_ticket.test_cases_generated = True
                session.commit()
                session.close()
            else:
                f.write("_No valid test cases detected._\n\n---\n\n")

        else:
            f.write("_No test cases generated._\n\n---\n\n")

print(f"Test cases saved to: {output_path}")
