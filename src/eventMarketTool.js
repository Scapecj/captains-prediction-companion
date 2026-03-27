import { buildEventMarketContract } from './eventMarketContract.js';

export async function buildEventMarketPlan(input = {}) {
  return buildEventMarketContract(input);
}

export function buildEventMarketPlanSummary(result = {}) {
  return {
    status: 'background_planned',
    recommendation: 'review_plan',
    confidence: null,
    one_line_reason:
      'The detailed workflow stays hidden in structured content while only the compact card is shown.',
    next_action:
      'Add pricing if you want a real buy_yes, buy_no, or pass decision.',
  };
}
