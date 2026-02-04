"""ProRef Streamlit UI - Modern Redesign v2."""

import json
import streamlit as st
from openai import OpenAI
from datetime import datetime

from app.config import load_config, save_config, get_config
from app.paths import ensure_dirs
from app.db.model import SessionLocal, Ticket, GeneratedContent, TicketEmbedding, init_db
from app.db.embedding import save_embedding
from app.logic.embedder import get_embedding
from app.logic.question_generator import generate_questions
from app.logic.test_case_generator import generate_test_cases
from app.logic.matching import match_text_to_ticket
from app.logic.related_tickets import find_related_tickets
from app.jira.fetcher import (
    fetch_backlog, fetch_jira_projects, fetch_jira_boards,
    fetch_jira_sprints, fetch_jira_issue_types, test_jira_connection
)
from app.jira.publisher import post_comment_to_jira, format_questions_for_jira, format_test_cases_for_jira


# ============ MODEL FETCHING ============

@st.cache_data(ttl=300)
def fetch_openai_models(api_key: str) -> dict:
    """Fetch available models from OpenAI API."""
    if not api_key:
        return {"chat": [], "embedding": []}
    try:
        client = OpenAI(api_key=api_key)
        models = client.models.list()
        chat_models = []
        embedding_models = []
        for model in models.data:
            model_id = model.id
            if any(x in model_id for x in ['gpt-4', 'gpt-3.5', 'o1', 'o3']):
                if 'realtime' not in model_id and 'audio' not in model_id:
                    chat_models.append(model_id)
            elif 'embedding' in model_id:
                embedding_models.append(model_id)
        chat_models.sort(key=lambda x: (0 if 'gpt-4o' in x else 1 if 'gpt-4' in x else 2, x))
        embedding_models.sort(reverse=True)
        return {"chat": chat_models, "embedding": embedding_models}
    except Exception:
        return {
            "chat": ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "gpt-4", "gpt-3.5-turbo"],
            "embedding": ["text-embedding-3-small", "text-embedding-3-large"]
        }


@st.cache_data(ttl=300)
def fetch_anthropic_models(api_key: str) -> dict:
    if not api_key:
        return {"chat": []}
    return {"chat": [
        "claude-sonnet-4-20250514", "claude-opus-4-20250514",
        "claude-3-5-sonnet-20241022", "claude-3-5-haiku-20241022",
        "claude-3-opus-20240229"
    ]}


@st.cache_data(ttl=300)
def fetch_google_models(api_key: str) -> dict:
    if not api_key:
        return {"chat": [], "embedding": []}
    return {
        "chat": ["gemini-1.5-pro", "gemini-1.5-flash", "gemini-1.0-pro"],
        "embedding": ["text-embedding-004"]
    }


# ============ PAGE CONFIG & STYLES ============

st.set_page_config(
    page_title="ProRef",
    page_icon="rocket",
    layout="wide",
    initial_sidebar_state="collapsed"
)

st.markdown("""
<style>
    /* Hide Streamlit defaults */
    [data-testid="stSidebar"] { display: none; }
    [data-testid="collapsedControl"] { display: none; }
    #MainMenu, footer, header { visibility: hidden; }

    /* Root variables */
    :root {
        --bg-base: #08080c;
        --bg-surface: #0f0f14;
        --bg-elevated: #16161d;
        --bg-hover: #1c1c26;

        --accent: #6366f1;
        --accent-hover: #818cf8;
        --accent-muted: rgba(99, 102, 241, 0.15);

        --success: #22c55e;
        --success-muted: rgba(34, 197, 94, 0.15);
        --warning: #f59e0b;
        --warning-muted: rgba(245, 158, 11, 0.15);
        --error: #ef4444;
        --error-muted: rgba(239, 68, 68, 0.15);

        --text-primary: #f1f5f9;
        --text-secondary: #94a3b8;
        --text-muted: #64748b;

        --border: rgba(255, 255, 255, 0.06);
        --border-hover: rgba(99, 102, 241, 0.4);

        --radius-sm: 6px;
        --radius-md: 10px;
        --radius-lg: 14px;
    }

    .stApp {
        background: var(--bg-base);
    }

    /* ===== HEADER ===== */
    .app-header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 1rem 0;
        margin-bottom: 1.5rem;
        border-bottom: 1px solid var(--border);
    }

    .logo {
        display: flex;
        align-items: center;
        gap: 0.75rem;
    }

    .logo-icon {
        width: 36px;
        height: 36px;
        background: linear-gradient(135deg, var(--accent) 0%, #8b5cf6 100%);
        border-radius: var(--radius-md);
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 1.25rem;
    }

    .logo-text {
        font-size: 1.35rem;
        font-weight: 700;
        color: var(--text-primary);
        letter-spacing: -0.02em;
    }

    /* ===== NAVIGATION ===== */
    .nav-container {
        display: flex;
        gap: 0.5rem;
        align-items: center;
    }

    .nav-item {
        padding: 0.5rem 1rem;
        border-radius: var(--radius-md);
        color: var(--text-secondary);
        font-size: 0.875rem;
        font-weight: 500;
        cursor: pointer;
        transition: all 0.15s ease;
        border: 1px solid transparent;
        background: transparent;
    }

    .nav-item:hover {
        color: var(--text-primary);
        background: var(--bg-elevated);
    }

    .nav-item.active {
        color: white;
        background: var(--accent);
        border-color: var(--accent);
    }

    .nav-divider {
        width: 1px;
        height: 24px;
        background: var(--border);
        margin: 0 0.5rem;
    }

    /* ===== PAGE HEADER ===== */
    .page-header {
        margin-bottom: 2rem;
    }

    .page-title {
        font-size: 1.75rem;
        font-weight: 700;
        color: var(--text-primary);
        margin: 0 0 0.25rem 0;
        letter-spacing: -0.02em;
    }

    .page-subtitle {
        color: var(--text-muted);
        font-size: 0.95rem;
        margin: 0;
    }

    /* ===== CARDS ===== */
    .card {
        background: var(--bg-surface);
        border: 1px solid var(--border);
        border-radius: var(--radius-lg);
        padding: 1.25rem;
        transition: all 0.2s ease;
    }

    .card:hover {
        border-color: var(--border-hover);
        background: var(--bg-elevated);
    }

    .card-header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        margin-bottom: 1rem;
    }

    .card-title {
        font-size: 0.875rem;
        font-weight: 600;
        color: var(--text-secondary);
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }

    /* ===== METRICS ===== */
    .metric-grid {
        display: grid;
        grid-template-columns: repeat(4, 1fr);
        gap: 1rem;
        margin-bottom: 1.5rem;
    }

    .metric-card {
        background: var(--bg-surface);
        border: 1px solid var(--border);
        border-radius: var(--radius-lg);
        padding: 1.25rem;
        text-align: center;
    }

    .metric-value {
        font-size: 2rem;
        font-weight: 700;
        color: var(--text-primary);
        line-height: 1;
        margin-bottom: 0.5rem;
    }

    .metric-value.accent { color: var(--accent); }
    .metric-value.success { color: var(--success); }
    .metric-value.warning { color: var(--warning); }

    .metric-label {
        font-size: 0.8rem;
        color: var(--text-muted);
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }

    /* ===== WORKFLOW STEPS ===== */
    .workflow {
        display: flex;
        align-items: center;
        gap: 0;
        margin: 2rem 0;
        padding: 1.5rem;
        background: var(--bg-surface);
        border: 1px solid var(--border);
        border-radius: var(--radius-lg);
    }

    .workflow-step {
        flex: 1;
        text-align: center;
        position: relative;
        padding: 0 1rem;
    }

    .workflow-step:not(:last-child)::after {
        content: '';
        position: absolute;
        right: -20px;
        top: 50%;
        transform: translateY(-50%);
        width: 40px;
        height: 2px;
        background: var(--border);
    }

    .workflow-step.done:not(:last-child)::after {
        background: var(--success);
    }

    .step-icon {
        width: 48px;
        height: 48px;
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        margin: 0 auto 0.75rem;
        font-size: 1.25rem;
        border: 2px solid var(--border);
        background: var(--bg-elevated);
        color: var(--text-muted);
    }

    .workflow-step.done .step-icon {
        background: var(--success-muted);
        border-color: var(--success);
        color: var(--success);
    }

    .workflow-step.active .step-icon {
        background: var(--accent-muted);
        border-color: var(--accent);
        color: var(--accent);
        animation: pulse 2s infinite;
    }

    @keyframes pulse {
        0%, 100% { box-shadow: 0 0 0 0 rgba(99, 102, 241, 0.4); }
        50% { box-shadow: 0 0 0 8px rgba(99, 102, 241, 0); }
    }

    .step-label {
        font-size: 0.8rem;
        font-weight: 600;
        color: var(--text-secondary);
        margin-bottom: 0.25rem;
    }

    .step-value {
        font-size: 0.75rem;
        color: var(--text-muted);
    }

    /* ===== QUICK ACTIONS ===== */
    .quick-actions {
        display: grid;
        grid-template-columns: repeat(3, 1fr);
        gap: 1rem;
        margin: 1.5rem 0;
    }

    .action-card {
        background: var(--bg-surface);
        border: 1px solid var(--border);
        border-radius: var(--radius-lg);
        padding: 1.25rem;
        cursor: pointer;
        transition: all 0.2s ease;
    }

    .action-card:hover {
        border-color: var(--accent);
        transform: translateY(-2px);
    }

    .action-icon {
        font-size: 1.5rem;
        margin-bottom: 0.75rem;
    }

    .action-title {
        font-size: 0.95rem;
        font-weight: 600;
        color: var(--text-primary);
        margin-bottom: 0.25rem;
    }

    .action-desc {
        font-size: 0.8rem;
        color: var(--text-muted);
    }

    /* ===== TABS ===== */
    .tabs-container {
        display: flex;
        gap: 0.25rem;
        border-bottom: 1px solid var(--border);
        margin-bottom: 1.5rem;
    }

    .tab {
        padding: 0.75rem 1.25rem;
        color: var(--text-muted);
        font-size: 0.875rem;
        font-weight: 500;
        cursor: pointer;
        border-bottom: 2px solid transparent;
        transition: all 0.15s ease;
    }

    .tab:hover {
        color: var(--text-secondary);
    }

    .tab.active {
        color: var(--accent);
        border-bottom-color: var(--accent);
    }

    .tab-count {
        background: var(--bg-elevated);
        padding: 0.125rem 0.5rem;
        border-radius: 10px;
        font-size: 0.75rem;
        margin-left: 0.5rem;
    }

    .tab.active .tab-count {
        background: var(--accent-muted);
        color: var(--accent);
    }

    /* ===== TICKET CARDS ===== */
    .ticket-card {
        background: var(--bg-surface);
        border: 1px solid var(--border);
        border-radius: var(--radius-lg);
        padding: 1rem 1.25rem;
        margin-bottom: 0.75rem;
        transition: all 0.2s ease;
    }

    .ticket-card:hover {
        border-color: var(--border-hover);
        background: var(--bg-elevated);
    }

    .ticket-header {
        display: flex;
        align-items: flex-start;
        justify-content: space-between;
        margin-bottom: 0.5rem;
    }

    .ticket-key {
        font-size: 0.8rem;
        font-weight: 600;
        color: var(--accent);
        margin-bottom: 0.25rem;
    }

    .ticket-title {
        font-size: 0.95rem;
        color: var(--text-primary);
        font-weight: 500;
        line-height: 1.4;
    }

    .ticket-meta {
        display: flex;
        align-items: center;
        gap: 1rem;
        margin-top: 0.75rem;
    }

    .ticket-type {
        font-size: 0.75rem;
        color: var(--text-muted);
        background: var(--bg-elevated);
        padding: 0.2rem 0.6rem;
        border-radius: var(--radius-sm);
    }

    /* ===== BADGES ===== */
    .badge {
        display: inline-flex;
        align-items: center;
        gap: 0.3rem;
        padding: 0.25rem 0.6rem;
        border-radius: var(--radius-sm);
        font-size: 0.7rem;
        font-weight: 600;
    }

    .badge-success {
        background: var(--success-muted);
        color: var(--success);
    }

    .badge-warning {
        background: var(--warning-muted);
        color: var(--warning);
    }

    .badge-error {
        background: var(--error-muted);
        color: var(--error);
    }

    .badge-neutral {
        background: var(--bg-elevated);
        color: var(--text-muted);
    }

    /* ===== STATUS INDICATORS ===== */
    .status-row {
        display: flex;
        align-items: center;
        gap: 0.5rem;
    }

    .status-dot {
        width: 8px;
        height: 8px;
        border-radius: 50%;
        background: var(--text-muted);
    }

    .status-dot.done { background: var(--success); }
    .status-dot.pending { background: var(--warning); }
    .status-dot.missing { background: var(--error); }

    /* ===== EMPTY STATE ===== */
    .empty-state {
        text-align: center;
        padding: 4rem 2rem;
    }

    .empty-icon {
        font-size: 3rem;
        margin-bottom: 1rem;
        opacity: 0.5;
    }

    .empty-title {
        font-size: 1.1rem;
        font-weight: 600;
        color: var(--text-secondary);
        margin-bottom: 0.5rem;
    }

    .empty-text {
        color: var(--text-muted);
        font-size: 0.9rem;
    }

    /* ===== FORMS ===== */
    .stTextInput > div > div > input,
    .stSelectbox > div > div,
    .stTextArea > div > div > textarea,
    .stMultiSelect > div > div {
        background: var(--bg-elevated) !important;
        border: 1px solid var(--border) !important;
        border-radius: var(--radius-md) !important;
        color: var(--text-primary) !important;
    }

    .stTextInput > div > div > input:focus,
    .stTextArea > div > div > textarea:focus {
        border-color: var(--accent) !important;
        box-shadow: 0 0 0 2px var(--accent-muted) !important;
    }

    /* ===== BUTTONS ===== */
    .stButton > button {
        background: var(--accent) !important;
        color: white !important;
        border: none !important;
        border-radius: var(--radius-md) !important;
        padding: 0.5rem 1rem !important;
        font-weight: 500 !important;
        font-size: 0.875rem !important;
        transition: all 0.15s ease !important;
    }

    .stButton > button:hover {
        background: var(--accent-hover) !important;
        transform: translateY(-1px) !important;
    }

    .stButton > button[kind="secondary"] {
        background: transparent !important;
        border: 1px solid var(--border) !important;
        color: var(--text-secondary) !important;
    }

    .stButton > button[kind="secondary"]:hover {
        background: var(--bg-elevated) !important;
        color: var(--text-primary) !important;
        border-color: var(--border-hover) !important;
        transform: none !important;
    }

    /* ===== EXPANDER ===== */
    .streamlit-expanderHeader {
        background: var(--bg-surface) !important;
        border: 1px solid var(--border) !important;
        border-radius: var(--radius-md) !important;
    }

    .streamlit-expanderContent {
        background: var(--bg-elevated) !important;
        border: 1px solid var(--border) !important;
        border-top: none !important;
        border-radius: 0 0 var(--radius-md) var(--radius-md) !important;
    }

    /* ===== PAGINATION ===== */
    .pagination {
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 0.5rem;
        margin-top: 1.5rem;
        padding-top: 1rem;
        border-top: 1px solid var(--border);
    }

    .page-info {
        color: var(--text-muted);
        font-size: 0.85rem;
        margin: 0 1rem;
    }

    /* ===== SETTINGS ===== */
    .settings-section {
        background: var(--bg-surface);
        border: 1px solid var(--border);
        border-radius: var(--radius-lg);
        padding: 1.5rem;
        margin-bottom: 1.5rem;
    }

    .settings-title {
        font-size: 1rem;
        font-weight: 600;
        color: var(--text-primary);
        margin-bottom: 1rem;
        display: flex;
        align-items: center;
        gap: 0.5rem;
    }

    /* ===== PROVIDER CARDS ===== */
    .provider-grid {
        display: grid;
        grid-template-columns: repeat(3, 1fr);
        gap: 0.75rem;
        margin-bottom: 1.5rem;
    }

    .provider-card {
        background: var(--bg-elevated);
        border: 2px solid var(--border);
        border-radius: var(--radius-md);
        padding: 1rem;
        text-align: center;
        cursor: pointer;
        transition: all 0.2s ease;
    }

    .provider-card:hover {
        border-color: var(--border-hover);
    }

    .provider-card.active {
        border-color: var(--accent);
        background: var(--accent-muted);
    }

    .provider-icon { font-size: 1.5rem; margin-bottom: 0.5rem; }
    .provider-name { color: var(--text-primary); font-weight: 600; font-size: 0.9rem; }

    /* ===== CHAT ===== */
    .chat-container {
        max-height: 450px;
        overflow-y: auto;
        padding: 1rem;
        background: var(--bg-surface);
        border: 1px solid var(--border);
        border-radius: var(--radius-lg);
        margin-bottom: 1rem;
    }

    .chat-message {
        max-width: 80%;
        padding: 0.875rem 1rem;
        border-radius: var(--radius-lg);
        margin-bottom: 0.75rem;
        font-size: 0.9rem;
        line-height: 1.5;
    }

    .chat-message.user {
        background: var(--accent);
        color: white;
        margin-left: auto;
        border-bottom-right-radius: 4px;
    }

    .chat-message.assistant {
        background: var(--bg-elevated);
        color: var(--text-primary);
        border: 1px solid var(--border);
        border-bottom-left-radius: 4px;
    }

    /* ===== DIVIDERS ===== */
    hr {
        border: none;
        border-top: 1px solid var(--border);
        margin: 1.5rem 0;
    }

    /* ===== ALERTS ===== */
    .alert {
        padding: 1rem 1.25rem;
        border-radius: var(--radius-md);
        margin: 1rem 0;
        display: flex;
        align-items: flex-start;
        gap: 0.75rem;
    }

    .alert-success {
        background: var(--success-muted);
        border: 1px solid rgba(34, 197, 94, 0.3);
    }

    .alert-warning {
        background: var(--warning-muted);
        border: 1px solid rgba(245, 158, 11, 0.3);
    }

    .alert-icon { font-size: 1.25rem; }
    .alert-content { flex: 1; }
    .alert-title { color: var(--text-primary); font-weight: 600; margin-bottom: 0.25rem; }
    .alert-text { color: var(--text-secondary); font-size: 0.85rem; }
</style>
""", unsafe_allow_html=True)


# ============ INITIALIZE ============

init_db()

if "current_page" not in st.session_state:
    st.session_state.current_page = "dashboard"
if "tickets_tab" not in st.session_state:
    st.session_state.tickets_tab = "all"


# ============ HELPERS ============

def get_stats():
    """Get all statistics."""
    session = SessionLocal()
    total = session.query(Ticket).count()
    embedded = session.query(TicketEmbedding).count()
    with_questions = session.query(Ticket).filter(Ticket.questions_generated == True).count()
    with_tests = session.query(Ticket).filter(Ticket.test_cases_generated == True).count()
    pub_q = session.query(GeneratedContent).filter(
        GeneratedContent.content_type == 'questions',
        GeneratedContent.published == True
    ).count()
    pub_t = session.query(GeneratedContent).filter(
        GeneratedContent.content_type == 'test_cases',
        GeneratedContent.published == True
    ).count()
    pending_q = session.query(GeneratedContent).filter(
        GeneratedContent.content_type == 'questions',
        GeneratedContent.published == False
    ).count()
    pending_t = session.query(GeneratedContent).filter(
        GeneratedContent.content_type == 'test_cases',
        GeneratedContent.published == False
    ).count()
    session.close()
    return {
        "total": total, "embedded": embedded,
        "with_questions": with_questions, "with_tests": with_tests,
        "pub_q": pub_q, "pub_t": pub_t,
        "pending_q": pending_q, "pending_t": pending_t,
        "published": pub_q + pub_t
    }


def get_ticket_status(ticket, session):
    """Get status info for a ticket."""
    published = session.query(GeneratedContent).filter_by(
        ticket_id=ticket.id, published=True
    ).all()
    pending = session.query(GeneratedContent).filter_by(
        ticket_id=ticket.id, published=False
    ).all()

    pub_types = {c.content_type for c in published}
    pend_types = {c.content_type for c in pending}

    return {
        "q_published": "questions" in pub_types,
        "q_pending": "questions" in pend_types,
        "q_missing": "questions" not in pub_types and "questions" not in pend_types,
        "t_published": "test_cases" in pub_types,
        "t_pending": "test_cases" in pend_types,
        "t_missing": "test_cases" not in pub_types and "test_cases" not in pend_types,
        "fully_published": "questions" in pub_types and "test_cases" in pub_types
    }


def _update_questions_in_db(ticket_key: str, questions: list):
    """Update questions in database."""
    session = SessionLocal()
    try:
        ticket = session.query(Ticket).filter_by(jira_key=ticket_key).first()
        if ticket:
            content = session.query(GeneratedContent).filter_by(
                ticket_id=ticket.id, content_type='questions'
            ).order_by(GeneratedContent.created_at.desc()).first()
            if content:
                content.content = json.dumps(questions)
                session.commit()
    finally:
        session.close()


def _update_tests_in_db(ticket_key: str, tests: list):
    """Update test cases in database."""
    session = SessionLocal()
    try:
        ticket = session.query(Ticket).filter_by(jira_key=ticket_key).first()
        if ticket:
            content = session.query(GeneratedContent).filter_by(
                ticket_id=ticket.id, content_type='test_cases'
            ).order_by(GeneratedContent.created_at.desc()).first()
            if content:
                content.content = json.dumps(tests)
                session.commit()
    finally:
        session.close()


# ============ NAVIGATION ============

def render_header():
    """Render app header with navigation."""
    st.markdown("""
        <div class="app-header">
            <div class="logo">
                <div class="logo-icon">P</div>
                <span class="logo-text">ProRef</span>
            </div>
        </div>
    """, unsafe_allow_html=True)

    # Navigation
    nav_items = [
        ("dashboard", "Dashboard"),
        ("tickets", "Tickets"),
        ("generate", "Generate"),
        ("publish", "Publish"),
        ("settings", "Settings"),
    ]

    cols = st.columns([1, 1, 1, 1, 1, 2])
    for i, (key, label) in enumerate(nav_items):
        with cols[i]:
            is_active = st.session_state.current_page == key or \
                       (st.session_state.current_page in ["questions", "tests"] and key == "generate")
            btn_type = "primary" if is_active else "secondary"
            if st.button(label, key=f"nav_{key}", use_container_width=True, type=btn_type):
                st.session_state.current_page = key
                st.rerun()


# ============ DASHBOARD ============

def page_dashboard():
    st.markdown("""
        <div class="page-header">
            <h1 class="page-title">Dashboard</h1>
            <p class="page-subtitle">Your refinement workflow at a glance</p>
        </div>
    """, unsafe_allow_html=True)

    stats = get_stats()

    # Workflow steps
    fetch_done = stats["total"] > 0
    embed_done = stats["embedded"] >= stats["total"] and stats["total"] > 0
    gen_done = stats["with_questions"] >= stats["total"] and stats["with_tests"] >= stats["total"] and stats["total"] > 0
    gen_partial = stats["with_questions"] > 0 or stats["with_tests"] > 0
    pub_done = stats["pub_q"] >= stats["total"] and stats["pub_t"] >= stats["total"] and stats["total"] > 0

    fetch_class = "done" if fetch_done else "active" if not fetch_done else ""
    embed_class = "done" if embed_done else "active" if fetch_done and not embed_done else ""
    gen_class = "done" if gen_done else "active" if embed_done and not gen_done else ""
    pub_class = "done" if pub_done else "active" if gen_partial else ""

    st.markdown(f"""
        <div class="workflow">
            <div class="workflow-step {fetch_class}">
                <div class="step-icon">1</div>
                <div class="step-label">Fetch</div>
                <div class="step-value">{stats['total']} tickets</div>
            </div>
            <div class="workflow-step {embed_class}">
                <div class="step-icon">2</div>
                <div class="step-label">Embed</div>
                <div class="step-value">{stats['embedded']}/{stats['total']}</div>
            </div>
            <div class="workflow-step {gen_class}">
                <div class="step-icon">3</div>
                <div class="step-label">Generate</div>
                <div class="step-value">Q:{stats['with_questions']} T:{stats['with_tests']}</div>
            </div>
            <div class="workflow-step {pub_class}">
                <div class="step-icon">4</div>
                <div class="step-label">Publish</div>
                <div class="step-value">{stats['pub_q'] + stats['pub_t']} published</div>
            </div>
        </div>
    """, unsafe_allow_html=True)

    # Metrics
    st.markdown(f"""
        <div class="metric-grid">
            <div class="metric-card">
                <div class="metric-value accent">{stats['total']}</div>
                <div class="metric-label">Total Tickets</div>
            </div>
            <div class="metric-card">
                <div class="metric-value">{stats['with_questions']}</div>
                <div class="metric-label">With Questions</div>
            </div>
            <div class="metric-card">
                <div class="metric-value">{stats['with_tests']}</div>
                <div class="metric-label">With Tests</div>
            </div>
            <div class="metric-card">
                <div class="metric-value success">{stats['pub_q'] + stats['pub_t']}</div>
                <div class="metric-label">Published</div>
            </div>
        </div>
    """, unsafe_allow_html=True)

    # Quick Actions
    st.markdown("### Quick Actions")

    col1, col2, col3 = st.columns(3)

    with col1:
        pending_q = stats["total"] - stats["with_questions"]
        st.markdown(f"""
            <div class="action-card">
                <div class="action-icon">*</div>
                <div class="action-title">Generate Questions</div>
                <div class="action-desc">{pending_q} tickets pending</div>
            </div>
        """, unsafe_allow_html=True)
        if st.button("Generate Questions", key="qa_questions", use_container_width=True):
            st.session_state.current_page = "questions"
            st.rerun()

    with col2:
        pending_t = stats["total"] - stats["with_tests"]
        st.markdown(f"""
            <div class="action-card">
                <div class="action-icon">*</div>
                <div class="action-title">Generate Tests</div>
                <div class="action-desc">{pending_t} tickets pending</div>
            </div>
        """, unsafe_allow_html=True)
        if st.button("Generate Tests", key="qa_tests", use_container_width=True):
            st.session_state.current_page = "tests"
            st.rerun()

    with col3:
        ready = stats["pending_q"] + stats["pending_t"]
        st.markdown(f"""
            <div class="action-card">
                <div class="action-icon">*</div>
                <div class="action-title">Review & Publish</div>
                <div class="action-desc">{ready} items ready</div>
            </div>
        """, unsafe_allow_html=True)
        if st.button("Review & Publish", key="qa_publish", use_container_width=True):
            st.session_state.current_page = "publish"
            st.rerun()

    # Fetch section
    st.markdown("---")
    st.markdown("### Data Source")

    config = get_config()
    jira = config.get("jira", {})

    col1, col2 = st.columns([3, 1])
    with col1:
        if jira.get("base_url"):
            st.markdown(f"""
                <div class="card">
                    <div style="display: flex; align-items: center; gap: 0.75rem;">
                        <span style="font-size: 1.5rem;">*</span>
                        <div>
                            <div style="color: var(--text-primary); font-weight: 500;">Connected to Jira</div>
                            <div style="color: var(--text-muted); font-size: 0.85rem;">{jira['base_url']}</div>
                        </div>
                    </div>
                </div>
            """, unsafe_allow_html=True)
        else:
            st.warning("Jira not configured. Go to Settings to connect.")

    with col2:
        if st.button("Fetch Tickets", use_container_width=True, disabled=not jira.get("base_url")):
            with st.spinner("Fetching from Jira..."):
                try:
                    count = fetch_backlog(verbose=False)
                    st.success(f"Fetched {count} tickets!")
                    st.rerun()
                except Exception as e:
                    st.error(str(e))


# ============ TICKETS ============

def page_tickets():
    st.markdown("""
        <div class="page-header">
            <h1 class="page-title">Tickets</h1>
            <p class="page-subtitle">Manage and track your Jira tickets</p>
        </div>
    """, unsafe_allow_html=True)

    session = SessionLocal()
    all_tickets = session.query(Ticket).order_by(Ticket.updated_at.desc()).all()

    if not all_tickets:
        st.markdown("""
            <div class="empty-state">
                <div class="empty-icon">*</div>
                <div class="empty-title">No tickets yet</div>
                <div class="empty-text">Fetch tickets from Jira to get started</div>
            </div>
        """, unsafe_allow_html=True)
        if st.button("Go to Dashboard", use_container_width=False):
            st.session_state.current_page = "dashboard"
            st.rerun()
        session.close()
        return

    # Calculate counts for each tab
    pending_tickets = []
    published_tickets = []

    for ticket in all_tickets:
        status = get_ticket_status(ticket, session)
        if status["fully_published"]:
            published_tickets.append(ticket)
        else:
            pending_tickets.append(ticket)

    # Tabs
    tab_col1, tab_col2, tab_col3, _, filter_col = st.columns([1, 1, 1, 2, 2])

    with tab_col1:
        if st.button(f"All ({len(all_tickets)})",
                    type="primary" if st.session_state.tickets_tab == "all" else "secondary",
                    use_container_width=True):
            st.session_state.tickets_tab = "all"
            st.session_state.tickets_page = 0
            st.rerun()

    with tab_col2:
        if st.button(f"Pending ({len(pending_tickets)})",
                    type="primary" if st.session_state.tickets_tab == "pending" else "secondary",
                    use_container_width=True):
            st.session_state.tickets_tab = "pending"
            st.session_state.tickets_page = 0
            st.rerun()

    with tab_col3:
        if st.button(f"Published ({len(published_tickets)})",
                    type="primary" if st.session_state.tickets_tab == "published" else "secondary",
                    use_container_width=True):
            st.session_state.tickets_tab = "published"
            st.session_state.tickets_page = 0
            st.rerun()

    with filter_col:
        search = st.text_input("Search", placeholder="Search tickets...", label_visibility="collapsed")

    # Select tickets based on tab
    if st.session_state.tickets_tab == "pending":
        tickets = pending_tickets
    elif st.session_state.tickets_tab == "published":
        tickets = published_tickets
    else:
        tickets = all_tickets

    # Apply search
    if search:
        search_lower = search.lower()
        tickets = [t for t in tickets if search_lower in t.jira_key.lower() or search_lower in (t.title or "").lower()]

    # Pagination
    if "tickets_page" not in st.session_state:
        st.session_state.tickets_page = 0

    per_page = 10
    total = len(tickets)
    total_pages = max(1, (total + per_page - 1) // per_page)
    st.session_state.tickets_page = min(st.session_state.tickets_page, total_pages - 1)

    start_idx = st.session_state.tickets_page * per_page
    end_idx = min(start_idx + per_page, total)
    page_tickets = tickets[start_idx:end_idx]

    st.caption(f"Showing {start_idx + 1}-{end_idx} of {total} tickets")

    # Render tickets
    for ticket in page_tickets:
        status = get_ticket_status(ticket, session)

        # Build status badges
        q_badge = ""
        if status["q_published"]:
            q_badge = '<span class="badge badge-success">Q Done</span>'
        elif status["q_pending"]:
            q_badge = '<span class="badge badge-warning">Q Ready</span>'
        else:
            q_badge = '<span class="badge badge-neutral">Q --</span>'

        t_badge = ""
        if status["t_published"]:
            t_badge = '<span class="badge badge-success">T Done</span>'
        elif status["t_pending"]:
            t_badge = '<span class="badge badge-warning">T Ready</span>'
        else:
            t_badge = '<span class="badge badge-neutral">T --</span>'

        with st.expander(f"**{ticket.jira_key}** - {ticket.title[:60]}{'...' if len(ticket.title or '') > 60 else ''}"):
            st.markdown(f"""
                <div style="margin-bottom: 1rem;">
                    <span class="ticket-type">{ticket.issue_type}</span>
                    {q_badge} {t_badge}
                </div>
            """, unsafe_allow_html=True)

            st.markdown(ticket.description[:500] + "..." if ticket.description and len(ticket.description) > 500 else ticket.description or "_No description_")

            # Action buttons
            col1, col2, col3 = st.columns(3)
            with col1:
                if not status["q_published"] and not status["q_pending"]:
                    if st.button("Generate Questions", key=f"gen_q_{ticket.id}", use_container_width=True):
                        st.session_state.selected_ticket = ticket.jira_key
                        st.session_state.current_page = "questions"
                        st.rerun()
            with col2:
                if not status["t_published"] and not status["t_pending"]:
                    if st.button("Generate Tests", key=f"gen_t_{ticket.id}", use_container_width=True):
                        st.session_state.selected_ticket = ticket.jira_key
                        st.session_state.current_page = "tests"
                        st.rerun()

    # Pagination controls
    if total_pages > 1:
        st.markdown("---")
        col1, col2, col3, col4, col5 = st.columns([1, 1, 2, 1, 1])

        with col1:
            if st.button("First", disabled=st.session_state.tickets_page == 0, key="t_first"):
                st.session_state.tickets_page = 0
                st.rerun()
        with col2:
            if st.button("Prev", disabled=st.session_state.tickets_page == 0, key="t_prev"):
                st.session_state.tickets_page -= 1
                st.rerun()
        with col3:
            st.markdown(f"<div style='text-align: center; padding: 0.5rem; color: var(--text-muted);'>Page {st.session_state.tickets_page + 1} of {total_pages}</div>", unsafe_allow_html=True)
        with col4:
            if st.button("Next", disabled=st.session_state.tickets_page >= total_pages - 1, key="t_next"):
                st.session_state.tickets_page += 1
                st.rerun()
        with col5:
            if st.button("Last", disabled=st.session_state.tickets_page >= total_pages - 1, key="t_last"):
                st.session_state.tickets_page = total_pages - 1
                st.rerun()

    session.close()


# ============ GENERATE PAGE (Router) ============

def page_generate():
    """Generate page - choose between questions and tests."""
    st.markdown("""
        <div class="page-header">
            <h1 class="page-title">Generate Content</h1>
            <p class="page-subtitle">Create questions and test cases for your tickets</p>
        </div>
    """, unsafe_allow_html=True)

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("""
            <div class="card" style="text-align: center; padding: 2rem;">
                <div style="font-size: 3rem; margin-bottom: 1rem;">*</div>
                <div style="font-size: 1.1rem; font-weight: 600; color: var(--text-primary); margin-bottom: 0.5rem;">
                    Refinement Questions
                </div>
                <div style="color: var(--text-muted); font-size: 0.9rem; margin-bottom: 1.5rem;">
                    Generate clarifying questions to improve ticket quality
                </div>
            </div>
        """, unsafe_allow_html=True)
        if st.button("Generate Questions", key="go_questions", use_container_width=True):
            st.session_state.current_page = "questions"
            st.rerun()

    with col2:
        st.markdown("""
            <div class="card" style="text-align: center; padding: 2rem;">
                <div style="font-size: 3rem; margin-bottom: 1rem;">*</div>
                <div style="font-size: 1.1rem; font-weight: 600; color: var(--text-primary); margin-bottom: 0.5rem;">
                    Test Cases
                </div>
                <div style="color: var(--text-muted); font-size: 0.9rem; margin-bottom: 1.5rem;">
                    Generate structured test cases for QA validation
                </div>
            </div>
        """, unsafe_allow_html=True)
        if st.button("Generate Test Cases", key="go_tests", use_container_width=True):
            st.session_state.current_page = "tests"
            st.rerun()


# ============ QUESTIONS ============

def page_questions():
    st.markdown("""
        <div class="page-header">
            <h1 class="page-title">Generate Questions</h1>
            <p class="page-subtitle">Create refinement questions for tickets</p>
        </div>
    """, unsafe_allow_html=True)

    # Back button
    if st.button("< Back to Generate", type="secondary"):
        st.session_state.current_page = "generate"
        st.rerun()

    ensure_dirs()
    session = SessionLocal()

    pending = session.query(Ticket).filter(
        Ticket.issue_type != "Spike",
        Ticket.questions_generated != True
    ).all()

    stats = get_stats()

    col1, col2 = st.columns(2)
    with col1:
        st.metric("Completed", stats["with_questions"])
    with col2:
        st.metric("Pending", len(pending))

    if not pending:
        st.success("All tickets have questions generated!")
        session.close()
        return

    # Ticket selection
    options = [f"{t.jira_key} - {t.title[:50]}..." for t in pending]
    default = options[:5] if len(options) >= 5 else options

    selected = st.multiselect("Select tickets to process", options, default=default)

    # Results containers
    if "gen_questions_results" not in st.session_state:
        st.session_state.gen_questions_results = []
    if "gen_questions_errors" not in st.session_state:
        st.session_state.gen_questions_errors = []

    if st.button("Generate Questions", disabled=not selected, type="primary"):
        st.session_state.gen_questions_results = []
        st.session_state.gen_questions_errors = []
        progress = st.progress(0)

        for i, sel in enumerate(selected):
            key = sel.split(" - ")[0]
            ticket = session.query(Ticket).filter_by(jira_key=key).first()
            if not ticket:
                continue

            progress.progress((i + 1) / len(selected), f"Processing {key}...")

            try:
                questions = generate_questions(ticket)
                if questions:
                    session.add(GeneratedContent(
                        ticket_id=ticket.id,
                        content_type='questions',
                        content=json.dumps(questions),
                        published=False
                    ))
                    ticket.questions_generated = True
                    session.commit()

                    st.session_state.gen_questions_results.append({
                        "key": key,
                        "title": ticket.title,
                        "questions": questions
                    })
            except Exception as e:
                st.session_state.gen_questions_errors.append({
                    "key": key,
                    "error": str(e)
                })

        progress.empty()

        if st.session_state.gen_questions_errors:
            st.error(f"{len(st.session_state.gen_questions_errors)} tickets failed")
        if st.session_state.gen_questions_results:
            st.success(f"Generated questions for {len(st.session_state.gen_questions_results)} tickets")

    # Show errors
    for err in st.session_state.gen_questions_errors:
        st.error(f"**{err['key']}**: {err['error']}")

    # Show results with edit capability
    if st.session_state.gen_questions_results:
        st.markdown("---")
        st.markdown("### Generated Questions")
        st.info("Edit questions below. Changes save automatically.")

        for item_idx, item in enumerate(st.session_state.gen_questions_results):
            with st.expander(f"**{item['key']}** - {item['title'][:50]}...", expanded=True):
                for q_idx, question in enumerate(item["questions"]):
                    col1, col2 = st.columns([10, 1])
                    with col1:
                        new_val = st.text_input(
                            f"Q{q_idx + 1}",
                            value=question,
                            key=f"q_{item_idx}_{q_idx}",
                            label_visibility="collapsed"
                        )
                        if new_val != question:
                            st.session_state.gen_questions_results[item_idx]["questions"][q_idx] = new_val
                            _update_questions_in_db(item["key"], st.session_state.gen_questions_results[item_idx]["questions"])
                    with col2:
                        if st.button("X", key=f"del_q_{item_idx}_{q_idx}"):
                            st.session_state.gen_questions_results[item_idx]["questions"].pop(q_idx)
                            _update_questions_in_db(item["key"], st.session_state.gen_questions_results[item_idx]["questions"])
                            st.rerun()

                # Add new question
                new_q = st.text_input("Add question", key=f"new_q_{item_idx}", placeholder="Type new question...")
                if new_q:
                    st.session_state.gen_questions_results[item_idx]["questions"].append(new_q)
                    _update_questions_in_db(item["key"], st.session_state.gen_questions_results[item_idx]["questions"])
                    st.rerun()

    session.close()


# ============ TESTS ============

def page_tests():
    st.markdown("""
        <div class="page-header">
            <h1 class="page-title">Generate Test Cases</h1>
            <p class="page-subtitle">Create structured test scenarios for tickets</p>
        </div>
    """, unsafe_allow_html=True)

    if st.button("< Back to Generate", type="secondary"):
        st.session_state.current_page = "generate"
        st.rerun()

    ensure_dirs()
    session = SessionLocal()

    pending = session.query(Ticket).filter(
        Ticket.test_cases_generated == False,
        Ticket.description != None
    ).all()

    stats = get_stats()

    col1, col2 = st.columns(2)
    with col1:
        st.metric("Completed", stats["with_tests"])
    with col2:
        st.metric("Pending", len(pending))

    if not pending:
        st.success("All tickets have test cases generated!")
        session.close()
        return

    options = [f"{t.jira_key} - {t.title[:50]}..." for t in pending]
    default = options[:5] if len(options) >= 5 else options

    selected = st.multiselect("Select tickets to process", options, default=default)

    if "gen_tests_results" not in st.session_state:
        st.session_state.gen_tests_results = []
    if "gen_tests_errors" not in st.session_state:
        st.session_state.gen_tests_errors = []

    if st.button("Generate Test Cases", disabled=not selected, type="primary"):
        st.session_state.gen_tests_results = []
        st.session_state.gen_tests_errors = []
        progress = st.progress(0)

        for i, sel in enumerate(selected):
            key = sel.split(" - ")[0]
            ticket = session.query(Ticket).filter_by(jira_key=key).first()
            if not ticket:
                continue

            progress.progress((i + 1) / len(selected), f"Processing {key}...")

            try:
                tests = generate_test_cases(ticket)
                if tests:
                    session.add(GeneratedContent(
                        ticket_id=ticket.id,
                        content_type='test_cases',
                        content=json.dumps(tests),
                        published=False
                    ))
                    ticket.test_cases_generated = True
                    session.commit()

                    st.session_state.gen_tests_results.append({
                        "key": key,
                        "title": ticket.title,
                        "tests": tests
                    })
            except Exception as e:
                st.session_state.gen_tests_errors.append({
                    "key": key,
                    "error": str(e)
                })

        progress.empty()

        if st.session_state.gen_tests_errors:
            st.error(f"{len(st.session_state.gen_tests_errors)} tickets failed")
        if st.session_state.gen_tests_results:
            st.success(f"Generated tests for {len(st.session_state.gen_tests_results)} tickets")

    for err in st.session_state.gen_tests_errors:
        st.error(f"**{err['key']}**: {err['error']}")

    if st.session_state.gen_tests_results:
        st.markdown("---")
        st.markdown("### Generated Test Cases")

        for item_idx, item in enumerate(st.session_state.gen_tests_results):
            with st.expander(f"**{item['key']}** - {item['title'][:50]}...", expanded=True):
                for tc_idx, tc in enumerate(item["tests"]):
                    if isinstance(tc, dict):
                        st.markdown(f"**TC-{tc.get('id', tc_idx + 1)}: {tc.get('title', '')}**")

                        col1, col2 = st.columns([4, 1])
                        with col1:
                            new_title = st.text_input("Title", value=tc.get("title", ""), key=f"tc_title_{item_idx}_{tc_idx}")
                            new_pre = st.text_input("PRE", value=tc.get("pre", ""), key=f"tc_pre_{item_idx}_{tc_idx}")
                            new_steps = st.text_area("STEPS", value=tc.get("steps", ""), key=f"tc_steps_{item_idx}_{tc_idx}", height=100)
                            new_expected = st.text_area("EXPECTED", value=tc.get("expected", ""), key=f"tc_exp_{item_idx}_{tc_idx}", height=80)

                        st.markdown("---")

    session.close()


# ============ PUBLISH ============

def page_publish():
    st.markdown("""
        <div class="page-header">
            <h1 class="page-title">Review & Publish</h1>
            <p class="page-subtitle">Review generated content and publish to Jira</p>
        </div>
    """, unsafe_allow_html=True)

    session = SessionLocal()

    pending = session.query(GeneratedContent).filter_by(published=False).all()

    if not pending:
        st.markdown("""
            <div class="empty-state">
                <div class="empty-icon">*</div>
                <div class="empty-title">Nothing to publish</div>
                <div class="empty-text">Generate questions or test cases first</div>
            </div>
        """, unsafe_allow_html=True)
        session.close()
        return

    st.info(f"{len(pending)} items ready for review")

    for item in pending:
        ticket = session.query(Ticket).filter_by(id=item.ticket_id).first()
        if not ticket:
            continue

        content_type = "Questions" if item.content_type == "questions" else "Test Cases"

        with st.expander(f"**{ticket.jira_key}** - {content_type}", expanded=False):
            st.markdown(f"**Ticket:** {ticket.title}")
            st.markdown("---")

            try:
                data = json.loads(item.content)

                if item.content_type == "questions":
                    for q in data:
                        st.markdown(f"- {q}")
                else:
                    for tc in data:
                        if isinstance(tc, dict):
                            st.markdown(f"**TC-{tc.get('id', '?')}:** {tc.get('title', '')}")
                            if tc.get('pre'):
                                st.markdown(f"PRE: {tc['pre']}")
                            if tc.get('steps'):
                                st.code(tc['steps'])
                            if tc.get('expected'):
                                st.markdown(f"EXPECTED: {tc['expected']}")
                            st.markdown("---")
            except:
                st.code(item.content)

            col1, col2 = st.columns(2)
            with col1:
                if st.button(f"Publish to Jira", key=f"pub_{item.id}", type="primary", use_container_width=True):
                    try:
                        data = json.loads(item.content)
                        if item.content_type == "questions":
                            adf_body = format_questions_for_jira(data)
                        else:
                            adf_body = format_test_cases_for_jira(data)

                        post_comment_to_jira(ticket.jira_key, "", adf_body=adf_body)
                        item.published = True
                        session.commit()
                        st.success(f"Published to {ticket.jira_key}!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Failed: {e}")

            with col2:
                if st.button("Skip", key=f"skip_{item.id}", type="secondary", use_container_width=True):
                    pass

    session.close()


# ============ SETTINGS ============

def page_settings():
    st.markdown("""
        <div class="page-header">
            <h1 class="page-title">Settings</h1>
            <p class="page-subtitle">Configure your connections and preferences</p>
        </div>
    """, unsafe_allow_html=True)

    config = get_config()

    # AI Provider Section
    st.markdown("""
        <div class="settings-section">
            <div class="settings-title">* AI Provider</div>
        </div>
    """, unsafe_allow_html=True)

    providers = [("openai", "OpenAI"), ("anthropic", "Anthropic"), ("google", "Google")]
    current_provider = config.get("ai_provider", "openai")

    cols = st.columns(3)
    for i, (key, name) in enumerate(providers):
        with cols[i]:
            is_active = current_provider == key
            if st.button(name, key=f"prov_{key}", type="primary" if is_active else "secondary", use_container_width=True):
                config["ai_provider"] = key
                save_config(config)
                st.rerun()

    # API Key
    selected = config.get("ai_provider", "openai")
    pconfig = config.get(selected, {})

    st.markdown("---")
    api_key = st.text_input(f"{selected.title()} API Key", value=pconfig.get("api_key", ""), type="password")

    # Models
    if selected == "openai" and api_key:
        models_data = fetch_openai_models(api_key)
        chat_models = models_data.get("chat", [])
        embed_models = models_data.get("embedding", [])

        if chat_models:
            col1, col2 = st.columns(2)
            with col1:
                current_q = pconfig.get("model_questions", chat_models[0] if chat_models else "")
                idx_q = chat_models.index(current_q) if current_q in chat_models else 0
                m_q = st.selectbox("Questions Model", chat_models, index=idx_q)

                current_t = pconfig.get("model_testcases", chat_models[0] if chat_models else "")
                idx_t = chat_models.index(current_t) if current_t in chat_models else 0
                m_t = st.selectbox("Tests Model", chat_models, index=idx_t)

            with col2:
                current_c = pconfig.get("model_chat", chat_models[0] if chat_models else "")
                idx_c = chat_models.index(current_c) if current_c in chat_models else 0
                m_c = st.selectbox("Chat Model", chat_models, index=idx_c)

                if embed_models:
                    current_e = pconfig.get("model_embedding", embed_models[0] if embed_models else "")
                    idx_e = embed_models.index(current_e) if current_e in embed_models else 0
                    m_e = st.selectbox("Embedding Model", embed_models, index=idx_e)

    # Jira Section
    st.markdown("---")
    st.markdown("### Jira Configuration")

    jira = config.get("jira", {})

    col1, col2 = st.columns(2)
    with col1:
        j_url = st.text_input("Jira URL", value=jira.get("base_url", ""), placeholder="https://your-org.atlassian.net")
        j_user = st.text_input("Email", value=jira.get("user", ""))
    with col2:
        j_token = st.text_input("API Token", value=jira.get("api_token", ""), type="password")
        j_project = st.text_input("Project Key", value=jira.get("project", ""), placeholder="PROJ")

    j_jql = st.text_area("JQL Query", value=jira.get("jql", ""), placeholder="project = PROJ ORDER BY updated DESC")

    # Test connection
    if st.button("Test Connection"):
        if all([j_url, j_user, j_token]):
            config["jira"] = {"base_url": j_url, "user": j_user, "api_token": j_token, "jql": j_jql, "project": j_project}
            save_config(config)
            success, msg = test_jira_connection()
            if success:
                st.success(msg)
            else:
                st.error(msg)
        else:
            st.warning("Fill in all Jira fields first")

    # Save button
    st.markdown("---")
    if st.button("Save All Settings", type="primary", use_container_width=True):
        config["ai_provider"] = selected
        config[selected] = {"api_key": api_key}

        if selected == "openai" and 'm_q' in dir():
            config[selected]["model_questions"] = m_q
            config[selected]["model_testcases"] = m_t
            config[selected]["model_chat"] = m_c
            if 'm_e' in dir():
                config[selected]["model_embedding"] = m_e

        config["jira"] = {
            "base_url": j_url,
            "user": j_user,
            "api_token": j_token,
            "jql": j_jql,
            "project": j_project
        }

        save_config(config)
        st.success("Settings saved!")
        st.balloons()


# ============ MAIN ============

def main():
    render_header()

    page = st.session_state.current_page

    if page == "dashboard":
        page_dashboard()
    elif page == "tickets":
        page_tickets()
    elif page == "generate":
        page_generate()
    elif page == "questions":
        page_questions()
    elif page == "tests":
        page_tests()
    elif page == "publish":
        page_publish()
    elif page == "settings":
        page_settings()
    else:
        page_dashboard()


if __name__ == "__main__":
    main()
