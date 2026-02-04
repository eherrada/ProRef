<div align="center">

# ProRef

### AI-Powered Product Refinement Assistant

[![Python 3.10+](https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![Streamlit](https://img.shields.io/badge/Streamlit-FF4B4B?style=for-the-badge&logo=streamlit&logoColor=white)](https://streamlit.io)
[![OpenAI](https://img.shields.io/badge/OpenAI-412991?style=for-the-badge&logo=openai&logoColor=white)](https://openai.com)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow?style=for-the-badge)](LICENSE)

**Transform your Jira backlog into actionable insights with AI-generated refinement questions and test cases.**

[Features](#-features) • [Demo](#-demo) • [Installation](#-installation) • [Usage](#-usage) • [Architecture](#-architecture)

</div>

---

## 🎯 The Problem

Product and QA teams spend countless hours in refinement sessions trying to:
- Identify edge cases and missing requirements
- Write comprehensive test cases
- Ensure tickets are implementation-ready

**ProRef automates this process** by analyzing your Jira tickets and generating intelligent questions and test cases using AI.

---

## ✨ Features

### 🔄 Jira Integration
- **Automatic sync** with your Jira backlog via REST API
- **Smart JQL builder** with project, board, and sprint selectors
- **Publish back to Jira** — generated content appears as formatted comments

### 🤖 Multi-Provider AI
- **OpenAI** (GPT-4, GPT-3.5)
- **Anthropic** (Claude 3.5 Sonnet, Haiku)
- **Google** (Gemini 1.5 Pro, Flash)

### ❓ Refinement Questions
AI analyzes each ticket to generate clarifying questions that uncover:
- Edge cases and boundary conditions
- Implicit assumptions
- Missing acceptance criteria
- Integration dependencies

### 🧪 Structured Test Cases
Generates QA-ready test cases in a structured format:
```
TC-1: User login with valid credentials
PRE: User account exists and is active
STEPS:
  1. Navigate to login page
  2. Enter valid email and password
  3. Click "Sign In"
EXPECTED:
  - User is redirected to dashboard
  - Welcome message displays user's name
```

### 🔍 Semantic Search
- **Embedding-based matching** finds related tickets
- **Cross-ticket awareness** prevents duplicate work
- **Smart suggestions** based on similarity

### 📈 Quality Scoring
AI-powered ticket quality assessment (1-10 scale):
- **Ready (8-10)** — Well-defined, implementation-ready
- **Needs Work (5-7)** — Minor improvements needed
- **Not Ready (1-4)** — Requires significant refinement

Evaluates: title clarity, description detail, acceptance criteria, edge cases

### 🏭 Domain Presets
Context-aware prompts for different industries:
- **Healthcare** — HIPAA compliance, clinical workflows, EHR integration
- **Fintech** — Transaction integrity, PCI-DSS, fraud prevention
- **E-commerce** — Inventory management, payments, promotions
- **SaaS** — Multi-tenancy, RBAC, API versioning
- **Generic** — General software development

### 📊 Workflow Dashboard
Visual progress tracking through the refinement pipeline:

```
┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐
│  FETCH   │ →  │  EMBED   │ →  │ GENERATE │ →  │ PUBLISH  │
│  ✓ 21    │    │  ✓ 21    │    │  ⏳ 15   │    │   8/21   │
└──────────┘    └──────────┘    └──────────┘    └──────────┘
```

---

## 🖥 Demo

### Web Interface
Modern dark-themed UI built with Streamlit:

- **Dashboard** — Workflow progress at a glance
- **Tickets** — Browse with filters, quality scores, and change indicators
- **Generate** — Create questions and test cases with domain presets
- **Publish** — Review and push to Jira
- **Reports** — Sprint summaries, quality breakdown, export to Excel/Markdown
- **Settings** — Configure AI providers and Jira connection

### CLI
```bash
$ proref status

ProRef Status
========================================

Tickets:
  Total:                 21
  With questions:        15
  With test cases:       12

Publication:
  Questions published:   8
  Test cases published:  6
  Pending:               13
```

---

## 🚀 Installation

### Prerequisites
- Python 3.10+
- Jira Cloud account with API access
- OpenAI/Anthropic/Google AI API key

### Quick Start

```bash
# Clone the repository
git clone https://github.com/yourusername/proref.git
cd proref

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Install dependencies
pip install -e .

# Copy and configure environment
cp .env.example .env
cp data/config.example.json data/config.json
# Edit .env or use the web UI to configure
```

### Configuration

You can configure ProRef via environment variables or the web UI:

```env
# .env
JIRA_BASE_URL=https://your-org.atlassian.net
JIRA_USER=your-email@example.com
JIRA_API_TOKEN=your-api-token
OPENAI_API_KEY=sk-your-key
```

Or launch the UI and go to **Settings**:
```bash
proref ui
```

---

## 📖 Usage

### Web Interface (Recommended)
```bash
proref ui
# Opens http://localhost:8501
```

### CLI Commands

| Command | Description |
|---------|-------------|
| `proref fetch` | Import tickets from Jira |
| `proref embed` | Generate embeddings for semantic search |
| `proref questions` | Generate refinement questions |
| `proref testcases` | Generate test cases |
| `proref publish` | Interactively publish to Jira |
| `proref status` | Show processing statistics |
| `proref chat` | Interactive Q&A about tickets |
| `proref ui` | Launch web interface |

### Workflow Example

```bash
# 1. Fetch tickets from Jira
proref fetch

# 2. Generate embeddings for semantic search
proref embed

# 3. Generate questions (with auto-publish)
proref questions --publish

# 4. Generate test cases
proref testcases --publish

# 5. Check status
proref status
```

---

## 🏗 Architecture

```
proref/
├── app/
│   ├── cli.py              # Typer CLI application
│   ├── ui.py               # Streamlit web interface
│   ├── config.py           # Configuration management
│   ├── paths.py            # Path constants
│   │
│   ├── db/
│   │   ├── model.py        # SQLAlchemy models
│   │   ├── save.py         # Data persistence + quality scores
│   │   └── embedding.py    # Vector storage
│   │
│   ├── jira/
│   │   ├── fetcher.py      # Jira API client
│   │   └── publisher.py    # ADF comment formatting
│   │
│   ├── logic/
│   │   ├── embedder.py     # Text embeddings
│   │   ├── matching.py     # Semantic search
│   │   ├── question_generator.py
│   │   ├── test_case_generator.py
│   │   ├── related_tickets.py
│   │   ├── quality_scorer.py   # AI quality assessment
│   │   ├── prompts.py          # Domain presets
│   │   └── exporter.py         # Excel/Markdown export
│   │
│   └── utils/
│       └── retry.py        # Retry decorator
│
├── data/
│   ├── proref.db           # SQLite database
│   └── config.json         # User configuration
│
├── tests/                  # 106 unit tests
└── scripts/                # Legacy CLI scripts
```

### Tech Stack

| Layer | Technology |
|-------|------------|
| **Frontend** | Streamlit with custom CSS |
| **CLI** | Typer + Rich |
| **Database** | SQLite + SQLAlchemy |
| **AI** | OpenAI / Anthropic / Google APIs |
| **Embeddings** | text-embedding-3-small (1536 dims) |
| **External API** | Jira REST API v3 |

### Data Flow

```
┌─────────┐     ┌─────────────┐     ┌──────────┐
│  Jira   │────▶│   ProRef    │────▶│  SQLite  │
│  Cloud  │◀────│   Engine    │◀────│    DB    │
└─────────┘     └─────────────┘     └──────────┘
                      │
                      ▼
               ┌─────────────┐
               │   AI APIs   │
               │ (GPT/Claude)│
               └─────────────┘
```

---

## 🧪 Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html

# Run specific test file
pytest tests/test_generators.py -v
```

**106 tests** covering:
- Configuration management
- Database models
- Question/test generation
- Jira integration
- Embedding operations
- Quality scoring
- Domain prompts
- Export functionality
- Retry logic

---

## 🛣 Roadmap

- [x] Multi-provider AI support
- [x] Structured test case format
- [x] Web UI with modern design
- [x] Jira comment publishing (ADF format)
- [x] Semantic ticket search
- [x] Ticket quality scoring
- [x] Domain-specific prompts
- [x] Export to Excel/Markdown
- [x] Sprint reports
- [x] Change detection
- [ ] Epic-level documentation generation
- [ ] Slack/Teams integration
- [ ] PDF export with styling

---

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

<div align="center">

**Built with ❤️ for QA and Product teams**

[Report Bug](https://github.com/yourusername/proref/issues) • [Request Feature](https://github.com/yourusername/proref/issues)

</div>
