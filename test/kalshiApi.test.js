import test from 'node:test';
import assert from 'node:assert/strict';
import { enrichEventMarketInput } from '../src/kalshiApi.js';

const KALSHI_BASE_URL = 'https://api.elections.kalshi.com/trade-api/v2';

function createFetchStub(routeMap) {
  return async (url, init = {}) => {
    const key = typeof url === 'string' ? url : url.toString();
    if (!routeMap.has(key)) {
      throw new Error(`Unexpected fetch call for ${key}`);
    }

    const payload = routeMap.get(key);
    return {
      ok: true,
      status: 200,
      async json() {
        return JSON.parse(JSON.stringify(payload));
      },
      init,
    };
  };
}

test('enrichEventMarketInput returns untouched input when no Kalshi context exists', async () => {
  const input = { title: 'No URL present' };
  const result = await enrichEventMarketInput(input, {
    fetchImpl: () => {
      throw new Error('fetch should not be called');
    },
  });

  assert.strictEqual(result, input);
});

test('enrichEventMarketInput fetches board data and picks a matching contract by phrase', async () => {
  const eventTicker = 'KXMULTIMARKET-24APR30';
  const boardUrl = `https://kalshi.com/markets/kxmultimarket/board/${eventTicker}`;
  const markets = [
    {
      ticker: `${eventTicker}-LION`,
      yes_bid_dollars: '0.30',
      yes_ask_dollars: '0.34',
      last_price_dollars: '0.32',
      status: 'active',
      custom_strike: { Word: 'Lion' },
      rules_primary: 'If Alex Doe says Lion during the keynote, settle Yes.',
      rules_secondary: 'Live stream resolves the question.',
    },
    {
      ticker: `${eventTicker}-TIGER`,
      yes_bid_dollars: '0.10',
      yes_ask_dollars: '0.50',
      last_price_dollars: '0.12',
      status: 'active',
      yes_sub_title: 'Tiger',
      rules_primary: 'If Alex Doe says Tiger during the keynote, settle Yes.',
    },
  ];

  const fetchImpl = createFetchStub(
    new Map([
      [
        `${KALSHI_BASE_URL}/events/${eventTicker}`,
        {
          event: {
            category: 'Mentions',
            event_ticker: eventTicker,
            series_ticker: 'KXMULTIMARKET',
            sub_title: 'Alex Doe - Wildlife Keynote',
            title: 'What will Alex Doe say during the Wildlife Keynote?',
          },
          markets,
        },
      ],
      [
        `${KALSHI_BASE_URL}/markets/${eventTicker}-LION/orderbook`,
        {
          orderbook_fp: {
            yes_dollars: [[0.34, 25]],
            no_dollars: [[0.66, 25]],
          },
        },
      ],
    ])
  );

  const result = await enrichEventMarketInput(
    { venue: 'Kalshi', url: boardUrl, question: 'Will Alex Doe say "Lion"?' },
    { fetchImpl }
  );

  assert.equal(result.domain, 'mention');
  assert.equal(result.market_subtype, 'mention');
  assert.equal(result.metadata.market_ticker, `${eventTicker}-LION`);
  assert.equal(result.metadata.kalshi_event_ticker, eventTicker);
  assert.equal(result.metadata.kalshi_series_ticker, 'KXMULTIMARKET');
  assert.equal(result.metadata.target_phrase, 'Lion');
  assert.equal(result.metadata.speaker, 'Alex Doe');
  assert.equal(result.metadata.event_name, 'Wildlife Keynote');
  assert.equal(result.metadata.market_status, 'active');
  assert.equal(result.metadata.market_yes, 0.32);
  assert.deepEqual(result.metadata.orderbook, {
    yes_dollars: [[0.34, 25]],
    no_dollars: [[0.66, 25]],
  });
  assert.equal(result.metadata.board_contract_count, 2);
  assert.equal(result.metadata.available_contracts.length, 2);
  assert.equal(result.metadata.available_contracts[0].market_ticker, `${eventTicker}-LION`);
  assert.ok(
    (result.metadata.available_contracts[0].market_yes ?? 0) >=
      (result.metadata.available_contracts[1].market_yes ?? 0)
  );
  assert.equal(result.market_id, `${eventTicker}-LION`);
  assert.equal(result.title, 'What will Alex Doe say during the Wildlife Keynote?');
  assert.equal(result.question, 'Will Alex Doe say "Lion"?');
});
