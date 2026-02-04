import logging
from openai import OpenAI
from app.db.model import Ticket
from app.config import load_config

logger = logging.getLogger(__name__)


def generate_questions(ticket: Ticket) -> list[str]:
    if not ticket.description or not ticket.title:
        return []

    config = load_config()
    provider = config.get("ai_provider", "openai")

    prompt = f"""
    You are a QA assistant working on a healthcare platform.

    Your task is to help the QA team **define 3 to 5 smart questions** before implementing the following Jira ticket.

    ---
    Title: {ticket.title.strip()}
    Description: {ticket.description.strip()}
    Issue type: {ticket.issue_type}
    ---

    The goal is to uncover:
    - Possible edge cases or system dependencies
    - Risky assumptions or vague requirements
    - Clinical or workflow-specific considerations
    - Scenarios that could break under real-world usage

    Return the questions in clear English as a bullet list.
    Do not include any explanation or commentary—only the questions.
    """

    try:
        if provider == "openai":
            api_key = config["openai"].get("api_key")
            model = config["openai"].get("model_questions", "gpt-4-turbo")
            client = OpenAI(api_key=api_key)
            response = client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
            )
            content = response.choices[0].message.content

        elif provider == "anthropic":
            import anthropic
            api_key = config["anthropic"].get("api_key")
            model = config["anthropic"].get("model_questions", "claude-3-5-sonnet-20241022")
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
            model = config["google"].get("model_questions", "gemini-1.5-pro")
            genai.configure(api_key=api_key)
            gen_model = genai.GenerativeModel(model)
            response = gen_model.generate_content(prompt)
            content = response.text

        else:
            logger.error(f"Unknown provider: {provider}")
            return []

        return [line.lstrip("-*0123456789. ").strip() for line in content.strip().split("\n") if line.strip()]

    except Exception as e:
        logger.error(f"Error generating questions for {ticket.jira_key}: {e}")
        raise  # Re-raise so the UI can show the error
