# Repo Realignment Note

## Why this file exists

This repository currently contains a mismatch between:

- the **actual application code** in `main`
- the **older project identity** still present in top-level docs and env examples

## What is actually in `main`

`main` is already a **Captains Prediction Companion** codebase centered on:

- Kalshi market URL intake
- event-market workflow generation
- mention-market and speech-event handling
- MCP delivery over HTTP

## What is stale

The following items still suggest an older app identity and should be treated as stale until replaced:

- `README.md`
- `.env.example`
- any leftover references to Alphapoly, Polymarket alpha detection, Chainstack, or Web3 dashboard setup

## Recommended cleanup order

1. replace `README.md` with a current product README
2. replace `.env.example` with only variables used by the current app
3. decide whether this repo remains the long-term home for Captains Prediction Companion
4. if yes, keep this repo and clean history forward
5. if no, archive this repo and move the current app to a new dedicated repo

## Current recommendation

Based on the code currently on `main`, a **repo cleanup** is enough. A brand-new repo is optional, not required.
