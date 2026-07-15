# CommHub — AI Context

## Project Overview

CommHub is a local-first centralized communication hub that aggregates email and calendar from multiple providers, with AI-powered automation and rules. It runs as a standalone desktop application (Python + FastAPI backend, browser-based UI via Alpine.js).

**GitHub:** https://github.com/SyntaxNulled/CommHub  
**Tech:** Python 3.13, FastAPI, SQLAlchemy (async), SQLite, Alpine.js 3, Tailwind CSS CDN, PyInstaller

---

## Architecture

```
run.py                  — Entry point: starts uvicorn server + opens browser
app/
├── main.py             — FastAPI app, lifespan, static mount, seed endpoint
├── config.py           — Pydantic Settings (host, port, DB path, OAuth keys)
├── database.py         — async engine, session factory, init_db()
├── models.py           — SQLAlchemy ORM models
├── mock_data.py        — seed_demo_data() — 14 emails + 8 calendar events
├── routers/
│   ├── health.py       — /api/health, / (root HTML)
│   ├── emails.py       — Email CRUD (list/get/send/draft/toggle-star/delete)
│   ├── calendar.py     — Calendar event CRUD (list/create/update/delete)
│   ├── ai.py           — AI provider configs + draft/summarize/categorize/chat
│   └── automation.py   — Automation rules CRUD + scheduler endpoints
├── ai/
│   └── providers/      — Pluggable AI providers (base, openai, anthropic, ollama, mock)
├── automation/
│   ├── scheduler.py    — APScheduler wrapper (add/remove/list cron jobs)
│   ├── engine.py       — Rules engine: trigger matching + action execution
│   └── actions.py      — Action handlers (auto_reply, categorize, mark_read, star, forward)
└── static/
    ├── index.html       — SPA shell with Tailwind + Alpine.js templates
    ├── js/app.js        — Alpine.js data + methods (all frontend logic)
    └── css/style.css    — Minimal custom CSS overrides
tests/                  — 59 pytest tests across 5 test files
```

---

## Key Conventions

### Backend
- **Async everywhere** — FastAPI async routes, SQLAlchemy async engine + sessions
- **SQLite** — single file at `~/.commhub/commhub.db`
- **Pydantic v2** — request/response models with `model_dump()` (not `.dict()`)
- **Router prefix** — `/api/ai`, `/api/automation`, `/api/emails`, `/api/calendar`, `/api/health`
- **DB dependency** — `async def get_db()` yields `AsyncSession`
- **OAuth not implemented** — all data is mock/demo; Google & Microsoft OAuth pending

### Frontend (Alpine.js 3)
- Single `Alpine.data('app', ...)` registration via `alpine:init` event in `app.js`
- All state (page, emails, events, rules, AI configs) lives in one component
- CDN-loaded: Alpine.js 3.14, Tailwind CSS (JIT CDN)
- Script loading order matters: `app.js` must load **before** Alpine's CDN script so the `alpine:init` listener is registered in time
- Navigation via `navigate(pageId)` — sets `this.page`, drives `x-show` sections
- All modals (compose, event form, AI panel) are inline `x-show` overlays

### Testing
- `pytest` with `pytest-asyncio` (strict mode)
- Test client: `httpx.AsyncClient` with `ASGITransport`
- Each test file uses `override_get_db` to inject a fresh in-memory SQLite DB per test
- 59 tests, all passing. Run: `pytest -v`

### Packaging
- PyInstaller via `commhub.spec`
- Build: `python build.py` → outputs `dist/commhub.exe`
- Static files bundled as `app/static/` → resolved at runtime via `sys._MEIPASS`
- Frozen mode detected via `getattr(sys, 'frozen', False)`

---

## Data Model

```
EmailAccount          — id, email, provider (gmail/outlook), is_authenticated
Email                 — id, account_id, folder, from_address, to_addresses, subject, body_text, is_read, is_starred, received_at
CalendarEvent         — id, account_id, title, description, start_time, end_time, is_all_day
AutomationRule        — id, name, trigger_type, trigger_config, action_type, action_config, cron_schedule, is_enabled, account_id
AIProviderConfig      — id, provider_type, display_name, api_key, base_url, model, is_active, temperature, max_tokens
```

---

## Current State

### Done
- Phase 1: FastAPI scaffold, SQLAlchemy models, Alpine.js SPA shell, pytest suite, git
- Phase 6: Pluggable AI providers (OpenAI/Anthropic/Ollama + mock), CRUD config API, AI assistant slideout UI
- Phase 7: APScheduler, rules engine, 5 action handlers, CRUD + toggle API + UI
- Phases 3-5 (mock): Email CRUD, Calendar CRUD, inbox UI, compose modal, week-calendar grid, seed endpoint
- Phase 8: PyInstaller packaging — `build.py` + `commhub.spec`, icon, frozen-mode path resolution
- **Fixes:** emoji UnicodeEncodeError on Windows cp1252, settings page `app.js` not loaded

### Blocked
- **Phase 2 (OAuth):** Google Cloud / Azure AD credentials required for real Gmail/Outlook sync. User's GitHub Education Plan approval pending.
- **Email/Calendar sync:** Depends on OAuth — currently using mock/seed data only

### Next up (no particular order)
- System tray icon (pystray) — minimize to tray, background running
- Fix 62 `utcnow()` deprecation warnings → `now(datetime.UTC)`
- UX polish: search/filter, dark mode, keyboard shortcuts, month calendar view
- Auto-start on boot option
- Inno Setup / NSIS installer wrapping `dist/commhub.exe`

---

## Running & Building

```bash
# Development
python run.py                       # starts on http://127.0.0.1:8765
pytest -v                           # 59 tests

# Seed demo data
curl -X POST http://127.0.0.1:8765/api/seed

# Build standalone exe
python build_icon.py                # generates app.ico
python -m PyInstaller --clean commhub.spec
dist\commhub.exe

# Or one-step build:
python build.py
```
