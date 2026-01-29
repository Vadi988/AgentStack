# AgentStack

Project layout:

```
├── app/                         # Main Application Source Code
│   ├── api/                     # API Route Handlers
│   │   └── v1/                  # Versioned API (v1 endpoints)
│   ├── core/                    # Core Application Config & Logic
│   │   ├── langgraph/           # AI Agent / LangGraph Logic
│   │   │   └── tools/           # Agent Tools (search, actions, etc.)
│   │   └── prompts/             # AI System & Agent Prompts
│   ├── models/                  # Database Models (SQLModel)
│   ├── schemas/                 # Data Validation Schemas (Pydantic)
│   ├── services/                # Business Logic Layer
│   └── utils/                   # Shared Helper Utilities
├── evals/                       # AI Evaluation Framework
│   └── metrics/                 # Evaluation Metrics & Criteria
│       └── prompts/             # LLM-as-a-Judge Prompt Definitions
├── grafana/                     # Grafana Observability Configuration
│   └── dashboards/              # Grafana Dashboards
│       └── json/                # Dashboard JSON Definitions
├── prometheus/                  # Prometheus Monitoring Configuration
├── scripts/                     # DevOps & Local Automation Scripts
│   └── rules/                   # Project Rules for Cursor
└── .github/                     # GitHub Configuration
    └── workflows/               # GitHub Actions CI/CD Workflows
```
