#!/usr/bin/env python3
"""Wrapper script for interactive chat."""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from openai import OpenAI

from app.config import OPENAI_API_KEY, MODEL_CHAT
from app.logic.matching import match_text_to_ticket

client = OpenAI(api_key=OPENAI_API_KEY)


def format_ticket_for_context(ticket, score=None):
    """Format a ticket for use as context in the prompt."""
    relevance = f"{score:.2%}" if score is not None else "N/A"
    return f"""
Ticket: {ticket.jira_key}
Title: {ticket.title}
Type: {ticket.issue_type}
Status: {ticket.status}
Description: {ticket.description}
Relevance: {relevance}
"""


def generate_response(question: str, relevant_tickets: list) -> str:
    """Generate a coherent response using GPT."""
    context = "\n".join(format_ticket_for_context(ticket, score) for ticket, score in relevant_tickets)

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

    response = client.chat.completions.create(
        model=MODEL_CHAT,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,
    )
    return response.choices[0].message.content


def chat():
    print("\nIntelligent Ticket Assistant")
    print("=" * 50)
    print("Ask questions about project tickets.")
    print("Type 'exit' to quit.")
    print("=" * 50)

    while True:
        try:
            question = input("\nYour question (or 'exit'): ").strip()
            if question.lower() in ['exit', 'quit', 'q']:
                break

            matches = match_text_to_ticket(question, top_k=5)

            if not matches:
                print("\nNo relevant information found.")
                continue

            print("\nAnalyzing...")
            response = generate_response(question, matches)
            print(f"\nResponse:\n{response}")

            print("\nReferences:")
            for ticket, score in matches:
                print(f"- {ticket.jira_key}: {ticket.title} ({score:.0%})")
            print("=" * 50)

        except KeyboardInterrupt:
            print("\n\nGoodbye!")
            break
        except Exception as e:
            print(f"\nError: {e}")


if __name__ == "__main__":
    chat()
