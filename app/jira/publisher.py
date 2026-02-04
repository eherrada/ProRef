"""Jira comment publisher module."""

import logging
import requests
from typing import Optional

from app.config import JIRA_BASE_URL, JIRA_USER, JIRA_API_TOKEN, validate_jira_config
from app.utils.retry import retry

logger = logging.getLogger(__name__)


def _text_to_adf_content(text: str) -> list:
    """Convert text with newlines to ADF content with hardBreaks."""
    content = []
    lines = text.split('\n')

    for i, line in enumerate(lines):
        if line:  # Non-empty line
            content.append({"type": "text", "text": line})
        if i < len(lines) - 1:  # Add hardBreak except after last line
            content.append({"type": "hardBreak"})

    return content if content else [{"type": "text", "text": " "}]


def _build_adf_document(sections: list[dict]) -> dict:
    """Build an ADF document from sections.

    Each section dict should have:
    - type: 'heading', 'paragraph', 'codeBlock', 'rule'
    - text: the content (for heading/paragraph)
    - level: heading level (for heading, optional)
    """
    content = []

    for section in sections:
        sec_type = section.get("type", "paragraph")
        text = section.get("text", "")

        if sec_type == "heading":
            level = section.get("level", 3)
            content.append({
                "type": "heading",
                "attrs": {"level": level},
                "content": [{"type": "text", "text": text}]
            })

        elif sec_type == "paragraph":
            if text:
                content.append({
                    "type": "paragraph",
                    "content": _text_to_adf_content(text)
                })

        elif sec_type == "codeBlock":
            content.append({
                "type": "codeBlock",
                "attrs": {"language": "text"},
                "content": [{"type": "text", "text": text}]
            })

        elif sec_type == "rule":
            content.append({"type": "rule"})

        elif sec_type == "bulletList":
            items = section.get("items", [])
            list_content = []
            for item in items:
                list_content.append({
                    "type": "listItem",
                    "content": [{
                        "type": "paragraph",
                        "content": [{"type": "text", "text": item}]
                    }]
                })
            if list_content:
                content.append({
                    "type": "bulletList",
                    "content": list_content
                })

    return {
        "type": "doc",
        "version": 1,
        "content": content
    }


@retry(max_attempts=3, delay=2.0, exceptions=(requests.RequestException,))
def post_comment_to_jira(ticket_key: str, comment: str, adf_body: dict = None) -> bool:
    """
    Post a comment to a Jira ticket.

    Args:
        ticket_key: The Jira ticket key (e.g., 'PROJ-123')
        comment: The comment text to post (used if adf_body is None)
        adf_body: Optional pre-built ADF document

    Returns:
        True if successful, False otherwise
    """
    validate_jira_config()

    url = f"{JIRA_BASE_URL}/rest/api/3/issue/{ticket_key}/comment"
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json"
    }
    auth = (JIRA_USER, JIRA_API_TOKEN)

    if adf_body:
        payload = {"body": adf_body}
    else:
        # Simple text - convert to ADF with proper line breaks
        payload = {
            "body": _build_adf_document([{"type": "paragraph", "text": comment}])
        }

    response = requests.post(url, headers=headers, json=payload, auth=auth)
    response.raise_for_status()

    logger.info(f"Comment posted to {ticket_key}")
    return True


def format_questions_for_jira(questions: list) -> dict:
    """Format questions list as ADF document for Jira comment."""
    sections = [
        {"type": "heading", "level": 3, "text": "Generated Refinement Questions"},
        {"type": "bulletList", "items": questions}
    ]
    return _build_adf_document(sections)


def format_test_cases_for_jira(test_cases: list) -> dict:
    """Format test cases as ADF document for Jira comment.

    Handles both new format (list of dicts) and old format (list of strings).
    """
    sections = [
        {"type": "heading", "level": 3, "text": "Generated Test Cases"}
    ]

    for i, tc in enumerate(test_cases):
        if i > 0:
            sections.append({"type": "rule"})

        if isinstance(tc, dict):
            # New format with id, title, pre, steps, expected
            tc_id = tc.get("id", "?")
            title = tc.get("title", "")
            pre = tc.get("pre", "")
            steps = tc.get("steps", tc.get("pasos", ""))
            expected = tc.get("expected", tc.get("esperado", ""))

            # Title as subheading
            sections.append({"type": "heading", "level": 4, "text": f"TC-{tc_id}: {title}"})

            # PRE
            if pre:
                sections.append({"type": "paragraph", "text": f"PRE: {pre}"})

            # STEPS in code block to preserve formatting
            if steps:
                sections.append({"type": "paragraph", "text": "STEPS:"})
                sections.append({"type": "codeBlock", "text": steps})

            # EXPECTED
            if expected:
                sections.append({"type": "paragraph", "text": "EXPECTED:"})
                # Parse expected items if they're bullet points
                expected_lines = [line.lstrip('- ').strip() for line in expected.split('\n') if line.strip()]
                if expected_lines:
                    sections.append({"type": "bulletList", "items": expected_lines})

        else:
            # Old format - just a string
            sections.append({"type": "paragraph", "text": str(tc)})

    return _build_adf_document(sections)
