"""Prompt templates and domain presets for AI generation."""

# Domain presets
DOMAIN_PRESETS = {
    "generic": {
        "name": "Generic Software",
        "description": "General software development projects",
        "questions_prompt": """You are a QA assistant helping refine software requirements.

Analyze this Jira ticket and generate 3-5 clarifying questions that will help uncover:
- Edge cases and boundary conditions
- Implicit assumptions that need validation
- Missing acceptance criteria
- Integration dependencies or impacts
- Potential error scenarios

TICKET:
Title: {title}
Type: {issue_type}
Description:
{description}

Return the questions as a bullet list. Be specific and actionable.
Do not include explanations - only the questions.""",

        "testcases_prompt": """You are a QA engineer creating test cases for software features.

Create 3-5 structured test cases for this ticket:

TICKET:
Title: {title}
Type: {issue_type}
Description:
{description}

For each test case, use this EXACT format:

TC-[number]: [descriptive title]
PRE: [preconditions required]
STEPS:
1. [step 1]
2. [step 2]
...
EXPECTED:
- [expected result 1]
- [expected result 2]

Include both happy path and edge cases. Be specific and testable."""
    },

    "healthcare": {
        "name": "Healthcare / MedTech",
        "description": "Healthcare applications with compliance requirements",
        "questions_prompt": """You are a QA specialist for healthcare software with expertise in HIPAA compliance and clinical workflows.

Analyze this Jira ticket and generate 3-5 critical questions focusing on:
- Patient data privacy and HIPAA compliance
- Clinical workflow impacts and safety considerations
- Integration with EHR/EMR systems
- Audit trail and logging requirements
- Error handling for critical medical data
- Accessibility for healthcare providers

TICKET:
Title: {title}
Type: {issue_type}
Description:
{description}

Return questions as a bullet list. Prioritize patient safety and compliance concerns.
Do not include explanations - only the questions.""",

        "testcases_prompt": """You are a QA engineer specializing in healthcare software testing.

Create 3-5 test cases for this ticket with focus on:
- HIPAA compliance verification
- Patient data handling
- Clinical workflow accuracy
- Audit logging verification
- Error recovery scenarios

TICKET:
Title: {title}
Type: {issue_type}
Description:
{description}

For each test case, use this EXACT format:

TC-[number]: [descriptive title]
PRE: [preconditions including user roles and patient data state]
STEPS:
1. [step 1]
2. [step 2]
...
EXPECTED:
- [expected result including compliance checks]

Include data privacy and safety-critical scenarios."""
    },

    "fintech": {
        "name": "Fintech / Banking",
        "description": "Financial applications with security and compliance needs",
        "questions_prompt": """You are a QA specialist for financial software with expertise in security and regulatory compliance.

Analyze this Jira ticket and generate 3-5 critical questions focusing on:
- Transaction integrity and data consistency
- Security vulnerabilities and fraud prevention
- Regulatory compliance (PCI-DSS, SOX, etc.)
- Audit trail requirements
- Concurrency and race conditions in financial operations
- Error handling and rollback scenarios

TICKET:
Title: {title}
Type: {issue_type}
Description:
{description}

Return questions as a bullet list. Prioritize security and financial accuracy.
Do not include explanations - only the questions.""",

        "testcases_prompt": """You are a QA engineer specializing in financial software testing.

Create 3-5 test cases for this ticket with focus on:
- Transaction accuracy and consistency
- Security and fraud prevention
- Compliance verification
- Concurrent operation handling
- Audit trail validation

TICKET:
Title: {title}
Type: {issue_type}
Description:
{description}

For each test case, use this EXACT format:

TC-[number]: [descriptive title]
PRE: [preconditions including account states and balances]
STEPS:
1. [step 1]
2. [step 2]
...
EXPECTED:
- [expected result including exact amounts and states]

Include edge cases for financial calculations and security scenarios."""
    },

    "ecommerce": {
        "name": "E-commerce / Retail",
        "description": "Online retail and shopping platforms",
        "questions_prompt": """You are a QA specialist for e-commerce platforms.

Analyze this Jira ticket and generate 3-5 clarifying questions focusing on:
- Inventory management and stock synchronization
- Payment processing and checkout flow
- User experience across devices
- Performance under high traffic
- Order fulfillment integration
- Promotional rules and pricing logic

TICKET:
Title: {title}
Type: {issue_type}
Description:
{description}

Return questions as a bullet list. Focus on customer experience and business rules.
Do not include explanations - only the questions.""",

        "testcases_prompt": """You are a QA engineer specializing in e-commerce testing.

Create 3-5 test cases for this ticket with focus on:
- Shopping cart and checkout flow
- Payment processing scenarios
- Inventory updates
- Promotional/discount rules
- Cross-device compatibility

TICKET:
Title: {title}
Type: {issue_type}
Description:
{description}

For each test case, use this EXACT format:

TC-[number]: [descriptive title]
PRE: [preconditions including cart state, user type, inventory levels]
STEPS:
1. [step 1]
2. [step 2]
...
EXPECTED:
- [expected result including prices, inventory changes]

Include edge cases for pricing, promotions, and inventory scenarios."""
    },

    "saas": {
        "name": "SaaS / B2B Platform",
        "description": "Multi-tenant SaaS applications",
        "questions_prompt": """You are a QA specialist for multi-tenant SaaS platforms.

Analyze this Jira ticket and generate 3-5 clarifying questions focusing on:
- Multi-tenancy and data isolation
- Role-based access control (RBAC)
- Subscription and billing impacts
- API compatibility and versioning
- Performance at scale
- Integration with third-party services

TICKET:
Title: {title}
Type: {issue_type}
Description:
{description}

Return questions as a bullet list. Focus on tenant isolation and enterprise needs.
Do not include explanations - only the questions.""",

        "testcases_prompt": """You are a QA engineer specializing in SaaS platform testing.

Create 3-5 test cases for this ticket with focus on:
- Tenant data isolation
- Permission and role verification
- API behavior and responses
- Subscription tier limitations
- Performance and scalability

TICKET:
Title: {title}
Type: {issue_type}
Description:
{description}

For each test case, use this EXACT format:

TC-[number]: [descriptive title]
PRE: [preconditions including tenant, user role, subscription tier]
STEPS:
1. [step 1]
2. [step 2]
...
EXPECTED:
- [expected result including access control verification]

Include cross-tenant isolation and permission boundary tests."""
    }
}


def get_domain_list() -> list[dict]:
    """Get list of available domains for selection."""
    return [
        {"key": key, "name": preset["name"], "description": preset["description"]}
        for key, preset in DOMAIN_PRESETS.items()
    ]


def get_prompt(domain: str, prompt_type: str, ticket_data: dict) -> str:
    """Get formatted prompt for a domain and type.

    Args:
        domain: Domain key (e.g., 'healthcare', 'fintech')
        prompt_type: 'questions' or 'testcases'
        ticket_data: Dict with 'title', 'description', 'issue_type'

    Returns:
        Formatted prompt string
    """
    preset = DOMAIN_PRESETS.get(domain, DOMAIN_PRESETS["generic"])
    prompt_key = f"{prompt_type}_prompt"
    template = preset.get(prompt_key, DOMAIN_PRESETS["generic"][prompt_key])

    return template.format(
        title=ticket_data.get("title", "No title"),
        description=ticket_data.get("description", "No description"),
        issue_type=ticket_data.get("issue_type", "Unknown")
    )


def get_custom_prompt(custom_template: str, ticket_data: dict) -> str:
    """Format a custom prompt template with ticket data.

    Available placeholders: {title}, {description}, {issue_type}
    """
    return custom_template.format(
        title=ticket_data.get("title", "No title"),
        description=ticket_data.get("description", "No description"),
        issue_type=ticket_data.get("issue_type", "Unknown")
    )
