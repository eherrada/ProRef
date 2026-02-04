import logging
import json
import re
from openai import OpenAI
from app.db.model import Ticket
from app.config import load_config

logger = logging.getLogger(__name__)


def generate_test_cases(ticket: Ticket) -> list[dict]:
    """Generate test cases in structured format.

    Returns list of dicts with keys: id, title, pre, pasos, esperado
    """
    if not ticket.description or not ticket.title:
        return []

    config = load_config()
    provider = config.get("ai_provider", "openai")

    prompt = f"""You are a senior QA analyst for a healthcare platform.
Generate up to 5 functional test cases for the following ticket.

RULES:
- Include happy path and at least one negative/edge case
- Avoid redundancy; fewer than 5 is OK
- Be specific with test data examples
- Output ONLY test cases in the EXACT format below, no extra text

FORMAT (use this EXACTLY for each test case):
TC-1: [Short descriptive title]

PRE: [Required preconditions, e.g.: User logged in as Admin]

STEPS:
1. [First step]
2. [Second step]
3. [Third step with sub-items if needed]
   - [Sub-item 1]
   - [Sub-item 2]
4. [Final step]

EXPECTED:
- [Expected result 1]
- [Expected result 2]
- [Expected message or validation]

---

(Repeat for each test case, incrementing TC-2, TC-3, etc.)

---
TICKET INFO:
Title: {ticket.title.strip()}
Description: {ticket.description.strip()}
Issue type: {ticket.issue_type}
---
"""

    try:
        if provider == "openai":
            api_key = config["openai"].get("api_key")
            model = config["openai"].get("model_testcases", "gpt-3.5-turbo")
            client = OpenAI(api_key=api_key)
            response = client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,
            )
            content = response.choices[0].message.content

        elif provider == "anthropic":
            import anthropic
            api_key = config["anthropic"].get("api_key")
            model = config["anthropic"].get("model_testcases", "claude-3-5-haiku-20241022")
            client = anthropic.Anthropic(api_key=api_key)
            response = client.messages.create(
                model=model,
                max_tokens=2048,
                messages=[{"role": "user", "content": prompt}]
            )
            content = response.content[0].text

        elif provider == "google":
            import google.generativeai as genai
            api_key = config["google"].get("api_key")
            model = config["google"].get("model_testcases", "gemini-1.5-flash")
            genai.configure(api_key=api_key)
            gen_model = genai.GenerativeModel(model)
            response = gen_model.generate_content(prompt)
            content = response.text

        else:
            logger.error(f"Unknown provider: {provider}")
            return []

        return parse_test_cases(content)

    except Exception as e:
        logger.error(f"Error generating test cases for {ticket.jira_key}: {e}")
        raise


def parse_test_cases(content: str) -> list[dict]:
    """Parse the generated content into structured test cases."""
    test_cases = []

    # Split by TC- pattern
    tc_blocks = re.split(r'(?=TC-\d+:)', content.strip())

    for block in tc_blocks:
        block = block.strip()
        if not block or not block.startswith('TC-'):
            continue

        tc = {
            "id": "",
            "title": "",
            "pre": "",
            "steps": "",
            "expected": ""
        }

        lines = block.split('\n')
        current_section = None
        section_content = []

        for line in lines:
            line_stripped = line.strip()

            # Parse TC-ID: Title
            if line_stripped.startswith('TC-'):
                match = re.match(r'TC-(\d+):\s*(.+)', line_stripped)
                if match:
                    tc["id"] = match.group(1)
                    tc["title"] = match.group(2)
                continue

            # Detect section headers (support both English and Spanish)
            if line_stripped.startswith('PRE:'):
                if current_section and section_content:
                    tc[current_section] = '\n'.join(section_content).strip()
                current_section = 'pre'
                rest = line_stripped[4:].strip()
                section_content = [rest] if rest else []
                continue

            if line_stripped.startswith('STEPS:') or line_stripped.startswith('PASOS:'):
                if current_section and section_content:
                    tc[current_section] = '\n'.join(section_content).strip()
                current_section = 'steps'
                section_content = []
                continue

            if line_stripped.startswith('EXPECTED:') or line_stripped.startswith('ESPERADO:'):
                if current_section and section_content:
                    tc[current_section] = '\n'.join(section_content).strip()
                current_section = 'expected'
                section_content = []
                continue

            # Skip separator lines
            if line_stripped == '---':
                continue

            # Add content to current section
            if current_section and line_stripped:
                section_content.append(line)

        # Save last section
        if current_section and section_content:
            tc[current_section] = '\n'.join(section_content).strip()

        # Only add if we have meaningful content
        if tc["id"] and (tc["title"] or tc["steps"]):
            test_cases.append(tc)

    return test_cases
