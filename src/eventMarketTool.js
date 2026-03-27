import { buildEventMarketContract } from './eventMarketContract.js';
import { enrichEventMarketInput } from './kalshiApi.js';
import { enrichEventMarketAlpha } from './eventMarketAlpha.js';

export async function buildEventMarketPlan(input = {}, options = {}) {
  const enrichedInput = await enrichEventMarketInput(input, options);
  const alphaInput = await enrichEventMarketAlpha(enrichedInput, options);
  return buildEventMarketContract(alphaInput);
}

function getAvailableContracts(summary = {}) {
  const contracts = summary?.market_view?.available_contracts;
  return Array.isArray(contracts) ? contracts : [];
}

function getActiveMarketTicker(summary = {}) {
  const ticker = summary?.market_view?.trade_view?.market_ticker;
  return typeof ticker === 'string' && ticker.trim() ? ticker.trim() : null;
}

function deriveContractUrl(baseUrl, marketTicker) {
  if (!baseUrl || !marketTicker) return null;

  try {
    const parsed = new URL(baseUrl);
    const segments = parsed.pathname.split('/').filter(Boolean);
    if (segments.length === 0) return null;
    segments[segments.length - 1] = marketTicker;
    parsed.pathname = `/${segments.join('/')}`;
    return parsed.toString();
  } catch {
    return null;
  }
}

export async function buildFocusedKalshiMarketPlan(input = {}, options = {}) {
  const initialResult = await buildEventMarketPlan(input, options);
  const initialSummary = buildEventMarketPlanSummary(initialResult);
  const availableContracts = getAvailableContracts(initialSummary);

  if (getActiveMarketTicker(initialSummary) || availableContracts.length === 0) {
    return initialResult;
  }

  const primaryContract = availableContracts[0];
  const contractUrl = deriveContractUrl(
    initialSummary?.source?.url ?? input.url ?? null,
    primaryContract?.market_ticker ?? null
  );

  if (!contractUrl) {
    return initialResult;
  }

  return buildEventMarketPlan(
    {
      ...input,
      url: contractUrl,
    },
    options
  );
}

export function buildEventMarketPlanSummary(result = {}) {
  return result.user_facing ?? {
    source: {
      platform: 'Kalshi',
      url: null,
      market_id: null,
    },
    event_domain: 'general',
    event_type: 'general',
    market_type: 'general',
    status: 'insufficient_context',
    confidence: 'low',
    summary: {
      headline: 'The market needs more detail before the app can build a card.',
      recommendation: 'pass',
      one_line_reason:
        'The planner did not receive enough market context to classify the event cleanly.',
    },
    next_action: 'confirm_event_context',
    context: {},
    market_view: {},
  };
}
