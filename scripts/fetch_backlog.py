#!/usr/bin/env python3
"""Wrapper script for fetching tickets from Jira."""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.jira.fetcher import fetch_backlog

if __name__ == "__main__":
    fetch_backlog(verbose=True)
