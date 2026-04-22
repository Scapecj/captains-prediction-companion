import { buildEventMarketPlanSummary } from './eventMarketTool.js';

function isObject(value) {
  return Boolean(value) && typeof value === 'object' && !Array.isArray(value);
}

function normalizeChildContracts(value) {
  if (!Array.isArray(value)) return [];
  return value.map(contract => ({
    ticker: contract?.ticker ?? contract?.market_ticker ?? null,
    label: contract?.label ?? null,
    yes_bid: contract?.yes_bid ?? contract?.market_yes_bid ?? null,
    yes_ask: contract?.yes_ask ?? contract?.market_yes_ask ?? null,
    last_price: contract?.last_price ?? null,
    source_url: contract?.source_url ?? null,
    transcript_excerpt: contract?.transcript_excerpt ?? null,
    phrase_found: contract?.phrase_found ?? null,
    evidence: Array.isArray(contract?.evidence) ? contract.evidence.filter(item => typeof item === 'string') : [],
  }));
}

function normalizeReasoningChain(value, fallback = []) {
  if (!Array.isArray(value)) return fallback;
  const cleaned = value
    .filter(item => typeof item === 'string')
    .map(item => item.trim())
    .filter(Boolean);
  return cleaned.length > 0 ? cleaned : fallback;
}

function hasActionableBoard(result) {
  const recommendation = String(result?.board_recommendation ?? result?.summary?.recommendation ?? '').trim().toLowerCase();
  return recommendation === 'buy_yes' || recommendation === 'buy_no';
}

export function runHermesOracle(researchResult = {}, input = {}, options = {}) {
  const summary = buildEventMarketPlanSummary(researchResult);
  const childContracts = normalizeChildContracts(researchResult?.child_contracts ?? summary?.market_view?.available_contracts ?? []);
  const boardRecommendation =
    researchResult?.board_recommendation ?? summary?.summary?.recommendation ?? 'watch';
  const boardConfidence = researchResult?.board_confidence ?? summary?.confidence ?? 'low';

  const board = {
    board_url: researchResult?.board_url ?? summary?.source?.url ?? input.url ?? null,
    board_headline: researchResult?.board_headline ?? summary?.summary?.headline ?? 'Hermes board analysis',
    board_recommendation: boardRecommendation,
    board_confidence: boardConfidence,
    child_contracts: childContracts,
    board_no_edge_reason_code: researchResult?.board_no_edge_reason_code ?? null,
    board_no_edge_reason: researchResult?.board_no_edge_reason ?? null,
    official_source_url: researchResult?.official_source_url ?? null,
    official_source_type: researchResult?.official_source_type ?? null,
    transcript_excerpt: researchResult?.transcript_excerpt ?? null,
    research_summary: researchResult?.research_summary ?? summary?.summary?.one_line_reason ?? null,
    evidence_strength: researchResult?.evidence_strength ?? null,
    source_quality: researchResult?.source_quality ?? null,
    source_packet_kind: researchResult?.source_packet_kind ?? null,
    event_format: researchResult?.event_format ?? null,
    speaker_type: researchResult?.speaker_type ?? null,
    timing_relevance: researchResult?.timing_relevance ?? null,
    why_valid_under_kalshi_rules: researchResult?.why_valid_under_kalshi_rules ?? null,
    unresolved_gaps: Array.isArray(researchResult?.unresolved_gaps) ? researchResult.unresolved_gaps : [],
    edge_type:
      researchResult?.edge_type ??
      (boardRecommendation === 'buy_yes' || boardRecommendation === 'buy_no' ? 'information' : 'none'),
    catalyst: researchResult?.catalyst ?? null,
    reasoning_chain: normalizeReasoningChain(researchResult?.reasoning_chain, []),
    invalidation_condition: researchResult?.invalidation_condition ?? null,
    time_sensitivity: researchResult?.time_sensitivity ?? null,
    exact_phrase_status: researchResult?.exact_phrase_status ?? null,
    official_source_candidates: Array.isArray(researchResult?.official_source_candidates) ? researchResult.official_source_candidates : [],
    user_facing: summary,
  };

  if (!hasActionableBoard(board)) {
    board.board_no_edge_reason_code =
      board.board_no_edge_reason_code ?? 'manual_classification_required';
    board.board_no_edge_reason =
      board.board_no_edge_reason ??
      'The board stayed on watch because Hermes returned no actionable edge with verifiable official-source evidence.';
  }

  return board;
}
