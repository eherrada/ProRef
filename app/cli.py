"""ProRef CLI - Unified command-line interface for ProRef operations."""

import json
import subprocess
import sys
import typer
from typing import Optional
from openai import OpenAI

from app.config import load_config
from app.paths import QUESTIONS_DIR, TESTCASES_DIR, ensure_dirs
from app.db.model import SessionLocal, Ticket, GeneratedContent, init_db
from app.db.embedding import save_embedding
from app.logic.embedder import get_embedding
from app.logic.question_generator import generate_questions
from app.logic.test_case_generator import generate_test_cases
from app.logic.matching import match_text_to_ticket
from app.logic.related_tickets import get_related_tickets_summary
from app.jira.fetcher import fetch_backlog
from app.jira.publisher import post_comment_to_jira, format_questions_for_jira, format_test_cases_for_jira

app = typer.Typer(
    name="proref",
    help="ProRef - Product Refinement Automation Assistant",
    add_completion=False
)


@app.command()
def fetch():
    """Fetch tickets from Jira."""
    typer.echo("Fetching tickets from Jira...")
    count = fetch_backlog(verbose=True)
    typer.echo(f"\nDone! Fetched {count} tickets.")


@app.command()
def embed():
    """Generate embeddings for all tickets."""
    typer.echo("Generating embeddings for tickets...")

    session = SessionLocal()
    tickets = session.query(Ticket).all()

    for ticket in tickets:
        typer.echo(f"Embedding {ticket.jira_key}...")
        text = f"{ticket.title or ''}\n\n{ticket.description or ''}"
        vector = get_embedding(text)
        save_embedding(ticket.id, vector)

    session.close()
    typer.echo(f"\nDone! Embedded {len(tickets)} tickets.")


@app.command()
def questions(
    publish: bool = typer.Option(False, "--publish", "-p", help="Publish directly to Jira after generation")
):
    """Generate refinement questions for tickets."""
    ensure_dirs()

    session = SessionLocal()
    tickets = session.query(Ticket).filter(
        Ticket.issue_type != "Spike",
        Ticket.questions_generated != True
    ).all()

    if not tickets:
        typer.echo("No tickets pending question generation.")
        session.close()
        return

    typer.echo(f"Generating questions for {len(tickets)} tickets...")

    output_path = QUESTIONS_DIR / "questions_by_ticket.md"
    with open(output_path, "a", encoding="utf-8") as f:
        for idx, ticket in enumerate(tickets, 1):
            typer.echo(f"[{idx}/{len(tickets)}] Generating for {ticket.jira_key}...")

            # Show related tickets
            related_summary = get_related_tickets_summary(ticket.id, threshold=0.8)
            if "No closely related" not in related_summary:
                typer.echo(f"  {related_summary}")

            generated = generate_questions(ticket)

            if generated:
                # Save to database
                content = GeneratedContent(
                    ticket_id=ticket.id,
                    content_type='questions',
                    content=json.dumps(generated),
                    published=False
                )
                session.add(content)
                ticket.questions_generated = True
                session.add(ticket)

                # Write to file
                f.write(f"## {ticket.jira_key} - {ticket.title.strip() if ticket.title else ''}\n")
                f.write(f"**Type:** {ticket.issue_type}\n\n")
                f.write("**Generated questions:**\n")
                for q in generated:
                    f.write(f"- {q}\n")
                f.write("\n---\n\n")

                # Publish if requested
                if publish:
                    try:
                        adf_body = format_questions_for_jira(generated)
                        post_comment_to_jira(ticket.jira_key, "", adf_body=adf_body)
                        content.published = True
                        typer.echo(f"  Published to Jira!")
                    except Exception as e:
                        typer.echo(f"  Failed to publish: {e}")

    session.commit()
    session.close()
    typer.echo(f"\nDone! Questions saved to {output_path}")


@app.command()
def testcases(
    publish: bool = typer.Option(False, "--publish", "-p", help="Publish directly to Jira after generation")
):
    """Generate test cases for tickets."""
    ensure_dirs()

    session = SessionLocal()
    tickets = session.query(Ticket).filter(
        Ticket.test_cases_generated == False,
        Ticket.description != None,
        Ticket.title != None
    ).all()

    if not tickets:
        typer.echo("No tickets pending test case generation.")
        session.close()
        return

    typer.echo(f"Generating test cases for {len(tickets)} tickets...")

    output_path = TESTCASES_DIR / "test_cases_by_ticket.md"
    with open(output_path, "a", encoding="utf-8") as f:
        for idx, ticket in enumerate(tickets, 1):
            typer.echo(f"[{idx}/{len(tickets)}] Generating for {ticket.jira_key}...")

            generated = generate_test_cases(ticket)

            if generated:
                # Save to database
                content = GeneratedContent(
                    ticket_id=ticket.id,
                    content_type='test_cases',
                    content=json.dumps(generated),
                    published=False
                )
                session.add(content)
                ticket.test_cases_generated = True
                session.add(ticket)

                # Write to file
                f.write(f"## {ticket.jira_key} - {ticket.title.strip()}\n")
                f.write(f"**Type:** {ticket.issue_type}\n\n")

                # Write test cases in new format
                test_case_count = 0
                for tc in generated:
                    if isinstance(tc, dict):
                        test_case_count += 1
                        tc_id = tc.get("id", str(test_case_count))
                        title = tc.get("title", "")
                        pre = tc.get("pre", "")
                        steps = tc.get("steps", "")
                        expected = tc.get("expected", "")

                        f.write(f"### TC-{tc_id}: {title}\n\n")
                        if pre:
                            f.write(f"**PRE:** {pre}\n\n")
                        if steps:
                            f.write(f"**STEPS:**\n```\n{steps}\n```\n\n")
                        if expected:
                            f.write(f"**EXPECTED:**\n{expected}\n\n")
                        f.write("---\n\n")

                # Publish if requested
                if publish and test_case_count > 0:
                    try:
                        adf_body = format_test_cases_for_jira(generated)
                        post_comment_to_jira(ticket.jira_key, "", adf_body=adf_body)
                        content.published = True
                        typer.echo(f"  Published to Jira!")
                    except Exception as e:
                        typer.echo(f"  Failed to publish: {e}")

    session.commit()
    session.close()
    typer.echo(f"\nDone! Test cases saved to {output_path}")


@app.command()
def ui():
    """Launch the web UI (Streamlit)."""
    typer.echo("Launching ProRef Web UI...")
    typer.echo("Open http://localhost:8501 in your browser")
    typer.echo("Press Ctrl+C to stop the server\n")

    try:
        subprocess.run([
            sys.executable, "-m", "streamlit", "run",
            "app/ui.py",
            "--server.headless=true"
        ])
    except KeyboardInterrupt:
        typer.echo("\nUI stopped.")


@app.command()
def chat():
    """Start interactive chat about tickets."""
    config = load_config()
    api_key = config["openai"]["api_key"]
    model = config["openai"]["model_chat"]

    if not api_key:
        typer.echo("Error: No OpenAI API key configured. Run 'proref ui' and go to Settings.")
        raise typer.Exit(1)

    client = OpenAI(api_key=api_key)

    typer.echo("\nIntelligent Ticket Assistant")
    typer.echo("=" * 50)
    typer.echo("Ask questions about project tickets.")
    typer.echo("Type 'exit' or 'quit' to end the session.")
    typer.echo("=" * 50)

    while True:
        try:
            question = typer.prompt("\nYour question")
            if question.lower() in ['exit', 'quit', 'q']:
                break

            # Find relevant tickets
            matches = match_text_to_ticket(question, top_k=5)

            if not matches:
                typer.echo("\nNo relevant information found for your question.")
                continue

            # Build context
            context_parts = []
            for ticket, score in matches:
                context_parts.append(f"""
Ticket: {ticket.jira_key}
Title: {ticket.title}
Type: {ticket.issue_type}
Status: {ticket.status}
Description: {ticket.description}
Relevance: {score:.2%}
""")

            context = "\n".join(context_parts)

            prompt = f"""You are an expert assistant for the project. Your task is to answer questions based on Jira ticket information.

Context (relevant tickets):
{context}

Question: {question}

Instructions:
1. Analyze the ticket information
2. Provide a clear and concise response
3. If information is insufficient, indicate it
4. Include references to relevant tickets (using their ticket keys)
5. If there are contradictions or ambiguities, mention them
6. IMPORTANT: Respond in the SAME LANGUAGE as the question.

Response:"""

            typer.echo("\nAnalyzing...")
            response = client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
            )

            typer.echo(f"\nResponse:\n{response.choices[0].message.content}")

            typer.echo("\nReferences:")
            for ticket, score in matches:
                typer.echo(f"- {ticket.jira_key}: {ticket.title} ({score:.0%})")
            typer.echo("=" * 50)

        except KeyboardInterrupt:
            typer.echo("\n\nGoodbye!")
            break
        except Exception as e:
            typer.echo(f"\nError: {e}")


@app.command()
def status():
    """Show status of processed tickets."""
    session = SessionLocal()

    total = session.query(Ticket).count()
    with_questions = session.query(Ticket).filter(Ticket.questions_generated == True).count()
    with_tests = session.query(Ticket).filter(Ticket.test_cases_generated == True).count()

    # Count published content
    published_questions = session.query(GeneratedContent).filter(
        GeneratedContent.content_type == 'questions',
        GeneratedContent.published == True
    ).count()
    published_tests = session.query(GeneratedContent).filter(
        GeneratedContent.content_type == 'test_cases',
        GeneratedContent.published == True
    ).count()

    # Pending publication
    pending_questions = session.query(GeneratedContent).filter(
        GeneratedContent.content_type == 'questions',
        GeneratedContent.published == False
    ).count()
    pending_tests = session.query(GeneratedContent).filter(
        GeneratedContent.content_type == 'test_cases',
        GeneratedContent.published == False
    ).count()

    session.close()

    typer.echo("\nProRef Status")
    typer.echo("=" * 40)
    typer.echo(f"\nTickets:")
    typer.echo(f"  Total:                 {total}")
    typer.echo(f"  With questions:        {with_questions}")
    typer.echo(f"  With test cases:       {with_tests}")
    typer.echo(f"\nPublication:")
    typer.echo(f"  Questions published:   {published_questions}")
    typer.echo(f"  Test cases published:  {published_tests}")
    typer.echo(f"  Questions pending:     {pending_questions}")
    typer.echo(f"  Test cases pending:    {pending_tests}")
    typer.echo("")


@app.command()
def publish():
    """Interactively publish pending content to Jira."""
    session = SessionLocal()

    # Get unpublished content
    pending = session.query(GeneratedContent).filter(
        GeneratedContent.published == False
    ).all()

    if not pending:
        typer.echo("No pending content to publish.")
        session.close()
        return

    typer.echo(f"\nFound {len(pending)} items pending publication.\n")

    for item in pending:
        ticket = session.query(Ticket).filter_by(id=item.ticket_id).first()
        if not ticket:
            continue

        content_data = json.loads(item.content)
        content_type_label = "Questions" if item.content_type == 'questions' else "Test Cases"

        typer.echo("=" * 60)
        typer.echo(f"Ticket: {ticket.jira_key} - {ticket.title}")
        typer.echo(f"Type: {content_type_label}")
        typer.echo("-" * 60)

        # Show preview
        if item.content_type == 'questions':
            for q in content_data:
                typer.echo(f"  - {q}")
        else:
            for line in content_data[:10]:  # Show first 10 lines
                typer.echo(f"  {line}")
            if len(content_data) > 10:
                typer.echo(f"  ... and {len(content_data) - 10} more lines")

        typer.echo("-" * 60)

        # Ask for action
        action = typer.prompt(
            "\n[P]ublish / [S]kip / [C]ancel all",
            default="S"
        ).upper()

        if action == 'C':
            typer.echo("Cancelled.")
            break
        elif action == 'P':
            try:
                if item.content_type == 'questions':
                    adf_body = format_questions_for_jira(content_data)
                else:
                    adf_body = format_test_cases_for_jira(content_data)

                post_comment_to_jira(ticket.jira_key, "", adf_body=adf_body)
                item.published = True
                session.add(item)
                session.commit()
                typer.echo(f"Published to {ticket.jira_key}!")
            except Exception as e:
                typer.echo(f"Failed to publish: {e}")
        else:
            typer.echo("Skipped.")

        typer.echo("")

    session.close()
    typer.echo("\nDone!")


def main():
    """Entry point for the CLI."""
    init_db()
    app()


if __name__ == "__main__":
    main()
