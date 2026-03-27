# Captains Prediction Companion

ChatGPT-first prediction companion for market analysis, with a remote MCP server today and room to grow into a dashboard later.

## What it gives you

- A real MCP server ChatGPT can connect to in Developer mode
- A compact user-facing card plus hidden planning payload
- A private note store behind an opt-in flag
- A clear path to expand into a dashboard without changing the core contract

## App surfaces

- `app_status`
- `event_market_plan`
- `event_market_workflow`

## Current architecture

- ChatGPT calls the MCP server
- The server classifies the market and returns structured output
- The visible payload stays compact
- The hidden payload keeps workflow, source tree, and reasoning internal

## Run locally

```bash
npm install
npm start
```

## Compatibility check

```bash
npm run check:skills
```

This confirms the starter stays isolated from `/root/.codex/skills`.

## Health check

```bash
curl http://localhost:3000/healthz
```

## Connect it to ChatGPT

1. Open ChatGPT on the web.
2. Enable `Developer mode` in `Settings -> Apps -> Advanced settings`.
3. Open `ChatGPT Apps settings`.
4. Click `Create app`.
5. Point it at your MCP server:
   - `http://localhost:3000/mcp` for local testing
   - any public HTTPS URL once deployed
6. The app will appear under `Drafts`.
7. Pick it in a conversation while in Developer mode.

## Environment variables

- `PORT`: server port, default `3000`
- `APP_NAME`: displayed app name
- `APP_VERSION`: displayed version
- `APP_DATA_FILE`: path to the notes JSON file
- `ENABLE_NOTE_TOOLS`: set to `true` to expose the note tools

## Default mode

The app starts in read-only mode by default so ChatGPT treats it as a planning tool first.

## Next step

The core analysis contract is ready to evolve from a compact planning card into a richer dashboard view without changing the MCP surface.
