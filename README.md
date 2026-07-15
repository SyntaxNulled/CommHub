# CommHub

**Local-first centralized communication hub** — Aggregates email and calendar from multiple providers with AI-powered automation and rules.

> ⚠️ **Status:** OAuth integration (Gmail/Outlook) is pending GitHub Education Plan approval. Currently runs with mock/seed data for demo and testing.

---

## Quick Start

### Prerequisites
- Python 3.13+
- Required packages listed in `requirements.txt`

### Run (development)
```bash
python run.py
```
Then open http://127.0.0.1:8765

### Seed demo data
```bash
curl -X POST http://127.0.0.1:8765/api/seed
```
This creates 14 sample emails and 8 calendar events.

### Run tests
```bash
pytest -v    # 59 tests
```

### Build standalone executable
```bash
python build.py
dist\commhub.exe
```

---

## Features

- **Multi-provider email** — Inbox, Sent, Drafts, Starred folders (currently mock data)
- **Calendar** — Week grid view, create/edit/delete events
- **AI Assistant** — Draft replies, summarize, categorize, chat (pluggable: OpenAI, Anthropic, Ollama, mock)
- **Automation Rules** — Trigger on new email, keyword match, or cron schedule; auto-reply, categorize, mark read, star, forward
- **Settings** — AI provider configuration, demo data seeding

---

## Tech Stack

| Layer          | Technology                                                       |
|----------------|------------------------------------------------------------------|
| Backend        | Python 3.13, FastAPI, Uvicorn                                    |
| Database       | SQLite via SQLAlchemy (async)                                    |
| Frontend       | Alpine.js 3, Tailwind CSS (CDN), vanilla JS                      |
| AI Providers   | OpenAI, Anthropic, Ollama, Mock (pluggable)                      |
| Automation     | APScheduler for cron-based rules                                 |
| Packaging      | PyInstaller — single `commhub.exe` (~36 MB)                      |

---

## Project Structure

```
CommHub/
├── run.py                  # Entry point — starts server + opens browser
├── build.py                # Build standalone executable
├── app/
│   ├── main.py             # FastAPI app, lifespan, static mount
│   ├── config.py           # Settings (host, port, DB path, OAuth keys)
│   ├── database.py         # Async SQLAlchemy engine + session factory
│   ├── models.py           # ORM models (Email, CalendarEvent, AutomationRule, etc.)
│   ├── mock_data.py        # Seed demo data function
│   ├── routers/
│   │   ├── health.py       # Health check, root HTML
│   │   ├── emails.py       # Email CRUD
│   │   ├── calendar.py     # Calendar event CRUD
│   │   ├── ai.py           # AI provider config + endpoints
│   │   └── automation.py   # Automation rules + scheduler
│   ├── ai/providers/       # Pluggable AI providers
│   ├── automation/         # Scheduler, engine, action handlers
│   └── static/             # Frontend (HTML, JS, CSS)
├── tests/                  # pytest suite (59 tests)
├── commhub.spec            # PyInstaller spec
└── AI_CONTEXT.md           # Onboarding for AI assistants
```

---

## Branches & Workflow

`master` is protected — all changes require a pull request with approval.

1. Work is done on feature branches
2. A PR is created for review
3. After approval, it's merged to `master`

---

## License

MIT
