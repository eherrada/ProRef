"""Jira ticket fetcher module."""

import logging
import requests
from datetime import datetime
from typing import List, Dict, Any, Optional

from app.config import (
    JIRA_BASE_URL, JIRA_USER, JIRA_API_TOKEN,
    get_jql, validate_jira_config, load_config
)
from app.db.model import init_db
from app.db.save import save_or_update_ticket
from app.io.adf_parser import parse_adf_to_text
from app.utils.retry import retry

logger = logging.getLogger(__name__)


def fetch_jira_projects() -> List[Dict[str, str]]:
    """Fetch available projects from Jira."""
    config = load_config()
    base_url = config["jira"]["base_url"]
    user = config["jira"]["user"]
    token = config["jira"]["api_token"]

    if not all([base_url, user, token]):
        return []

    try:
        url = f"{base_url}/rest/api/3/project"
        response = requests.get(
            url,
            headers={"Accept": "application/json"},
            auth=(user, token)
        )
        response.raise_for_status()
        projects = response.json()
        return [{"key": p["key"], "name": p["name"]} for p in projects]
    except Exception as e:
        logger.error(f"Failed to fetch projects: {e}")
        return []


def fetch_jira_boards(project_key: str = None) -> List[Dict[str, Any]]:
    """Fetch available boards from Jira."""
    config = load_config()
    base_url = config["jira"]["base_url"]
    user = config["jira"]["user"]
    token = config["jira"]["api_token"]

    if not all([base_url, user, token]):
        return []

    try:
        url = f"{base_url}/rest/agile/1.0/board"
        params = {}
        if project_key:
            params["projectKeyOrId"] = project_key

        response = requests.get(
            url,
            headers={"Accept": "application/json"},
            params=params,
            auth=(user, token)
        )
        response.raise_for_status()
        data = response.json()
        return [{"id": b["id"], "name": b["name"], "type": b.get("type", "")} for b in data.get("values", [])]
    except Exception as e:
        logger.error(f"Failed to fetch boards: {e}")
        return []


def fetch_jira_sprints(board_id: int) -> List[Dict[str, Any]]:
    """Fetch sprints for a board."""
    config = load_config()
    base_url = config["jira"]["base_url"]
    user = config["jira"]["user"]
    token = config["jira"]["api_token"]

    if not all([base_url, user, token]):
        return []

    try:
        url = f"{base_url}/rest/agile/1.0/board/{board_id}/sprint"
        response = requests.get(
            url,
            headers={"Accept": "application/json"},
            auth=(user, token)
        )
        response.raise_for_status()
        data = response.json()
        sprints = data.get("values", [])
        # Return most recent sprints first
        return [{"id": s["id"], "name": s["name"], "state": s.get("state", "")} for s in reversed(sprints)]
    except Exception as e:
        logger.error(f"Failed to fetch sprints: {e}")
        return []


def fetch_jira_issue_types(project_key: str) -> List[str]:
    """Fetch issue types for a project."""
    config = load_config()
    base_url = config["jira"]["base_url"]
    user = config["jira"]["user"]
    token = config["jira"]["api_token"]

    if not all([base_url, user, token]):
        return []

    try:
        url = f"{base_url}/rest/api/3/project/{project_key}"
        response = requests.get(
            url,
            headers={"Accept": "application/json"},
            auth=(user, token)
        )
        response.raise_for_status()
        data = response.json()
        issue_types = data.get("issueTypes", [])
        return [it["name"] for it in issue_types]
    except Exception as e:
        logger.error(f"Failed to fetch issue types: {e}")
        return []


def create_jira_ticket(
    project_key: str,
    summary: str,
    description: str,
    issue_type: str = "Story"
) -> tuple[bool, str]:
    """Create a ticket in Jira.

    Returns:
        Tuple of (success, ticket_key or error message)
    """
    config = load_config()
    base_url = config["jira"]["base_url"]
    user = config["jira"]["user"]
    token = config["jira"]["api_token"]

    if not all([base_url, user, token]):
        return False, "Jira not configured"

    try:
        url = f"{base_url}/rest/api/3/issue"

        # Build ADF description
        adf_description = {
            "type": "doc",
            "version": 1,
            "content": []
        }

        # Split description into paragraphs
        for para in description.split('\n\n'):
            if para.strip():
                # Check if it's a header (starts with ##)
                if para.strip().startswith('## '):
                    adf_description["content"].append({
                        "type": "heading",
                        "attrs": {"level": 3},
                        "content": [{"type": "text", "text": para.strip()[3:]}]
                    })
                elif para.strip().startswith('- '):
                    # Bullet list
                    items = [line.strip()[2:] for line in para.split('\n') if line.strip().startswith('- ')]
                    adf_description["content"].append({
                        "type": "bulletList",
                        "content": [
                            {
                                "type": "listItem",
                                "content": [{
                                    "type": "paragraph",
                                    "content": [{"type": "text", "text": item}]
                                }]
                            }
                            for item in items
                        ]
                    })
                else:
                    # Regular paragraph with line breaks
                    lines = para.split('\n')
                    content = []
                    for i, line in enumerate(lines):
                        if line.strip():
                            content.append({"type": "text", "text": line.strip()})
                        if i < len(lines) - 1:
                            content.append({"type": "hardBreak"})
                    if content:
                        adf_description["content"].append({
                            "type": "paragraph",
                            "content": content
                        })

        payload = {
            "fields": {
                "project": {"key": project_key},
                "summary": summary,
                "description": adf_description,
                "issuetype": {"name": issue_type}
            }
        }

        response = requests.post(
            url,
            headers={"Accept": "application/json", "Content-Type": "application/json"},
            json=payload,
            auth=(user, token)
        )
        response.raise_for_status()
        data = response.json()
        return True, data.get("key", "Unknown")
    except requests.exceptions.HTTPError as e:
        error_detail = ""
        try:
            error_detail = e.response.json()
        except:
            error_detail = e.response.text
        return False, f"HTTP {e.response.status_code}: {error_detail}"
    except Exception as e:
        return False, str(e)


def test_jira_connection() -> tuple[bool, str]:
    """Test Jira connection and return status."""
    config = load_config()
    base_url = config["jira"]["base_url"]
    user = config["jira"]["user"]
    token = config["jira"]["api_token"]

    if not base_url:
        return False, "Jira URL not configured"
    if not user:
        return False, "Jira user not configured"
    if not token:
        return False, "Jira API token not configured"

    try:
        url = f"{base_url}/rest/api/3/myself"
        response = requests.get(
            url,
            headers={"Accept": "application/json"},
            auth=(user, token)
        )
        response.raise_for_status()
        data = response.json()
        return True, f"Connected as {data.get('displayName', user)}"
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 401:
            return False, "Authentication failed - check email and API token"
        return False, f"HTTP Error: {e.response.status_code}"
    except Exception as e:
        return False, f"Connection failed: {str(e)}"


def _fetch_from_jira(jql: str, max_results: int = 150) -> List[Dict[str, Any]]:
    """Fetch issues from Jira API with automatic endpoint detection.

    Tries endpoints in order:
    1. /rest/api/3/search/jql (new, 2024+)
    2. /rest/api/3/search (legacy v3)
    3. /rest/api/2/search (legacy v2)
    """
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json"
    }
    auth = (JIRA_USER, JIRA_API_TOKEN)

    # Endpoints to try in order of preference
    endpoints = [
        {
            "url": f"{JIRA_BASE_URL}/rest/api/3/search/jql",
            "method": "POST",
            "payload": {
                "jql": jql,
                "fields": ["summary", "description", "status", "updated", "issuetype"],
                "maxResults": max_results
            }
        },
        {
            "url": f"{JIRA_BASE_URL}/rest/api/3/search",
            "method": "GET",
            "params": {
                "jql": jql,
                "fields": "summary,description,status,updated,issuetype",
                "maxResults": max_results
            }
        },
        {
            "url": f"{JIRA_BASE_URL}/rest/api/2/search",
            "method": "GET",
            "params": {
                "jql": jql,
                "fields": "summary,description,status,updated,issuetype",
                "maxResults": max_results
            }
        }
    ]

    last_error = None
    for endpoint in endpoints:
        try:
            if endpoint["method"] == "POST":
                response = requests.post(
                    endpoint["url"],
                    headers=headers,
                    json=endpoint.get("payload"),
                    auth=auth
                )
            else:
                response = requests.get(
                    endpoint["url"],
                    headers=headers,
                    params=endpoint.get("params"),
                    auth=auth
                )

            # If we get a 410 Gone, try next endpoint
            if response.status_code == 410:
                logger.debug(f"Endpoint {endpoint['url']} returned 410, trying next...")
                continue

            response.raise_for_status()
            logger.info(f"Successfully using endpoint: {endpoint['url']}")
            return response.json().get("issues", [])

        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 410:
                continue  # Try next endpoint
            last_error = e
            logger.warning(f"Endpoint {endpoint['url']} failed: {e}")
        except Exception as e:
            last_error = e
            logger.warning(f"Endpoint {endpoint['url']} failed: {e}")

    # All endpoints failed
    raise last_error or Exception("All Jira API endpoints failed")


def fetch_backlog(verbose: bool = True) -> int:
    """
    Fetch tickets from Jira and save to database.

    Args:
        verbose: Whether to print progress messages

    Returns:
        Number of tickets processed (excluding spikes)
    """
    validate_jira_config()
    init_db()

    jql = get_jql()
    if verbose:
        print(f"JQL Query: {jql}")
        print("Querying tickets from Jira...")

    try:
        issues = _fetch_from_jira(jql)
    except requests.RequestException as e:
        logger.error(f"Failed to fetch from Jira: {e}")
        if verbose:
            print(f"Error fetching from Jira: {e}")
        return 0

    processed = 0
    for issue in issues:
        key = issue["key"]
        fields = issue["fields"]

        description = fields.get("description")
        if isinstance(description, dict):
            description = parse_adf_to_text(description)
        elif description is None:
            description = ""

        updated_str = fields.get("updated")
        updated_at = None
        if updated_str:
            updated_at = datetime.strptime(updated_str, "%Y-%m-%dT%H:%M:%S.%f%z")

        issue_type = fields.get("issuetype", {}).get("name", "").lower()

        if issue_type == "spike":
            if verbose:
                print(f"Skipping SPIKE: {key}")
            continue

        ticket_data = {
            "id": key,
            "jira_key": key,
            "title": fields.get("summary"),
            "description": description,
            "issue_type": issue_type,
            "status": fields.get("status", {}).get("name", ""),
            "updated_at": updated_at
        }

        save_or_update_ticket(ticket_data)
        if verbose:
            print(f"Saved: [{key}] {fields['summary']}")
        processed += 1

    if verbose:
        print(f"Total tickets processed (excluding Spikes): {processed}")

    return processed
