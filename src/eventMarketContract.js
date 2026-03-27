function canonicalizeVenue(venue) {
  if (!venue) return 'Kalshi';
  const value = String(venue).trim();
  if (!value) return 'Kalshi';
  if (/^kalshi/i.test(value)) return 'Kalshi';
  if (/^polymarket/i.test(value)) return 'Polymarket';
  return value;
}

function normalizeDomain(domain) {
  if (!domain) return 'general';
  const value = String(domain).trim().toLowerCase();
  const aliases = {
    sports: 'sports',
    politics: 'politics',
    macro: 'macro',
    economics: 'macro',
    earnings: 'mention',
    corporate: 'mention',
    mention: 'mention',
    mentions: 'mention',
    media: 'mention',
    general: 'general',
  };
  return aliases[value] ?? value;
}

function normalizeText(value) {
  return value == null ? '' : String(value).trim().toLowerCase();
}

function extractUrlContext(url) {
  if (!url) {
    return {
      hostname: '',
      pathname: '',
      tokens: [],
      tail: '',
    };
  }

  const raw = String(url).trim();
  if (!raw) {
    return {
      hostname: '',
      pathname: '',
      tokens: [],
      tail: '',
    };
  }

  let parsed = null;
  try {
    parsed = new URL(raw);
  } catch {
    return {
      hostname: '',
      pathname: raw.toLowerCase(),
      tokens: raw
        .toLowerCase()
        .split(/[^a-z0-9]+/)
        .filter(Boolean),
      tail: raw.toLowerCase(),
    };
  }

  const pathname = parsed.pathname.toLowerCase();
  const segments = pathname
    .split('/')
    .filter(Boolean)
    .map(segment => segment.toLowerCase());
  const tail = segments.length > 0 ? segments[segments.length - 1] : '';
  const slugTokens = segments.flatMap(segment => segment.split(/[^a-z0-9]+/).filter(Boolean));

  return {
    hostname: parsed.hostname.toLowerCase(),
    pathname,
    tokens: slugTokens,
    tail,
  };
}

function inferMarketId(input) {
  if (input.market_id) {
    return String(input.market_id).trim() || null;
  }

  const urlContext = extractUrlContext(input.url);
  if (urlContext.tail && /[a-z0-9]/i.test(urlContext.tail)) {
    return urlContext.tail.toUpperCase();
  }

  return null;
}

function collectDomainText(input) {
  const urlContext = extractUrlContext(input.url);
  return [
    input.title,
    input.question,
    input.market_id,
    input.url,
    input.resolution_source,
    urlContext.pathname,
    urlContext.tokens.join(' '),
    urlContext.tail,
  ]
    .map(normalizeText)
    .filter(Boolean)
    .join(' ');
}

function inferDomain(input) {
  const explicit = normalizeDomain(input.domain);
  if (explicit !== 'general') {
    return explicit;
  }

  const haystack = collectDomainText(input);

  if (/\bmention(s)?\b|\bphrase\b|\bword\b|\bsaid\b|\bsays\b|\bsaying\b|\bspeech\b|\bremarks\b/.test(haystack)) {
    return 'mention';
  }

  if (/\b(nfl|nba|mlb|ufc|nascar|football|basketball|baseball|team|game|score|win|quarter|series)\b/.test(haystack)) {
    return 'sports';
  }

  if (/\b(election|politics|president|congress|senate|house|debate|campaign|white house|c-span|press conference)\b/.test(haystack)) {
    return 'politics';
  }

  if (/\b(inflation|fed|fomc|rates|cpi|jobs|unemployment|gdp|powell|treasury)\b/.test(haystack)) {
    return 'macro';
  }

  if (/\b(earnings|earnings call|quarter|revenue|guidance|investor relations|transcript)\b/.test(haystack)) {
    return 'mention';
  }

  return 'general';
}

function buildMacroProfile() {
  return {
    name: 'macro-market-research',
    wrapper: 'macro-market',
    source_hints: [
      'Official government release or central-bank release',
      'Official transcript or press conference when applicable',
      'Perplexity-discovered authoritative public source',
    ],
    evidence_targets: [
      'official release',
      'official transcript',
      'press conference replay',
      'statement',
      'data release page',
    ],
    comparison_axes: ['release type', 'policy path', 'headline data vs. core data', 'surprise vs. expectation', 'execution risk'],
    source_tree_note:
      'For macro markets, the controlling source is usually the official release or press event named by the rules. Use the scraper only after the authoritative public source is located.',
    stage_overrides: [
      {
        stage: 'intake',
        purpose: 'Identify the release, event type, venue, and settlement boundary.',
        input_focus: 'market title, market id, venue, release type, date, time',
        output_focus: 'macro market context',
      },
      {
        stage: 'market',
        purpose: 'Read the Kalshi board and the rules before looking at any macro data.',
        input_focus: 'contract wording, resolution rules, source hierarchy, price, order book',
        output_focus: 'venue-grounded macro snapshot',
      },
      {
        stage: 'research',
        purpose: 'Use Perplexity to find the authoritative official release or event page.',
        input_focus: 'which official page or press event controls the question',
        output_focus: 'ranked source tree and source summary',
      },
      {
        stage: 'evidence',
        purpose: 'Use the scraper skill to extract the exact release, statement, or transcript evidence.',
        input_focus: 'official release pages, transcripts, press conference replays, statements',
        output_focus: 'verbatim or structured evidence',
      },
      {
        stage: 'pricing',
        purpose: 'Convert the evidence into fair probability and edge.',
        input_focus: 'market probability, fair probability, and release surprise',
        output_focus: 'EV, confidence, and stake cap',
      },
      {
        stage: 'decision',
        purpose: 'Apply macro-specific no-bet filters and produce the final action.',
        input_focus: 'confidence, source quality, release timing, execution risk',
        output_focus: 'buy_yes, buy_no, or pass',
      },
      {
        stage: 'logging',
        purpose: 'Store the source tree and final decision for reuse.',
        input_focus: 'all intermediate outputs',
        output_focus: 'audit-ready decision record',
      },
    ],
    notes:
      'Macro markets are release-and-event problems. Read the official source first, then use Perplexity to confirm the exact page or event, then scrape the source for the actionable text or numbers.',
  };
}

function buildPoliticsProfile() {
  return {
    name: 'politics-market-research',
    wrapper: 'politics-market',
    source_hints: [
      'Official stream or public event page',
      'Official transcript or pool report when available',
      'Perplexity-discovered authoritative public source',
    ],
    evidence_targets: [
      'official stream',
      'official transcript',
      'press conference replay',
      'debate replay',
      'statement',
      'campaign page',
    ],
    comparison_axes: ['speaker role', 'event type', 'prepared remarks vs Q&A', 'policy position', 'execution risk'],
    source_tree_note:
      'For politics markets, the controlling source is usually the exact official stream, transcript, or event page named by the rules. Use the scraper only after the authoritative public source is located.',
    stage_overrides: [
      {
        stage: 'intake',
        purpose: 'Identify the speaker, event type, venue, and settlement boundary.',
        input_focus: 'market title, market id, venue, speaker, event type, date, time',
        output_focus: 'politics market context',
      },
      {
        stage: 'market',
        purpose: 'Read the Kalshi board and the rules before looking at any political data.',
        input_focus: 'contract wording, resolution rules, source hierarchy, price, order book',
        output_focus: 'venue-grounded politics snapshot',
      },
      {
        stage: 'research',
        purpose: 'Use Perplexity to find the authoritative official stream or event page.',
        input_focus: 'which official page or event controls the question',
        output_focus: 'ranked source tree and source summary',
      },
      {
        stage: 'evidence',
        purpose: 'Use the scraper skill to extract the exact speech, debate, or transcript evidence.',
        input_focus: 'official streams, transcripts, debate clips, statements, pool reports',
        output_focus: 'verbatim or structured evidence',
      },
      {
        stage: 'pricing',
        purpose: 'Convert the evidence into fair probability and edge.',
        input_focus: 'market probability, fair probability, and speaker incentives',
        output_focus: 'EV, confidence, and stake cap',
      },
      {
        stage: 'decision',
        purpose: 'Apply politics-specific no-bet filters and produce the final action.',
        input_focus: 'confidence, source quality, timing, execution risk',
        output_focus: 'buy_yes, buy_no, or pass',
      },
      {
        stage: 'logging',
        purpose: 'Store the source tree and final decision for reuse.',
        input_focus: 'all intermediate outputs',
        output_focus: 'audit-ready decision record',
      },
    ],
    notes:
      'Politics markets are speaker-and-event problems. Read the official source first, then use Perplexity to confirm the exact page or event, then scrape the source for the actionable text or words.',
  };
}

function buildDomainProfile(domain) {
  if (domain === 'mention') {
    return {
      name: 'mention-market-research',
      wrapper: 'mention-market',
      source_hints: [
        'Kalshi market rules and board wording',
        'Perplexity-discovered authoritative source',
        'Live broadcast, replay, or official transcript depending on the rules',
      ],
      evidence_targets: [
        'live broadcast',
        'official replay',
        'official transcript',
        'captions only if the rules allow them',
      ],
      comparison_axes: [
        'allowed speaker role',
        'prepared remarks versus Q&A',
        'event segment and boundary',
        'exact word form and phrase allowance',
        'reflexivity risk if the market changes speech incentives',
      ],
      source_tree_note:
        'For mention markets, the controlling source is usually the exact live source named by the rules. The scraper is only for exact evidence extraction after the source is located.',
      stage_overrides: [
        {
          stage: 'intake',
          purpose: 'Identify the exact phrase, allowed speaker, event boundary, and rules clause.',
          input_focus: 'market title, market id, venue, allowed speaker scope, phrase wording',
          output_focus: 'contract-specific mention context',
        },
        {
          stage: 'market',
          purpose: 'Read the Kalshi board and the rules before doing any probability work.',
          input_focus: 'contract wording, resolution rules, source hierarchy, price, order book',
          output_focus: 'venue-grounded mention snapshot',
        },
        {
          stage: 'research',
          purpose: 'Use Perplexity to discover the exact authoritative source that controls settlement.',
          input_focus: 'which live source, replay, or transcript actually matters',
          output_focus: 'ranked source tree and source summary',
        },
        {
          stage: 'scope',
          purpose: 'Determine whether the phrase is allowed for the speaker, role, and segment.',
          input_focus: 'speaker role, prepared remarks, Q&A, moderator prompts, exclusions',
          output_focus: 'speaker-scope decision',
        },
        {
          stage: 'evidence',
          purpose: 'Use the scraper skill to extract the exact supporting or falsifying evidence.',
          input_focus: 'official pages, transcripts, captions, replay timestamps, clip text',
          output_focus: 'verbatim or structured evidence',
        },
        {
          stage: 'pricing',
          purpose: 'Convert the evidence into a phrase probability and edge estimate.',
          input_focus: 'market probability vs. fair probability, role, and event-specific bias',
          output_focus: 'EV, confidence, and stake cap',
        },
        {
          stage: 'decision',
          purpose: 'Apply mention-specific no-bet filters and produce the final action.',
          input_focus: 'confidence, source quality, clause fit, execution risk',
          output_focus: 'buy_yes, buy_no, or pass',
        },
        {
          stage: 'logging',
          purpose: 'Store the source tree, scope judgment, and final decision for reuse.',
          input_focus: 'all intermediate outputs',
          output_focus: 'audit-ready decision record',
        },
      ],
      notes:
        'Mention markets are resolution-constrained language problems. Treat contract wording as stricter than common sense, separate allowed speaker roles carefully, and only trust transcripts or captions when the rules allow them. Earnings-call markets belong here as mention markets, not as a separate domain.',
    };
  }

  if (domain === 'sports') {
    return {
      name: 'sports-market-research',
      wrapper: 'sports-market',
      source_hints: [
        'Kalshi board and rules',
        'Perplexity-discovered official source',
        'Public schedules, scoreboards, injury reports, lineup pages, or broadcast evidence',
      ],
      evidence_targets: [
        'official schedule',
        'live scoreboard',
        'injury report',
        'lineup page',
        'broadcast replay',
        'official stats page',
      ],
      comparison_axes: ['league', 'market subtype', 'game state', 'team or player context', 'execution risk'],
      source_tree_note:
        'For sports markets, the outside source should be the smallest authoritative public page that actually controls settlement, with scraper extraction used only after that page is identified.',
      stage_overrides: [
        {
          stage: 'intake',
          purpose: 'Identify the league, market subtype, venue, and settlement boundary.',
          input_focus: 'market title, market id, venue, league, market subtype, date',
          output_focus: 'sports market context',
        },
        {
          stage: 'market',
          purpose: 'Read the Kalshi board and rules before looking at any outside sports data.',
          input_focus: 'contract wording, resolution rules, price, order book, market subtype',
          output_focus: 'venue-grounded sports snapshot',
        },
        {
          stage: 'routing',
          purpose: 'Route the market into the correct league-specific modeling skill.',
          input_focus: 'league id, sport, market subtype, pregame versus live versus futures',
          output_focus: 'sport-specific model route',
        },
        {
          stage: 'research',
          purpose: 'Use Perplexity to find the authoritative sports source or public page.',
          input_focus: 'which official page, scoreboard, or report controls the question',
          output_focus: 'ranked source tree and source summary',
        },
        {
          stage: 'evidence',
          purpose: 'Use the scraper skill to extract the exact sports evidence needed for pricing.',
          input_focus: 'schedules, scoreboards, lineups, injuries, stats, replay evidence',
          output_focus: 'verbatim or structured evidence',
        },
        {
          stage: 'pricing',
          purpose: 'Convert the evidence into fair probability and edge.',
          input_focus: 'model probability, market probability, and risk limits',
          output_focus: 'EV, confidence, and stake cap',
        },
        {
          stage: 'decision',
          purpose: 'Apply sports-specific no-bet filters and produce the final action.',
          input_focus: 'confidence, stale data, injury uncertainty, execution risk',
          output_focus: 'buy_yes, buy_no, or pass',
        },
        {
          stage: 'logging',
          purpose: 'Store the routing choice, source tree, and final decision for reuse.',
          input_focus: 'all intermediate outputs',
          output_focus: 'audit-ready decision record',
        },
      ],
      notes:
        'Sports markets should route by league and market subtype before pricing. Use the market venue first, then route into the sport-specific skill, then research the truth source, then extract evidence.',
    };
  }

  if (domain === 'macro') {
    return buildMacroProfile();
  }

  if (domain === 'politics') {
    return buildPoliticsProfile();
  }

  return {
    name: 'event-market-research',
    wrapper: 'general-event-market',
    source_hints: ['Kalshi market rules and board wording', 'Perplexity source discovery', 'Playwright scraper evidence extraction'],
    evidence_targets: ['official page', 'transcript', 'filing', 'schedule', 'board or replay'],
    comparison_axes: ['source fit', 'resolution wording', 'timing boundary', 'execution risk'],
    source_tree_note:
      'Use the venue first, then discover the authoritative outside source, then extract evidence with the scraper skill.',
    stage_overrides: [],
    notes:
      'Keep the output compact, audit-friendly, and reusable across sports, politics, macro, and mention markets.',
  };
}

function buildPlan(input) {
  const venue = canonicalizeVenue(input.venue);
  const domain = inferDomain(input);
  const domainProfile = buildDomainProfile(domain);
  const sourceOrder = [venue, 'Perplexity', 'Playwright Scraper Skill'];
  const marketId = inferMarketId(input);
  const url = input.url ? String(input.url).trim() || null : null;

  return {
    venue,
    domain,
    domain_profile: domainProfile,
    source_order: sourceOrder,
    primary_source: sourceOrder[0],
    research_source: sourceOrder[1],
    evidence_source: sourceOrder[2],
    decision_rule: 'Market first, Perplexity second, scraper third, decision layer last.',
    notes: domainProfile.notes,
    metadata: {
      market_id: marketId,
      title: input.title ?? null,
      question: input.question ?? null,
      market_type: input.market_type ?? null,
      market_subtype: input.market_subtype ?? null,
      url,
      resolution_source: input.resolution_source ?? null,
      context: input.metadata ? { ...input.metadata } : {},
    },
  };
}

function buildWorkflow(plan) {
  const domainProfile = plan.domain_profile;
  const stages =
    domainProfile.stage_overrides.length > 0
      ? domainProfile.stage_overrides
      : [
          {
            stage: 'intake',
            purpose: 'Identify the market, venue, domain, and contract boundary.',
            input_focus: 'market title, market id, venue, question, domain',
            output_focus: 'canonical market context',
          },
          {
            stage: 'market',
            purpose: 'Read the venue itself before looking anywhere else.',
            input_focus: 'contract wording, resolution rules, price, order book',
            output_focus: 'venue-grounded market snapshot',
          },
          {
            stage: 'research',
            purpose: 'Use Perplexity to find the authoritative outside source.',
            input_focus: 'what source actually settles the dispute',
            output_focus: 'ranked source tree and source summary',
          },
          {
            stage: 'evidence',
            purpose: 'Use the scraper skill to extract the exact supporting facts.',
            input_focus: 'official pages, transcripts, filings, schedules, scoreboards',
            output_focus: 'verbatim or structured evidence',
          },
          {
            stage: 'pricing',
            purpose: 'Convert the evidence into fair probability and edge.',
            input_focus: 'market probability vs. fair probability',
            output_focus: 'EV, confidence, and stake cap',
          },
          {
            stage: 'decision',
            purpose: 'Apply no-bet filters and produce a final action.',
            input_focus: 'confidence, stale data, CLV, execution risk',
            output_focus: 'buy_yes, buy_no, or pass',
          },
          {
            stage: 'logging',
            purpose: 'Store the market source tree and final decision for reuse.',
            input_focus: 'all intermediate outputs',
            output_focus: 'audit-ready decision record',
          },
        ];

  return {
    name: domainProfile.name,
    domain_wrapper: domainProfile.wrapper,
    domain_profile: domainProfile,
    stages,
    source_order: plan.source_order,
    source_hints: domainProfile.source_hints,
    evidence_targets: domainProfile.evidence_targets,
    comparison_axes: domainProfile.comparison_axes,
    source_tree_note: domainProfile.source_tree_note,
    decision_rule: plan.decision_rule,
    notes: plan.notes,
  };
}

function buildOutputContract() {
  return {
    name: 'event-market-output',
    sections: [
      {
        section: 'user_facing',
        fields: [
          { name: 'status', kind: 'string', required: true, description: 'Compact status for the chat response, such as background_planned, pick_ready, buy_yes, buy_no, or pass.' },
          { name: 'recommendation', kind: 'string', required: true, description: 'Short user-facing recommendation or action label.' },
          { name: 'confidence', kind: 'number', required: false, description: 'Optional confidence score for the recommendation, normalized to 0-1.' },
          { name: 'one_line_reason', kind: 'string', required: true, description: 'Single-sentence explanation with no workflow dump.' },
          { name: 'background_plan_hidden', kind: 'boolean', required: true, description: 'True when the detailed planning memo should stay hidden from the user.' },
          { name: 'next_action', kind: 'string', required: false, description: 'Optional next step if the user should do something else.' },
        ],
      },
      {
        section: 'market',
        fields: [
          { name: 'venue', kind: 'string', required: true, description: 'Market venue or exchange name.' },
        { name: 'domain', kind: 'string', required: true, description: 'High-level event domain such as sports, politics, macro, mention, or general.' },
          { name: 'market_id', kind: 'string', required: false, description: 'Venue-specific market identifier when available.' },
          { name: 'title', kind: 'string', required: false, description: 'Human-readable title or question for the market.' },
          { name: 'question', kind: 'string', required: false, description: 'Binary proposition or resolution question.' },
          { name: 'market_type', kind: 'string', required: false, description: 'High-level market type such as binary, spread, total, prop, or future.' },
          { name: 'market_subtype', kind: 'string', required: false, description: 'Narrow subtype used for routing and logging.' },
          { name: 'url', kind: 'string', required: false, description: 'Canonical URL for the market or source page.' },
        ],
      },
      {
        section: 'sources',
        fields: [
          { name: 'source_order', kind: 'array[string]', required: true, description: 'Ordered source stack used by the pipeline.' },
          { name: 'resolution_source', kind: 'string', required: false, description: 'Primary authoritative source that settles the market if known.' },
          { name: 'primary_evidence', kind: 'string', required: false, description: 'The strongest evidence item supporting the decision.' },
          { name: 'secondary_evidence', kind: 'array[string]', required: false, description: 'Supporting evidence items or citations.' },
          { name: 'falsifier', kind: 'string', required: false, description: 'What would invalidate the thesis or force a pass.' },
        ],
      },
      {
        section: 'domain_profile',
        fields: [
          { name: 'wrapper', kind: 'string', required: true, description: 'Domain wrapper used to choose the right market-specific workflow.' },
          { name: 'source_hints', kind: 'array[string]', required: true, description: 'High-level source hints for the active domain.' },
          { name: 'evidence_targets', kind: 'array[string]', required: true, description: 'Concrete evidence targets to search for after source discovery.' },
          { name: 'comparison_axes', kind: 'array[string]', required: true, description: 'The main axes used to compare the market thesis to historical or contextual evidence.' },
          { name: 'source_tree_note', kind: 'string', required: false, description: 'Short note explaining how the source tree should be interpreted for the active domain.' },
        ],
      },
      {
        section: 'pricing',
        fields: [
          { name: 'fair_probability', kind: 'number', required: true, description: 'Model probability for the side being evaluated.' },
          { name: 'market_probability', kind: 'number', required: true, description: 'Market-implied probability from the venue or consensus book.' },
          { name: 'edge', kind: 'number', required: true, description: 'Fair probability minus market probability.' },
          { name: 'expected_value', kind: 'number', required: true, description: 'Expected value per unit stake after simple pricing.' },
          { name: 'confidence', kind: 'number', required: true, description: 'Confidence score for the estimate, normalized to 0-1.' },
        ],
      },
      {
        section: 'decision',
        fields: [
          { name: 'decision', kind: 'string', required: true, description: 'Final action: buy_yes, buy_no, pass, or watch.' },
          { name: 'no_bet_flag', kind: 'boolean', required: true, description: 'True when the edge does not survive the filters.' },
          { name: 'recommended_stake_cap', kind: 'number', required: false, description: 'Maximum stake recommended after risk sizing.' },
          { name: 'notes', kind: 'string', required: false, description: 'Short rationale and any execution caveats.' },
        ],
      },
    ],
    notes: 'Keep the output compact, audit-friendly, and reusable across sports, politics, macro, and mention markets.',
  };
}

export function buildEventMarketContract(input = {}) {
  const plan = buildPlan(input);
  return {
    plan,
    workflow: buildWorkflow(plan),
    output_contract: buildOutputContract(),
  };
}
