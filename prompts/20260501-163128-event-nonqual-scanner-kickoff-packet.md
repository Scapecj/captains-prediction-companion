# Event Non-Qualification Scanner Kickoff Packet

purpose:
Use this as the fresh initial prompt for a planning conversation. This is not an implementation request yet. The job is to make the agents converge on the smallest useful MVP for an Event Does Not Qualify scanner for Kalshi mention markets.

starter_prompt: |
  We are designing a Captain Companion feature, not implementing it yet.

  Feature idea:
  Build an "Event Does Not Qualify" scanner for Kalshi mention markets.

  Real goal:
  Every day at 9:00 AM, scan today's Kalshi mention-market events and flag events where the underlying event may fail to qualify under Kalshi's rules.

  The scanner should look for event non-qualification risk, including:
  - event canceled
  - event postponed beyond the valid market window
  - listed speaker did not attend
  - listed speaker attended but did not speak
  - speech was private, unofficial, or not open to press/public
  - no livestream, unavailable livestream, or stream does not cover the qualifying period
  - date, time, venue, host, or event-name mismatch
  - missing, weak, delayed, or conflicting resolver source
  - no transcript, video, or qualifying source near event time
  - market rules require a live televised/streamed/open-press event and that condition may not be met

  Required product output:
  - ranked list of today's mention events with possible non-qualification risk
  - event ticker, market URL, and Event Does Not Qualify/NQE contract if one exists
  - exact Kalshi rule excerpt that controls qualification
  - confirmed facts separated from suspected risk
  - raw source URLs preserved
  - primary-source evidence first, secondary-source evidence only as locator/context
  - simple risk label: CONFIRMED_RISK, SUSPECTED_RISK, WATCH, or CLEAR
  - concise reason a trader would care
  - market-mispricing signal if the NQE price appears too low or too high, but no trade instruction
  - drafted X post for the most interesting flagged event

  Hard constraints:
  - This is a scanner, not a full research agent.
  - Do not place trades.
  - Do not give trade recommendations.
  - Do not blur confirmed facts with suspected risk.
  - Do not rely on news summaries when primary sources are available.
  - Do not assume an event qualifies just because Kalshi listed the market.
  - Keep the first version narrow, auditable, and proof-first.

  Existing repo context:
  - Repo: captains-prediction-companion
  - Operator files live under agents/, skills/, channels/, state/, runbooks/, and prompts/.
  - App/runtime code lives outside the operator folders.
  - Do not modify app code until the MVP scope is converged.
  - Keep operator prompt/runbook work separate from runtime implementation.

  Agents to respond in this order:
  1. @team-lead
  2. @researcher
  3. @code-architect
  4. @product-manager

  Optional agent:
  - Add @qa-engineer only after an MVP plan or first implementation exists and needs independent proof against real mention-market examples.

  Every agent response must use exactly this numbered format:
  1. Real problem
  2. Measurable success
  3. Real-world failure risk
  4. Contrarian or non-obvious approach
  5. Most likely wrong assumption
  6. What changes if time/cost were cut in half
  7. Whether another agent is needed; if yes, give exact role, task, and proof required

  After the agent responses, @product-manager must converge and return only:
  1. MVP
  2. Scope IN
  3. Scope OUT
  4. Risks
  5. Whether to deploy another agent
  6. Single next execution step

  Decision rules:
  - Prefer the smallest scanner that can produce one useful proof-backed ranked list.
  - Favor Kalshi event/rules data plus primary event-source verification over broad web research.
  - If evidence is missing, the scanner should label WATCH, not invent certainty.
  - If an NQE contract is present, track it explicitly.
  - If no NQE contract is present, still flag event-level qualification risk but do not imply a directly tradeable contract exists.
  - A good MVP should be testable on real mention events from today plus at least one historical known qualifying/non-qualifying example.

acceptance_criteria:
- The output is a conversation-starter prompt/task packet, not code.
- The prompt forces convergence before implementation.
- The prompt preserves the user's numbered agent-response format.
- The prompt keeps the scanner narrow and proof-first.
- The prompt explicitly separates confirmed facts from suspected risk.
- The prompt blocks trade placement and direct trade recommendations.
- The prompt names primary-source evidence and Kalshi rule excerpts as required proof.

scope_out:
- writing implementation code
- editing src/ or frontend/
- deploying a cron job
- running the scanner
- producing live picks
- writing a full Captain's Guide article

proof_requirements:
- saved prompt path
- file contains starter_prompt
- file contains the exact product constraints
- file contains the required agent response format
- file contains product-manager convergence format

exact_next_step:
Paste starter_prompt into a fresh planning conversation, run one exploration round with the named agents, then have @product-manager converge on one MVP and one next execution step.
