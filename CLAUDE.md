# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

Factory Inventory Management System — a Claude Code workshop demo. Vue 3 frontend, Python FastAPI backend, in-memory mock data loaded from JSON (no database). `client/CLAUDE.md` and `server/CLAUDE.md` hold per-side conventions.

> ⚠️ **This repository and any fork you create are PUBLIC.** Do not commit credentials, internal hostnames, or private registry URLs. `client/.npmrc` pins the public npm registry and `client/package-lock.json` is gitignored to prevent locally-configured registries from leaking into commits — leave both in place.

## Critical Tool Usage Rules

### Subagents
Use the Agent tool with these subagents (defined in `.claude/agents/`):

- **vue-expert**: Vue 3 frontend features, UI components, styling, client-side functionality
  - **MANDATORY RULE: ANY time you need to create or significantly modify a .vue file, you MUST delegate to vue-expert**
- **code-reviewer**: after writing significant code
- **security-auditor**: security review of changes
- **Explore**: understanding codebase structure, searching for patterns

### Skills
- **backend-api-test**: use when writing or modifying tests in `tests/backend/` (pytest + FastAPI TestClient)

### MCP Tools (`.mcp.json`)
- **ALWAYS use GitHub MCP tools** (`mcp__github__*`) for ALL GitHub operations
  - Exception: local branches — use `git checkout -b` instead of `mcp__github__create_branch`
- **ALWAYS use Playwright MCP tools** (`mcp__playwright__*`) for browser testing against `http://localhost:3000` (frontend) and `http://localhost:8001` (API)

## Commands

```bash
./scripts/start.sh            # start both servers (installs deps if missing); macOS/Linux only
./scripts/stop.sh

cd server && uv sync && uv run python main.py   # backend → :8001, docs at /docs
cd client && npm install && npm run dev         # frontend → :3000
cd client && npm run build                      # production build → client/dist/
```

**Backend tests must be run from `server/`** — the pytest deps live in the server's uv environment; `cd tests && uv run pytest` (as `tests/README.md` says) fails with `No module named 'fastapi'`:

```bash
cd server && uv run pytest ../tests                                    # all tests
cd server && uv run pytest ../tests/backend/test_inventory.py::TestInventoryEndpoints::test_get_all_inventory
```

There is no frontend test suite, linter, or type checker configured.

## Architecture

**Backend** is a single file, `server/main.py`. `server/mock_data.py` loads every `server/data/*.json` file once at import time into module-level lists; endpoints filter those lists in memory and validate through Pydantic `response_model`s. Consequences:
- Editing a JSON file requires a server restart; changing a JSON shape requires updating the matching Pydantic model.
- `server/generate_data.py` regenerates **only** `data/orders.json` (random data, overwrites it) and must be run from `server/`.

**Filtering** flows end to end:
1. `client/src/composables/useFilters.js` holds filter state as **module-level refs**, so every view shares one singleton filter state (Time Period, Warehouse, Category, Order Status).
2. `getCurrentFilters()` maps the period to a `month` param; `client/src/api.js` drops any value equal to `'all'`.
3. In `main.py`, `apply_filters()` handles warehouse (exact match), category and status (case-insensitive); `filter_by_month()` substring-matches `order_date` and accepts either `YYYY-MM` or a quarter key from `QUARTER_MAP` (2025 only).

Which endpoints accept which filters:
- `GET /api/inventory` — warehouse, category (no time dimension, so no month)
- `GET /api/orders`, `GET /api/dashboard/summary` — warehouse, category, status, month
- `GET /api/inventory/{id}`, `/api/orders/{id}` — 404 if missing
- `GET`/`POST /api/restock-orders` — restock orders kept in memory (lost on restart); prices and lead times come from `demand_forecasts.json`
- `GET /api/demand`, `/api/backlog`, `/api/spending/{summary,monthly,categories,transactions}`, `/api/reports/{quarterly,monthly-trends}` — no filters. `/api/backlog` derives `has_purchase_order` from `purchase_orders.json`.

**Frontend**: views are registered in `client/src/main.js` (vue-router). Raw API data goes in refs (`allOrders`, `inventoryItems`), derived data in computed properties. Most views call `api.js`, but `Reports.vue` calls axios directly with a hardcoded URL.

**i18n / currency**: `useI18n.js` provides `t('dotted.key')` with `en`/`ja` locales in `client/src/locales/` (falls back to English, persisted in localStorage). Switching to `ja` also switches currency to JPY; `utils/currency.js` converts at a fixed `USD_TO_JPY = 150`. Add new UI strings to both locale files.

### Known gaps
- `api.js` calls `/api/tasks` (GET/POST/PATCH/DELETE, used by `App.vue`) and `/api/purchase-orders` (POST, GET by backlog item), but `main.py` implements **neither**; those calls 404.
- `views/Backlog.vue` exists but has no route in `main.js`.
- `tests/README.md` lists a `test_orders.py` and 51 tests; the file does not exist and the suite has 50 tests.

## Conventions / Common Issues
1. Use stable keys in `v-for` (`sku`, `month`, `id`), never `index`.
2. Validate dates before `.getMonth()` calls.
3. Revenue goals: $800K/month for a single month, $9.6M YTD across all months.
4. Design: slate/gray palette (#0f172a, #64748b, #e2e8f0), green/blue/yellow/red for status, custom SVG charts, CSS Grid layouts, global styles in `client/src/App.vue`. No emojis in the UI.
