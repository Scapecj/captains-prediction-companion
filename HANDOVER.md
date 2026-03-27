# Handover Notes

Project: Captains Prediction Companion

Current focus:
- ChatGPT-first MCP app
- compact user-facing card
- hidden planning payload
- future dashboard expansion

Important recovery facts:
- Skills live in `/root/.codex/skills`
- The MCP server does not run a model until we wire one in
- The visible output should stay compact and UI-safe
- The hidden workflow must stay internal

Current recovery state:
- Root MCP server is the JS app in `src/server.js` on port `3000`.
- Frontend companion is the Next app on port `3001`; `/companion` renders the MCP card through `/api/mcp/analyze`.
- Mention-market alpha now runs server-side through OpenRouter before card rendering.
- Latest durable code checkpoint: `a29a390 fix: stabilize openrouter alpha responses`.

Known failure mode:
- If the companion card falls back to `needs_pricing` with `fair_yes: null` and `edge_cents: null`, first check whether the live `3000` Node process has `OPENROUTER_API_KEY` in its environment. A healthy `/healthz` response alone does not prove alpha is enabled.
- If localhost returns alpha-priced cards but the phone/public URL still shows stale data, rotate the frontend tunnel. Old `trycloudflare` links can stay attached to an outdated `3001` process.

Current volatile endpoints at last verification:
- Frontend companion: `https://florists-enters-spirituality-employee.trycloudflare.com/companion`
- Public MCP: `https://youth-scenes-olympus-gaming.trycloudflare.com/mcp`

Current expected Trump board result:
- Auto-focuses to `KXTRUMPMENTION-26MAR27-SLEE`
- `status: ready`
- `recommendation: watch`
- `fair_yes: 0.995`
- `edge_cents: 0`
