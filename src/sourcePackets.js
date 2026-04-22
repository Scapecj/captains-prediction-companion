const TESLA_CIK = '1318605';

function isObject(value) {
  return Boolean(value) && typeof value === 'object' && !Array.isArray(value);
}

function normalizeString(value) {
  return value == null ? '' : String(value).trim();
}

function normalizeComparableText(value) {
  return normalizeString(value).toLowerCase().replace(/[^a-z0-9]+/g, ' ').trim();
}

function compactWhitespace(value) {
  return normalizeString(value).replace(/\s+/g, ' ').trim();
}

function decodeHtmlEntities(text) {
  return normalizeString(text)
    .replace(/&#8217;/g, "'")
    .replace(/&#8220;/g, '"')
    .replace(/&#8221;/g, '"')
    .replace(/&#8211;/g, '-')
    .replace(/&#8212;/g, '-')
    .replace(/&#160;/g, ' ')
    .replace(/&amp;/g, '&')
    .replace(/&lt;/g, '<')
    .replace(/&gt;/g, '>')
    .replace(/&quot;/g, '"');
}

function stripHtml(html) {
  return decodeHtmlEntities(
    normalizeString(html)
      .replace(/<script[\s\S]*?<\/script>/gi, ' ')
      .replace(/<style[\s\S]*?<\/style>/gi, ' ')
      .replace(/<[^>]+>/g, ' ')
  );
}

function uniqueStrings(values) {
  return [...new Set(values.map(normalizeString).filter(Boolean))];
}

function extractSnippet(text, terms = [], windowSize = 260) {
  const haystack = normalizeString(text);
  if (!haystack) return null;

  const lowered = haystack.toLowerCase();
  const candidateTerms = uniqueStrings(terms)
    .map(term => ({
      raw: term,
      normalized: normalizeComparableText(term),
    }))
    .filter(term => term.normalized);

  let bestIndex = -1;
  let bestTerm = null;
  for (const term of candidateTerms) {
    const index = lowered.indexOf(term.normalized);
    if (index >= 0 && (bestIndex < 0 || index < bestIndex)) {
      bestIndex = index;
      bestTerm = term.raw;
    }
  }

  if (bestIndex < 0) return null;

  const start = Math.max(0, bestIndex - windowSize);
  const end = Math.min(haystack.length, bestIndex + Math.max(windowSize, bestTerm?.length ?? 0) + windowSize);
  return compactWhitespace(haystack.slice(start, end));
}

function safeUrl(base, maybeRelative) {
  if (!maybeRelative) return null;
  try {
    return new URL(maybeRelative, base).toString();
  } catch {
    return null;
  }
}

async function fetchJson(url, options = {}) {
  const response = await fetch(url, {
    headers: {
      'user-agent': options.userAgent ?? 'HermesAgent/1.0 (research packet)',
      accept: 'application/json,text/plain,*/*',
    },
  });

  if (!response.ok) {
    throw new Error(`Fetch failed for ${url}: ${response.status} ${response.statusText}`);
  }

  return response.json();
}

async function fetchText(url, options = {}) {
  const response = await fetch(url, {
    headers: {
      'user-agent': options.userAgent ?? 'HermesAgent/1.0 (research packet)',
      accept: 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
      'accept-language': 'en-US,en;q=0.9',
    },
  });

  if (!response.ok) {
    throw new Error(`Fetch failed for ${url}: ${response.status} ${response.statusText}`);
  }

  return response.text();
}

function inferMarketText(input = {}) {
  const metadata = isObject(input.metadata) ? input.metadata : {};
  return [
    input.url,
    input.title,
    input.question,
    input.domain,
    input.market_id,
    input.market_type,
    metadata.rules_summary,
    metadata.target_phrase,
    metadata.speaker,
    metadata.event_name,
    metadata.kalshi_category,
  ]
    .filter(Boolean)
    .map(value => String(value).toLowerCase())
    .join(' ');
}

function isTeslaEarningsMarket(input = {}) {
  const text = inferMarketText(input);
  return /tesla|tsla/.test(text) && /(earnings|quarter|full self driving|fsd|optimus|robotaxi|battery|delivery)/.test(text);
}

function isMacroMarket(input = {}) {
  const text = inferMarketText(input);
  return /(cpi|inflation|ppi|jobs|unemployment|gdp|fomc|fed|rates|treasury|pce|employment)/.test(text);
}

function buildBasePacket(input = {}) {
  const metadata = isObject(input.metadata) ? input.metadata : {};
  return {
    board_url: input.url ?? null,
    market_id: input.market_id ?? metadata.market_ticker ?? null,
    event_domain: input.domain ?? null,
    event_type: input.event_type ?? null,
    market_type: input.market_type ?? null,
    target_phrase: metadata.target_phrase ?? null,
    rules_summary: metadata.rules_summary ?? null,
    source_packet_kind: 'generic',
    source_quality: 'low',
    evidence_strength: 'low',
    official_source_url: null,
    official_source_type: null,
    transcript_excerpt: null,
    exact_phrase_status: 'unknown',
    event_format: null,
    speaker_type: null,
    timing_relevance: null,
    why_valid_under_kalshi_rules: null,
    catalyst: null,
    reasoning_chain: [],
    invalidation_condition: null,
    time_sensitivity: null,
    unresolved_gaps: ['Official source not yet located'],
    official_source_candidates: [],
  };
}

async function buildTeslaEarningsSourcePacket(input = {}, options = {}) {
  const metadata = isObject(input.metadata) ? input.metadata : {};
  const sourcePacket = buildBasePacket(input);
  sourcePacket.source_packet_kind = 'earnings';
  sourcePacket.event_domain = 'mention';
  sourcePacket.event_type = 'earnings_call';
  sourcePacket.market_type = 'mention';
  sourcePacket.source_quality = 'high';
  sourcePacket.evidence_strength = 'high';
  sourcePacket.event_format = 'issuer earnings update / 8-K exhibit';
  sourcePacket.speaker_type = 'company management / issuer filing';
  sourcePacket.timing_relevance = 'same-day official quarterly update';
  sourcePacket.catalyst = 'Tesla quarterly earnings update';
  sourcePacket.time_sensitivity = 'high';
  sourcePacket.why_valid_under_kalshi_rules =
    'Kalshi earnings-mention rules are governed by the official issuer update, transcript, or replay; a public SEC 8-K exhibit from Tesla is a primary official source.';
  sourcePacket.reasoning_chain = [
    'Tesla filed an official 8-K on the earnings date and attached Exhibit 99.1 as the company update.',
    'The exhibit is an issuer-posted primary source, which is the correct source class for an earnings mention market.',
  ];
  sourcePacket.invalidation_condition =
    'If the settlement rule names a different controlling source or a later official transcript/replay supersedes the exhibit, re-evaluate the packet.';
  sourcePacket.official_source_candidates = [];

  try {
    const submissions = await fetchJson('https://data.sec.gov/submissions/CIK0001318605.json', options);
    const recent = submissions?.filings?.recent ?? {};
    const forms = Array.isArray(recent.form) ? recent.form : [];
    const filingDates = Array.isArray(recent.filingDate) ? recent.filingDate : [];
    const accessionNumbers = Array.isArray(recent.accessionNumber) ? recent.accessionNumber : [];
    const primaryDocuments = Array.isArray(recent.primaryDocument) ? recent.primaryDocument : [];
    const eightKIndex = forms.findIndex(form => String(form).toUpperCase() === '8-K');

    if (eightKIndex < 0) {
      sourcePacket.unresolved_gaps = ['No recent Tesla 8-K located in SEC submissions feed'];
      return sourcePacket;
    }

    const accessionNumber = accessionNumbers[eightKIndex] ?? null;
    const primaryDocument = primaryDocuments[eightKIndex] ?? null;
    const filingDate = filingDates[eightKIndex] ?? null;

    if (!accessionNumber || !primaryDocument) {
      sourcePacket.unresolved_gaps = ['Tesla 8-K filing metadata incomplete'];
      return sourcePacket;
    }

    const accessionPath = String(accessionNumber).replace(/-/g, '');
    const filingUrl = `https://www.sec.gov/Archives/edgar/data/${TESLA_CIK}/${accessionPath}/${primaryDocument}`;
    sourcePacket.official_source_candidates.push({
      url: filingUrl,
      type: 'sec_8k_filing',
      label: `Tesla 8-K filing ${filingDate ?? ''}`.trim(),
    });

    const filingHtml = await fetchText(filingUrl, options);
    const exhibitHref = filingHtml.match(/href=["']([^"']*exhibit99?1[^"']*)["']/i)?.[1] ?? null;
    const exhibitUrl = safeUrl(filingUrl, exhibitHref);

    if (exhibitUrl) {
      sourcePacket.official_source_candidates.push({
        url: exhibitUrl,
        type: 'sec_8k_exhibit_99_1',
        label: 'Tesla Exhibit 99.1 Q1 2026 Update',
      });
      sourcePacket.official_source_url = exhibitUrl;
      sourcePacket.official_source_type = 'sec_8k_exhibit_99_1';

      const exhibitHtml = await fetchText(exhibitUrl, options);
      const exhibitText = stripHtml(exhibitHtml);
      const targetPhrase = metadata.target_phrase ?? input.question ?? input.title ?? null;
      const phraseCandidates = uniqueStrings([
        targetPhrase,
        metadata.target_phrase,
        'FSD / Full Self Driving',
        'FSD (Supervised)',
        'Full Self Driving',
        'Full Self-Driving',
        'Optimus',
        'Robotaxi',
        'Battery',
        'Delivery',
      ]);
      const snippet = extractSnippet(exhibitText, phraseCandidates);
      const phraseFound = Boolean(snippet);
      sourcePacket.transcript_excerpt = snippet;
      sourcePacket.exact_phrase_status = phraseFound ? 'found' : 'not_found';
      sourcePacket.unresolved_gaps = phraseFound
        ? []
        : ['Exact target phrase was not found in the official Tesla exhibit text'];
      sourcePacket.reasoning_chain = [
        ...sourcePacket.reasoning_chain,
        phraseFound
          ? 'The requested phrase or a close phrase variant appears in the official exhibit text.'
          : 'The exact phrase was not found in the official exhibit text, so the result should be downgraded or left on watch.',
      ];
    } else {
      sourcePacket.official_source_url = filingUrl;
      sourcePacket.official_source_type = 'sec_8k_filing';
      sourcePacket.transcript_excerpt = null;
      sourcePacket.exact_phrase_status = 'not_found';
      sourcePacket.unresolved_gaps = ['Exhibit 99.1 link was not found in the Tesla 8-K filing'];
    }

    sourcePacket.research_summary = sourcePacket.transcript_excerpt
      ? 'Tesla official issuer filing contains source text relevant to the mention market.'
      : 'Tesla official issuer filing was located, but the exact phrase was not extracted.';

    return sourcePacket;
  } catch (error) {
    sourcePacket.unresolved_gaps = [error instanceof Error ? error.message : 'Tesla source fetch failed'];
    return sourcePacket;
  }
}

function buildMacroSourcePacket(input = {}) {
  const packet = buildBasePacket(input);
  packet.source_packet_kind = 'macro';
  packet.event_domain = 'macro';
  packet.event_type = 'official_release';
  packet.market_type = 'macro';
  packet.event_format = 'official macro release';
  packet.speaker_type = 'government agency / central bank';
  packet.timing_relevance = 'release-date dependent';
  packet.source_quality = 'medium';
  packet.evidence_strength = 'medium';
  packet.why_valid_under_kalshi_rules =
    'Macro markets should rely on the named official release, central bank statement, or official data publication that controls settlement.';
  packet.reasoning_chain = [
    'Macro markets should reason from the official release page or central-bank publication named in the rules.',
    'If the exact release page is not yet known, the packet should carry authoritative candidates rather than commentary.',
  ];
  packet.official_source_candidates = [];

  const text = inferMarketText(input);
  if (/\bcpi\b|inflation|price index/.test(text)) {
    packet.official_source_candidates.push({
      url: 'https://www.bls.gov/cpi/',
      type: 'bls_release_landing_page',
      label: 'BLS Consumer Price Index',
    });
  }
  if (/\bppi\b|producer price/.test(text)) {
    packet.official_source_candidates.push({
      url: 'https://www.bls.gov/ppi/',
      type: 'bls_release_landing_page',
      label: 'BLS Producer Price Index',
    });
  }
  if (/\bjobs\b|employment|unemployment/.test(text)) {
    packet.official_source_candidates.push({
      url: 'https://www.bls.gov/news.release/empsit.toc.htm',
      type: 'bls_release_landing_page',
      label: 'BLS Employment Situation',
    });
  }
  if (/\bgdp\b/.test(text)) {
    packet.official_source_candidates.push({
      url: 'https://www.bea.gov/data/gdp/gross-domestic-product',
      type: 'bea_release_landing_page',
      label: 'BEA Gross Domestic Product',
    });
  }
  if (/\bfomc\b|\bfed\b|rates|powell/.test(text)) {
    packet.official_source_candidates.push({
      url: 'https://www.federalreserve.gov/newsevents/pressreleases.htm',
      type: 'fed_press_release_landing_page',
      label: 'Federal Reserve press releases',
    });
  }
  if (/treasury|yield|auction/.test(text)) {
    packet.official_source_candidates.push({
      url: 'https://home.treasury.gov/',
      type: 'treasury_release_landing_page',
      label: 'U.S. Treasury',
    });
  }
  if (/sec|earnings|quarter|guidance|transcript/.test(text)) {
    packet.official_source_candidates.push({
      url: 'https://www.sec.gov/',
      type: 'sec_release_landing_page',
      label: 'SEC filings and releases',
    });
  }

  if (packet.official_source_candidates.length === 0) {
    packet.unresolved_gaps = ['Macro source classification is still broad; need the exact release page from rules or board wording.'];
  }

  return packet;
}

function buildGenericMentionSourcePacket(input = {}) {
  const packet = buildBasePacket(input);
  packet.source_packet_kind = 'mention';
  packet.event_domain = 'mention';
  packet.event_type = 'mention';
  packet.market_type = 'mention';
  packet.event_format = 'live remarks / replay / transcript';
  packet.speaker_type = 'allowed speaker from board rules';
  packet.timing_relevance = 'board window dependent';
  packet.source_quality = 'medium';
  packet.evidence_strength = 'low';
  packet.why_valid_under_kalshi_rules =
    'Mention markets should rely on the exact live source named by the rules, usually a transcript, replay, or official video/captions when the rules allow them.';
  packet.reasoning_chain = [
    'The board wording should determine whether the source is a transcript, video, replay, or official captions.',
    'Secondary commentary can locate the source, but only the official source can settle the phrase.',
  ];
  packet.official_source_candidates = [
    { url: input.resolution_source ?? null, type: 'board_named_source', label: 'Source named by board rules' },
  ].filter(candidate => Boolean(candidate.url));

  if (packet.official_source_candidates.length === 0) {
    packet.unresolved_gaps = ['Exact official source URL not yet identified for this mention market.'];
  }

  return packet;
}

export async function buildOfficialSourcePacket(input = {}, options = {}) {
  if (isTeslaEarningsMarket(input)) {
    return buildTeslaEarningsSourcePacket(input, options);
  }

  if (isMacroMarket(input)) {
    return buildMacroSourcePacket(input);
  }

  if (String(input.domain ?? '').toLowerCase() === 'mention' || /(earnings|transcript|replay|video)/.test(inferMarketText(input))) {
    return buildGenericMentionSourcePacket(input);
  }

  return buildBasePacket(input);
}
