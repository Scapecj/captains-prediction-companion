# Hermes Kalshi Mention Research Packet

objective:
Run a Hermes-backed research pass for a single Kalshi mention board and return a board-first evidence record.

scope_in:
- one Kalshi board URL
- one selected child contract at a time
- official source discovery
- transcript or video verification
- proof-backed recommendation

scope_out:
- UI changes
- pricing-only analysis without evidence
- social/news commentary as settlement proof
- guessing when the official source is missing

controller_rules:
- Treat the Kalshi board, rules, and official source as the source of truth.
- If the URL is a board URL, identify the loaded child contracts before selecting one contract to inspect.
- Do not finalize a recommendation until the researcher returns direct source proof.
- Do not accept summaries without an official source URL and exact excerpt.
- One exploration round only.
- Reject any answer that is not backed by file evidence or source evidence.
- If there is no real research packet, automatically downgrade to pass or watch.
- No pick without evidence.

researcher_rules:
- Find the official Kalshi board/rules page first.
- Identify the exact child contract ticker and phrase being tested.
- Locate the controlling official source named by the rules.
- Extract the exact transcript/video excerpt that supports or falsifies the phrase.
- Note speaker-scope risk, excluded-segment risk, and any rule ambiguity.
- Use secondary sources only to locate the official source, never as settlement proof.
- Return facts first, no fake certainty, no market commentary masquerading as evidence.
- Do not return generic statements like no evidence, unclear, insufficient information, or weak signal unless expanded into concrete source-backed detail.
- Every result must include exact official source URL, source type, exact excerpt or exact statement that the phrase was not found, and why that source is valid under Kalshi rules.
- For event markets, identify event format, speaker type, timing relevance, and whether the source is transcript, video, filing, calendar release, or macro print.
- Return source_quality and evidence_strength based on source quality, not vibes.

oracle_rules:
- Do not output pick/watch/pass from price math alone.
- reasoning_chain must include at least one of: historical pattern, behavioral tendency, timing/catalyst insight, market-structure mismatch.
- reasoning_chain must compare implied market probability, model/fair probability, and why the difference exists.
- Must return edge_type, catalyst, reasoning_chain, invalidation_condition, and time_sensitivity.
- If no real research packet exists, downgrade to pass/watch automatically.
- No pick without evidence.
- Good: "This is a live earnings-call board, management usually covers vehicle roadmap in Q&A, and the contract is priced below what that format implies."
- Bad: "No strong evidence yet."

required_output:
{
  "board_url": "string",
  "board_headline": "string",
  "board_recommendation": "buy_yes|buy_no|pass|watch",
  "board_confidence": "low|medium|high",
  "child_contracts": [
    {
      "ticker": "string",
      "label": "string",
      "yes_bid": "number|null",
      "yes_ask": "number|null",
      "last_price": "number|null",
      "source_url": "string|null",
      "transcript_excerpt": "string|null",
      "phrase_found": "true|false|null",
      "evidence": ["string"]
    }
  ],
  "board_no_edge_reason_code": "string|null",
  "board_no_edge_reason": "string|null"
}

proof_requirements:
- official source URL
- exact transcript/video excerpt or a clear statement that the phrase was not found
- selected child contract ticker
- the board URL used for research
- file paths if the result is written back into the repo

execution_notes:
- If the board contains multiple child contracts, the controller must choose one contract to drill into before the final report.
- If evidence is incomplete, the result should be pass or watch rather than a fabricated edge.
- Keep the report board-first and nest child contracts beneath the board record.
