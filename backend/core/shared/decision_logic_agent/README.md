# Decision Logic Agent

`decision_logic_agent` is a shared deterministic layer that sits above domain apps and below execution.

It owns:

- implied probability normalization
- fair value comparison
- YES / NO edge calculation
- spread and slippage checks
- maker vs taker guidance
- microprice calculation
- inventory-cap checks
- Kelly and reduced-Kelly sizing
- effective-resolution versus official-settlement handling
- trade posture selection

It does not own:

- scraping
- transcript collection
- sports stat ingestion
- event linking
- final order placement

## Package layout

- `models.py` — strict request/response schemas
- `calculations.py` — pure market math
- `market_state.py` — market-state and settlement-state classification
- `sizing.py` — Kelly and reduced-Kelly sizing helpers
- `decision_engine.py` — deterministic orchestration and policy thresholds

## Core formulas

- normalized implied probability:
  - `p_yes_norm = yes_price / (yes_price + no_price)`
- midpoint:
  - `(bid + ask) / 2`
- microprice:
  - `((ask * bid_size) + (bid * ask_size)) / (bid_size + ask_size)`
- YES expected value:
  - `fair_yes_probability - execution_price`
- binary Kelly:
  - `(fair_probability - execution_price) / (1 - execution_price)`

All policy thresholds are kept in `DecisionPolicy`.
