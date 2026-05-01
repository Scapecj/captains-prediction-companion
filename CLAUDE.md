# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

**Backend (root, port 8000):**
```bash
npm run dev          # Watch mode (node --watch src/server.js)
npm start            # Production server
npm test             # Run all tests (node:test)
```

**Frontend (`frontend/`, proxied via backend on port 3000):**
```bash
cd frontend
npm run dev          # Dev server (Next.js + custom proxy server.js)
npm run build        # Production build
npm run lint         # Prettier + ESLint --fix
npm run typecheck    # tsc --noEmit
```

**Run a single test file:**
```bash
node --test test/server.test.js
```

## Architecture

The app is a prediction market analysis companion with three surfaces:

1. **MCP endpoint** (`POST /mcp`) — ChatGPT integration via Model Context Protocol
2. **Browser dashboard** — Next.js frontend (`frontend/`) for portfolio and market cards
3. **Background pipeline** — multi-step Hermes-orchestrated market analysis

### Backend structure (`src/`)

`server.js` is the HTTP entry point. It handles routing and registers MCP tools using `@modelcontextprotocol/sdk` with Zod input schemas. Primary MCP tools:
- `app_status` — health check
- `analyze_kalshi_market_url` — core synchronous analysis tool
- Note tools (gated by `ENABLE_NOTE_TOOLS=true`): `remember_note`, `list_notes`, `search_notes`, `delete_note`

**Synchronous analysis flow:**
```
Kalshi URL → kalshiApi.js (fetch metadata) → eventMarketAlpha.js (alpha model call)
           → eventMarketContract.js (normalize output) → user_facing card
```

**Asynchronous pipeline flow (`pipelineService.js`):**
```
POST /pipeline/queue → 8-step pipeline → hermesResearch.js / hermesOracle.js
                     → sourcePackets.js (HTML parsing) → storage.js (persist JSON)
```

The output contract has two layers: `user_facing` (exposed to ChatGPT) and hidden fields (`workflow_memo`, `reasoning_framework`, `validation_details`). Cards include: source, event_domain, confidence, summary, recommendation, market_view.

### Frontend structure (`frontend/`)

Next.js App Router. The custom `server.js` proxies `/api/*` to the backend at `BACKEND_URL` (default `http://localhost:8000`). Pages: `companion`, `dashboard`, `terminal`, `positions`, `portfolios`. Design uses Tailwind + CSS variables (`--void`, `--cyan`, `--text-primary`, `--text-secondary`) with JetBrains Mono and Syne fonts.

### Key conventions

**Storage:** All JSON persistence goes through `src/storage.js` — `loadJsonFile(path, fallback)` and `writeJsonFileAtomic(path, value)` (write-to-temp + rename). Files live in `data/`.

**Hermes integration:** `hermesRuntime.js` spawns the Hermes CLI via `spawnSync`. Configurable via `HERMES_COMMAND` / `HERMES_CLI` env vars. Research and oracle instruction packets live in `prompts/`.

**Web scraping:** Prefer [Scrapling](https://github.com/D4Vinci/Scrapling) for Python-side scraping tasks (e.g. source packet enrichment via Hermes). It handles anti-bot bypass, auto-adapts to page structure changes, and supports CSS/XPath/regex selectors. Install: `pip install "scrapling[fetchers]" && scrapling install`.

**Recommendation values:** Fixed set — `buy_yes`, `buy_no`, `home`, `away`, `home_cover`, `away_cover`, `over`, `under`, `pass`.

**Event domains:** `sports`, `politics`, `macro`/`economics`, `mention`, `general`.

**Env loading:** Custom `loadDotEnv()` (no dotenv package). All config has fallback defaults.

**Operator workspace** (`agents/`, `skills/`, `channels/`, `state/`, `runbooks/`, `prompts/`): isolated from app runtime — do not import from these in `src/` or `frontend/`.

**Testing:** Uses `node:test` + `node:assert/strict`. Tests stub external dependencies (Kalshi API, Hermes, alpha engine) and use builder helpers (`buildTrumpEventPayload()`, `buildReadyCard()`, `buildNoEdgeBoard()`). Focus is on integration tests over unit tests.
