"""Ticket quality scoring module."""

import logging
import re
from openai import OpenAI
from app.db.model import Ticket
from app.config import load_config

logger = logging.getLogger(__name__)


def score_ticket_quality(ticket: Ticket) -> dict:
    """
    Score a ticket's quality using AI analysis.

    Returns:
        dict with:
            - score: int (1-10)
            - summary: str (brief explanation)
            - issues: list[str] (specific problems found)
            - suggestions: list[str] (improvements)
    """
    if not ticket.description and not ticket.title:
        return {
            "score": 1,
            "summary": "Ticket has no content",
            "issues": ["No title", "No description"],
            "suggestions": ["Add a descriptive title", "Add detailed description"]
        }

    config = load_config()
    provider = config.get("ai_provider", "openai")

    prompt = f"""Analyze this Jira ticket and score its quality from 1-10.

TICKET:
Title: {ticket.title or 'No title'}
Type: {ticket.issue_type or 'Unknown'}
Description:
{ticket.description or 'No description'}

SCORING CRITERIA:
- Clear title that describes the work (0-2 points)
- Detailed description explaining the context (0-2 points)
- Acceptance criteria or definition of done (0-2 points)
- Edge cases or error scenarios mentioned (0-2 points)
- Technical details or dependencies noted (0-2 points)

RESPOND IN THIS EXACT FORMAT:
SCORE: [number 1-10]
SUMMARY: [one sentence summary of quality]
ISSUES:
- [issue 1]
- [issue 2]
SUGGESTIONS:
- [suggestion 1]
- [suggestion 2]

Be concise. Max 3 issues and 3 suggestions."""

    try:
        if provider == "openai":
            api_key = config["openai"].get("api_key")
            model = config["openai"].get("model_questions", "gpt-3.5-turbo")
            client = OpenAI(api_key=api_key)
            response = client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=500
            )
            content = response.choices[0].message.content

        elif provider == "anthropic":
            import anthropic
            api_key = config["anthropic"].get("api_key")
            model = config["anthropic"].get("model_questions", "claude-3-5-sonnet-20241022")
            client = anthropic.Anthropic(api_key=api_key)
            response = client.messages.create(
                model=model,
                max_tokens=500,
                messages=[{"role": "user", "content": prompt}]
            )
            content = response.content[0].text

        elif provider == "google":
            import google.generativeai as genai
            api_key = config["google"].get("api_key")
            model = config["google"].get("model_questions", "gemini-1.5-flash")
            genai.configure(api_key=api_key)
            gen_model = genai.GenerativeModel(model)
            response = gen_model.generate_content(prompt)
            content = response.text
        else:
            return _fallback_score(ticket)

        return _parse_score_response(content)

    except Exception as e:
        logger.error(f"Error scoring ticket {ticket.jira_key}: {e}")
        return _fallback_score(ticket)


def _parse_score_response(content: str) -> dict:
    """Parse the AI response into structured data."""
    result = {
        "score": 5,
        "summary": "Unable to parse response",
        "issues": [],
        "suggestions": []
    }

    lines = content.strip().split('\n')
    current_section = None

    for line in lines:
        line = line.strip()
        if not line:
            continue

        if line.startswith("SCORE:"):
            try:
                score_str = line.replace("SCORE:", "").strip()
                # Handle formats like "7/10" or just "7"
                score_str = score_str.split("/")[0].strip()
                result["score"] = max(1, min(10, int(score_str)))
            except:
                pass

        elif line.startswith("SUMMARY:"):
            result["summary"] = line.replace("SUMMARY:", "").strip()

        elif line.startswith("ISSUES:"):
            current_section = "issues"

        elif line.startswith("SUGGESTIONS:"):
            current_section = "suggestions"

        elif line.startswith("- ") or line.startswith("* "):
            item = line.lstrip("-* ").strip()
            if current_section == "issues" and len(result["issues"]) < 5:
                result["issues"].append(item)
            elif current_section == "suggestions" and len(result["suggestions"]) < 5:
                result["suggestions"].append(item)

    return result


def _fallback_score(ticket: Ticket) -> dict:
    """Calculate a basic score without AI based on heuristics."""
    score = 5
    issues = []
    suggestions = []

    # Check title
    if not ticket.title:
        score -= 2
        issues.append("Missing title")
        suggestions.append("Add a descriptive title")
    elif len(ticket.title) < 10:
        score -= 1
        issues.append("Title is too short")
        suggestions.append("Make title more descriptive")

    # Check description
    desc = ticket.description or ""
    if not desc:
        score -= 3
        issues.append("No description")
        suggestions.append("Add a detailed description")
    elif len(desc) < 50:
        score -= 2
        issues.append("Description is very brief")
        suggestions.append("Expand the description with more details")
    elif len(desc) < 150:
        score -= 1
        issues.append("Description could be more detailed")

    # Check for acceptance criteria indicators
    ac_patterns = [
        r'acceptance criteria',
        r'AC:',
        r'definition of done',
        r'DoD:',
        r'expected behavior',
        r'should be able to',
        r'given.*when.*then',
        r'\[\s*\]',  # Checkboxes
    ]
    has_ac = any(re.search(p, desc, re.IGNORECASE) for p in ac_patterns)
    if not has_ac:
        score -= 1
        issues.append("No clear acceptance criteria")
        suggestions.append("Add acceptance criteria or definition of done")

    # Check for edge cases
    edge_patterns = [
        r'edge case',
        r'error',
        r'fail',
        r'invalid',
        r'empty',
        r'null',
        r'boundary',
        r'limit',
    ]
    has_edges = any(re.search(p, desc, re.IGNORECASE) for p in edge_patterns)
    if not has_edges and len(desc) > 100:
        issues.append("No edge cases mentioned")
        suggestions.append("Consider documenting error scenarios")

    score = max(1, min(10, score))

    summary = _generate_summary(score)

    return {
        "score": score,
        "summary": summary,
        "issues": issues[:3],
        "suggestions": suggestions[:3]
    }


def _generate_summary(score: int) -> str:
    """Generate a summary based on score."""
    if score >= 8:
        return "Well-defined ticket with clear requirements"
    elif score >= 6:
        return "Adequate ticket, minor improvements possible"
    elif score >= 4:
        return "Ticket needs more detail before implementation"
    else:
        return "Ticket requires significant refinement"


def get_score_color(score: int) -> str:
    """Get color class for score display."""
    if score >= 8:
        return "success"
    elif score >= 5:
        return "warning"
    else:
        return "error"


def get_score_label(score: int) -> str:
    """Get label for score."""
    if score >= 8:
        return "Ready"
    elif score >= 5:
        return "Needs Work"
    else:
        return "Not Ready"
