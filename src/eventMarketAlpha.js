import { resolveOpenRouterModel } from './modelDefaults.js';

const OPENROUTER_URL = 'https://openrouter.ai/api/v1/chat/completions';
const EDGE_THRESHOLD_CENTS = 3;
const ALPHA_SYSTEM_PROMPT =
  'You are the alpha stage for a prediction-market companion. Treat mention markets as resolution-constrained language problems. Use only the provided market data. Do not assume extra facts. Respect the exact phrase, exact speaker, exact event boundary, and exact source constraints from the rules summary. Return JSON only with keys fair_yes, confidence, reasoning, and watch_for. fair_yes must be a number from 0 to 1. confidence must be low, medium, or high. reasoning must be one short sentence. watch_for must be an array of up to three short strings. Do not use the live market price itself as evidence. If fair value is inside the no-bet band, say there is no actionable edge rather than implying certainty. watch_for items must be concrete monitoring hooks such as transcript release, exact-phrase confirmation, or excluded-segment risk, not names, tickers, or event titles.';

function isObject(value) {
  return Boolean(value) && typeof value === 'object' && !Array.isArray(value);
}

function mergeMetadata(input, extraMetadata) {
  return {
    ...(isObject(input.metadata) ? input.metadata : {}),
    ...extraMetadata,
  };
}

function toNumber(value) {
  if (value == null || value === '') return null;
  const number = Number(value);
  return Number.isFinite(number) ? number : null;
}

function clampProbability(value) {
  const number = toNumber(value);
  if (number == null) return null;
  return Math.max(0, Math.min(1, number));
}

function normalizeConfidence(value) {
  if (typeof value !== 'string') return 'low';
  const lowered = value.trim().toLowerCase();
  if (lowered === 'high' || lowered === 'medium' || lowered === 'low') {
    return lowered;
  }
  return 'low';
}

function normalizeReasoning(value) {
  if (typeof value !== 'string') return null;
  const cleaned = value.trim();
  return cleaned || null;
}

function normalizeWatchFor(value) {
  if (!Array.isArray(value)) return [];
  return value
    .filter(item => typeof item === 'string')
    .map(item => item.trim())
    .filter(Boolean)
    .slice(0, 3);
}

function parseJsonResponse(text) {
  const trimmed = typeof text === 'string' ? text.trim() : '';
  if (!trimmed) return null;

  try {
    return JSON.parse(trimmed);
  } catch {
    const fenced = trimmed.match(/```(?:json)?\s*([\s\S]*?)```/i);
    if (!fenced?.[1]) return null;
    try {
      return JSON.parse(fenced[1].trim());
    } catch {
      return null;
    }
  }
}

function extractMessageText(content) {
  if (typeof content === 'string') return content;
  if (!Array.isArray(content)) return null;
  return content
    .map(part => (typeof part?.text === 'string' ? part.text : ''))
    .filter(Boolean)
    .join('\n');
}

function buildPromptPayload(input) {
  const metadata = isObject(input.metadata) ? input.metadata : {};
  const availableContracts = Array.isArray(metadata.available_contracts)
    ? metadata.available_contracts.slice(0, 5).map(contract => ({
        market_ticker: contract.market_ticker ?? null,
        label: contract.label ?? null,
        market_yes: contract.market_yes ?? null,
        yes_bid: contract.yes_bid ?? null,
        yes_ask: contract.yes_ask ?? null,
        last_price: contract.last_price ?? null,
      }))
    : [];

  return {
    venue: input.venue ?? 'Kalshi',
    market_id: input.market_id ?? metadata.market_ticker ?? null,
    title: input.title ?? null,
    question: input.question ?? null,
    event_domain_hint: input.domain ?? null,
    event_name: metadata.event_name ?? null,
    speaker: metadata.speaker ?? null,
    target_phrase: metadata.target_phrase ?? null,
    rules_summary: metadata.rules_summary ?? null,
    market: {
      status: metadata.market_status ?? null,
      market_yes: metadata.market_yes ?? null,
      market_yes_bid: metadata.market_yes_bid ?? null,
      market_yes_ask: metadata.market_yes_ask ?? null,
      last_price: metadata.market_last_price ?? null,
    },
    available_contracts: availableContracts,
  };
}

async function callOpenRouterAlpha(payload, options) {
  const fetchImpl = options.alphaFetchImpl ?? options.fetchImpl ?? globalThis.fetch;
  const apiKey = options.alphaApiKey ?? process.env.OPENROUTER_API_KEY ?? null;
  const model =
    options.alphaModel ??
    resolveOpenRouterModel('EVENT_MARKET_ALPHA_MODEL', resolveOpenRouterModel('IMPLICATIONS_MODEL'));

  if (!apiKey || typeof fetchImpl !== 'function') return null;

  const requestBody = JSON.stringify({
    model,
    temperature: 0.1,
    max_tokens: 400,
    reasoning: {
      effort: 'none',
      exclude: true,
    },
    messages: [
      {
        role: 'system',
        content: ALPHA_SYSTEM_PROMPT,
      },
      {
        role: 'user',
        content: JSON.stringify(payload),
      },
    ],
  });

  for (let attempt = 0; attempt < 2; attempt += 1) {
    try {
      const response = await fetchImpl(OPENROUTER_URL, {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${apiKey}`,
          'Content-Type': 'application/json',
        },
        body: requestBody,
      });

      if (!response.ok) {
        continue;
      }

      const data = await response.json();
      const content = extractMessageText(data?.choices?.[0]?.message?.content);
      const parsed = parseJsonResponse(content);
      if (parsed) {
        return parsed;
      }
    } catch {
      // Retry once on transient network/provider failures.
    }
  }

  return null;
}

export async function enrichEventMarketAlpha(input = {}, options = {}) {
  const metadata = isObject(input.metadata) ? input.metadata : {};
  const targetPhrase = metadata.target_phrase ?? null;
  const marketTicker = metadata.market_ticker ?? null;
  const marketYes = toNumber(metadata.market_yes);
  const marketStatus = metadata.market_status ?? null;

  if (!targetPhrase || !marketTicker || marketYes == null) {
    return input;
  }

  if (marketStatus && marketStatus !== 'active') {
    return input;
  }

  if (metadata.fair_yes != null && metadata.edge_cents != null) {
    return input;
  }

  const alpha = await callOpenRouterAlpha(buildPromptPayload(input), options);
  if (!isObject(alpha)) {
    return input;
  }

  const fairYes = clampProbability(alpha.fair_yes);
  const confidence = normalizeConfidence(alpha.confidence);
  const reasoning = normalizeReasoning(alpha.reasoning);
  const watchFor = normalizeWatchFor(alpha.watch_for);

  if (fairYes == null) {
    return input;
  }

  const signedEdge = Number(((fairYes - marketYes) * 100).toFixed(1));
  const boundedEdge = Math.abs(signedEdge) < EDGE_THRESHOLD_CENTS ? 0 : signedEdge;

  return {
    ...input,
    metadata: mergeMetadata(input, {
      fair_yes: fairYes,
      edge_cents: boundedEdge,
      alpha_confidence: confidence,
      alpha_summary_reason: reasoning,
      watch_for: watchFor.length > 0 ? watchFor : metadata.watch_for,
      alpha_model:
        options.alphaModel ??
        resolveOpenRouterModel('EVENT_MARKET_ALPHA_MODEL', resolveOpenRouterModel('IMPLICATIONS_MODEL')),
    }),
  };
}
