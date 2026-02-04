"""Tests for prompts module."""

import pytest


class TestDomainPresets:
    """Tests for domain presets."""

    def test_generic_preset_exists(self):
        """Generic preset should always exist."""
        from app.logic.prompts import DOMAIN_PRESETS

        assert "generic" in DOMAIN_PRESETS
        assert "questions_prompt" in DOMAIN_PRESETS["generic"]
        assert "testcases_prompt" in DOMAIN_PRESETS["generic"]

    def test_all_presets_have_required_fields(self):
        """All presets should have name, description, and prompts."""
        from app.logic.prompts import DOMAIN_PRESETS

        required_fields = ["name", "description", "questions_prompt", "testcases_prompt"]

        for key, preset in DOMAIN_PRESETS.items():
            for field in required_fields:
                assert field in preset, f"Preset '{key}' missing field '{field}'"

    def test_healthcare_preset_mentions_hipaa(self):
        """Healthcare preset should mention HIPAA compliance."""
        from app.logic.prompts import DOMAIN_PRESETS

        healthcare = DOMAIN_PRESETS["healthcare"]
        assert "HIPAA" in healthcare["questions_prompt"]
        assert "HIPAA" in healthcare["testcases_prompt"]

    def test_fintech_preset_mentions_security(self):
        """Fintech preset should mention security."""
        from app.logic.prompts import DOMAIN_PRESETS

        fintech = DOMAIN_PRESETS["fintech"]
        assert "security" in fintech["questions_prompt"].lower()


class TestGetDomainList:
    """Tests for get_domain_list function."""

    def test_returns_list_of_domains(self):
        """Should return a list of domain dictionaries."""
        from app.logic.prompts import get_domain_list

        domains = get_domain_list()

        assert isinstance(domains, list)
        assert len(domains) >= 5  # At least 5 presets

    def test_each_domain_has_required_keys(self):
        """Each domain should have key, name, and description."""
        from app.logic.prompts import get_domain_list

        domains = get_domain_list()

        for domain in domains:
            assert "key" in domain
            assert "name" in domain
            assert "description" in domain


class TestGetPrompt:
    """Tests for get_prompt function."""

    def test_returns_formatted_prompt(self):
        """Should return prompt with ticket data substituted."""
        from app.logic.prompts import get_prompt

        ticket_data = {
            "title": "Test Title",
            "description": "Test Description",
            "issue_type": "Story"
        }

        result = get_prompt("generic", "questions", ticket_data)

        assert "Test Title" in result
        assert "Test Description" in result
        assert "Story" in result

    def test_falls_back_to_generic(self):
        """Unknown domain should fall back to generic."""
        from app.logic.prompts import get_prompt

        ticket_data = {
            "title": "Test",
            "description": "Desc",
            "issue_type": "Bug"
        }

        result = get_prompt("unknown_domain", "questions", ticket_data)

        # Should still work with generic fallback
        assert "Test" in result

    def test_handles_missing_ticket_data(self):
        """Should handle missing ticket data gracefully."""
        from app.logic.prompts import get_prompt

        ticket_data = {}

        result = get_prompt("generic", "questions", ticket_data)

        assert "No title" in result
        assert "No description" in result


class TestGetCustomPrompt:
    """Tests for get_custom_prompt function."""

    def test_formats_custom_template(self):
        """Should format custom template with ticket data."""
        from app.logic.prompts import get_custom_prompt

        template = "Ticket: {title} ({issue_type})\n{description}"
        ticket_data = {
            "title": "My Ticket",
            "description": "My Description",
            "issue_type": "Task"
        }

        result = get_custom_prompt(template, ticket_data)

        assert "My Ticket" in result
        assert "My Description" in result
        assert "Task" in result

    def test_handles_partial_template(self):
        """Should handle template with only some placeholders."""
        from app.logic.prompts import get_custom_prompt

        template = "Just the title: {title}"
        ticket_data = {"title": "Test"}

        result = get_custom_prompt(template, ticket_data)

        assert "Test" in result
