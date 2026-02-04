"""Centralized configuration for ProRef."""

import os
import json
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# Config file path
CONFIG_FILE = Path(__file__).parent.parent / "data" / "config.json"

# Default configuration
DEFAULT_CONFIG = {
    "ai_provider": "openai",
    "openai": {
        "api_key": "",
        "model_questions": "gpt-4-turbo",
        "model_testcases": "gpt-3.5-turbo",
        "model_chat": "gpt-4-turbo",
        "model_embedding": "text-embedding-3-small"
    },
    "anthropic": {
        "api_key": "",
        "model_questions": "claude-3-5-sonnet-20241022",
        "model_testcases": "claude-3-5-haiku-20241022",
        "model_chat": "claude-3-5-sonnet-20241022"
    },
    "google": {
        "api_key": "",
        "model_questions": "gemini-1.5-pro",
        "model_testcases": "gemini-1.5-flash",
        "model_chat": "gemini-1.5-pro",
        "model_embedding": "text-embedding-004"
    },
    "jira": {
        "base_url": "",
        "user": "",
        "api_token": "",
        "project": "",
        "sprint": "",
        "jql": ""
    }
}


def load_config() -> dict:
    """Load configuration from file, merging with defaults."""
    config = DEFAULT_CONFIG.copy()

    # Try to load from file
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, 'r') as f:
                saved = json.load(f)
                # Deep merge
                for key, value in saved.items():
                    if isinstance(value, dict) and key in config:
                        config[key].update(value)
                    else:
                        config[key] = value
        except Exception:
            pass

    # Use environment variables only as FALLBACK (if config file doesn't have value)
    # This allows UI-saved values to take precedence
    if not config["openai"]["api_key"] and os.getenv("OPENAI_API_KEY"):
        config["openai"]["api_key"] = os.getenv("OPENAI_API_KEY")
    if not config["anthropic"]["api_key"] and os.getenv("ANTHROPIC_API_KEY"):
        config["anthropic"]["api_key"] = os.getenv("ANTHROPIC_API_KEY")
    if not config["google"]["api_key"] and os.getenv("GOOGLE_API_KEY"):
        config["google"]["api_key"] = os.getenv("GOOGLE_API_KEY")

    # Jira from env (fallback only)
    if not config["jira"]["base_url"] and os.getenv("JIRA_BASE_URL"):
        config["jira"]["base_url"] = os.getenv("JIRA_BASE_URL")
    if not config["jira"]["user"] and os.getenv("JIRA_USER"):
        config["jira"]["user"] = os.getenv("JIRA_USER")
    if not config["jira"]["api_token"] and os.getenv("JIRA_API_TOKEN"):
        config["jira"]["api_token"] = os.getenv("JIRA_API_TOKEN")
    if not config["jira"]["project"] and os.getenv("JIRA_PROJECT"):
        config["jira"]["project"] = os.getenv("JIRA_PROJECT")
    if not config["jira"]["sprint"] and os.getenv("JIRA_SPRINT"):
        config["jira"]["sprint"] = os.getenv("JIRA_SPRINT")
    if not config["jira"]["jql"] and os.getenv("JIRA_JQL"):
        config["jira"]["jql"] = os.getenv("JIRA_JQL")

    # Model from env (fallback only)
    if not config["openai"].get("model_questions") and os.getenv("OPENAI_MODEL_QUESTIONS"):
        config["openai"]["model_questions"] = os.getenv("OPENAI_MODEL_QUESTIONS")
    if not config["openai"].get("model_testcases") and os.getenv("OPENAI_MODEL_TESTCASES"):
        config["openai"]["model_testcases"] = os.getenv("OPENAI_MODEL_TESTCASES")
    if not config["openai"].get("model_chat") and os.getenv("OPENAI_MODEL_CHAT"):
        config["openai"]["model_chat"] = os.getenv("OPENAI_MODEL_CHAT")
    if not config["openai"].get("model_embedding") and os.getenv("OPENAI_MODEL_EMBEDDING"):
        config["openai"]["model_embedding"] = os.getenv("OPENAI_MODEL_EMBEDDING")

    return config


def save_config(config: dict):
    """Save configuration to file."""
    CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f, indent=2)


def get_config():
    """Get current configuration."""
    return load_config()


# Backwards compatible exports
_config = load_config()

# OpenAI Configuration (legacy)
OPENAI_API_KEY = _config["openai"]["api_key"] or os.getenv("OPENAI_API_KEY")

# Model Configuration (legacy)
MODEL_QUESTIONS = _config["openai"]["model_questions"]
MODEL_TESTCASES = _config["openai"]["model_testcases"]
MODEL_CHAT = _config["openai"]["model_chat"]
MODEL_EMBEDDING = _config["openai"]["model_embedding"]

# Jira Configuration (legacy)
JIRA_BASE_URL = _config["jira"]["base_url"] or os.getenv("JIRA_BASE_URL")
JIRA_USER = _config["jira"]["user"] or os.getenv("JIRA_USER")
JIRA_API_TOKEN = _config["jira"]["api_token"] or os.getenv("JIRA_API_TOKEN")
JIRA_PROJECT = _config["jira"]["project"] or os.getenv("JIRA_PROJECT")
JIRA_SPRINT = _config["jira"]["sprint"] or os.getenv("JIRA_SPRINT")
JIRA_JQL = _config["jira"]["jql"] or os.getenv("JIRA_JQL")


def get_jql():
    """Get JQL query from config, either direct or constructed."""
    config = load_config()
    jql = config["jira"]["jql"]
    project = config["jira"]["project"]
    sprint = config["jira"]["sprint"]

    if jql:
        return jql
    elif project and sprint:
        return f'project = {project} AND Sprint = "{sprint}" ORDER BY updated DESC'
    else:
        raise ValueError("Either JIRA_JQL or both JIRA_PROJECT and JIRA_SPRINT must be set")


def validate_jira_config():
    """Validate that required Jira configuration is present."""
    config = load_config()
    jira = config["jira"]
    if not all([jira["base_url"], jira["user"], jira["api_token"]]):
        raise ValueError(
            "Missing required Jira configuration. "
            "Please set JIRA_BASE_URL, JIRA_USER, and JIRA_API_TOKEN"
        )


def get_ai_client():
    """Get the AI client based on configured provider."""
    config = load_config()
    provider = config["ai_provider"]

    if provider == "openai":
        from openai import OpenAI
        return OpenAI(api_key=config["openai"]["api_key"]), config["openai"]
    elif provider == "anthropic":
        import anthropic
        return anthropic.Anthropic(api_key=config["anthropic"]["api_key"]), config["anthropic"]
    elif provider == "google":
        import google.generativeai as genai
        genai.configure(api_key=config["google"]["api_key"])
        return genai, config["google"]
    else:
        raise ValueError(f"Unknown AI provider: {provider}")


def get_model_for_task(task: str) -> str:
    """Get the model name for a specific task."""
    config = load_config()
    provider = config["ai_provider"]
    provider_config = config.get(provider, {})

    model_key = f"model_{task}"
    return provider_config.get(model_key, "")
