# CommHub — AI Context

## Project Overview

CommHub is a local-first centralized communication hub that aggregates email and calendar from multiple providers, with AI-powered automation and rules. It runs as a standalone desktop application (Python + FastAPI backend, browser-based UI via Alpine.js).

**GitHub:** https://github.com/SyntaxNulled/CommHub
**Tech:** Python 3.13, FastAPI, SQLAlchemy (async), SQLite, Alpine.js 3, Tailwind CSS CDN, PyInstaller

---

## Architecture

```
run.py                  — Entry point: uvicorn Server (controllable), browser opens after health check, system tray
app/
├── main.py             — FastAPI app, lifespan (cron restore is fault-tolerant), static mount, seed endpoint
├── config.py           — Pydantic Settings (host, port, DB path, OAuth keys); debug defaults to False
├── database.py         — async engine, session factory, init_db()
├── models.py           — SQLAlchemy ORM models (naive-UTC datetimes via utcnow(), indexed hot columns)
├── mock_data.py        — seed_demo_data(session) — takes caller's session (test-safe)
├── tray.py             — pystray system tray (optional; degrades gracefully)
├── routers/
│   ├── health.py       — /api/health
│   ├── accounts.py     — GET /api/accounts (list connected accounts)
│   ├── emails.py       — Email CRUD + pagination + server-side search (?q=) + /unread-count + /mark-read
│   ├── calendar.py     — Calendar event CRUD (validates datetimes, end >= start)
│   ├── ai.py           — AI provider configs (secrets masked!) + draft/summarize/categorize/chat
│   └── automation.py   — Automation rules CRUD (validates cron + regex before commit)
├── ai/
│   └── providers/      — Pluggable AI providers (base, openai, anthropic, ollama, mock)
├── automation/
│   ├── scheduler.py    — APScheduler wrapper (add/remove/list cron jobs)
│   ├── engine.py       — Rules engine: trigger matching (regex-safe) + action execution
│   └── actions.py      — Action handlers (auto_reply, categorize, mark_read, star, forward)
└── static/
    ├── index.html       — SPA shell: template x-if pages, a11y (aria, labels, focus), responsive (mobile drawer)
    ├── js/app.js        — Alpine.js component (toasts, race-guarded fetches, confirm dialogs)
    └── css/style.css    — Design tokens, x-cloak, focus-visible, skeleton shimmer, reduced-motion
tests/                  — 71 pytest tests across 5 test files
```

---

## Key Conventions

### Backend
- **Async everywhere** — FastAPI async routes, SQLAlchemy async engine + sessions
- **SQLite** — single file at `~/.commhub/commhub.db`
- **Pydantic v2** — request/response models with `model_dump()` (not `.dict()`)
- **Router prefixes** — `/api/ai`, `/api/automation`, `/api/emails`, `/api/calendar`, `/api/accounts`, `/api/health`
- **DB dependency** — `async def get_db()` yields `AsyncSession`; **everything** (including seed) goes through it
- **Datetimes are naive UTC** — use `utcnow()` from `app.models`; router inputs normalized via `_parse_iso`
- **Status codes** — POST creates return 201; duplicates return 409; validation failures 400
- **Secrets never leave the API** — AI config responses expose `api_key_masked`/`has_api_key` only; empty `api_key` on update means "keep existing"
- **Single-active AI provider** — activating one deactivates the rest (enforced in `update_config`)
- **Cron + regex validated at write time** — `_validate_rule_state` in automation router; boot skips bad rows
- **OAuth not implemented** — all data is mock/demo; Google & Microsoft OAuth pending

### Frontend (Alpine.js 3)
- Single `Alpine.data('app', ...)` registration via `alpine:init` in `app.js`
- **`init()` is called automatically by Alpine — never add `x-init="init()"`** (double-listener bug)
- **Tailwind config `<script>` must come AFTER the CDN `<script src>`** — before it, `tailwind` is undefined and dark mode silently breaks
- Pages are `<template x-if>` (not `x-show`) — removed from DOM, no null-binding errors
- Keyboard shortcuts ignore modifier keys (`ctrl/meta/alt`) and inputs; j/k/r/c//, ?, Esc
- Every fetch failure surfaces a toast (`this.toast(msg, 'error')`); destructive actions go through `requestDelete()` → confirm dialog
- Email list fetches are race-guarded via `_emailReq` token; search is server-side (`?q=`) with 300ms debounce
- Mobile: sidebar is a drawer (`sidebarOpen`), detail pane replaces list below `lg:`, AI panel is full-screen below `sm:`
- `[x-cloak]` hides everything until Alpine boots

### Design System (UI/UX Pro Max — flat design, dashboard density)
- Primary `#2563EB`, accent/destructive `#DC2626`, muted `#F1F5FD`, border `#E4ECFC` (CSS vars in style.css)
- Fira Sans (UI) / Fira Code (mono) via Google Fonts
- No gradients/shadows; hover = color shift with `transition-colors duration-150`
- `cursor-pointer` on all clickables; visible `:focus-visible` rings; WCAG-AA text (gray-500 minimum on white)
- SVG icons only (no emoji); `aria-label` on all icon-only buttons

### Testing
- `pytest` with `pytest-asyncio` (strict mode)
- Test client: `httpx.AsyncClient` with `ASGITransport`
- Each test file uses `override_get_db` to inject a fresh in-memory SQLite DB per test
- 84 tests, all passing. Run: `pytest -v`

### Packaging
- PyInstaller via `commhub.spec` (includes pystray/PIL hidden imports)
- Build: `python build.py` → outputs `dist/commhub.exe`
- Static files bundled as `app/static/` → resolved at runtime via `sys._MEIPASS`

---

## Data Model

```
EmailAccount          — id, email, provider (gmail/outlook), display_name, is_active, oauth_token_json
Email                 — id, account_id*, folder, from_address, to_addresses, subject, body_text,
                        is_read, is_starred*, received_at   (* indexed; composite folder+received_at)
CalendarEvent         — id, account_id*, title, description, start_time*, end_time, is_all_day,
                        category (work/personal/meeting/important/travel/birthday/reminder/other)
Folder                — id, name, normalized_name (unique), color, icon, is_system, sort_order
AutomationRule        — id, name, trigger_type, trigger_config, action_type, action_config,
                        cron_schedule (validated), is_enabled, account_id (nullable)
AIProviderConfig      — id, provider_type (index, built-ins unique by code), display_name,
                        api_key (never in responses), base_url, model, is_active (single-active enforced),
                        temperature, max_tokens; supports multiple custom OpenAI-compatible endpoints
```

---

## Current State

### Done
- Phases 1, 3-8: scaffold, models, mock email/calendar CRUD, AI providers, automation engine, packaging, tray, pagination
- Full security/correctness hardening pass (2026-07): masked secrets, validated cron/regex/datetimes/folders,
  side-effect-free GETs, race-guarded frontend, toast feedback, confirm dialogs, a11y, responsive layout
- UI overhaul on the UI/UX Pro Max design system (flat, dense, Fira, WCAG AA)

### Blocked
- **Phase 2 (OAuth):** Google Cloud / Azure AD credentials required. User's GitHub Education Plan approval pending.
- **Email/Calendar sync:** Depends on OAuth — currently mock/seed data only

### Next up (no particular order)
- OAuth (when credentials arrive) — then real Gmail/Outlook sync
- Recurring calendar events (RRULE subset)
- Drag-and-drop email organization + right-click context menu
- Email snooze + undo send
- Auto-start on boot option
- Inno Setup / NSIS installer wrapping `dist/commhub.exe`

---

## Running & Building

```bash
# Development
python run.py                       # starts on http://127.0.0.1:8765
pytest -v                           # 84 tests

# Seed demo data
curl -X POST http://127.0.0.1:8765/api/seed

# Build standalone exe
python build.py                     # or: python -m PyInstaller --clean commhub.spec
dist\commhub.exe
```
