import { buildFocusedKalshiMarketPlan, buildEventMarketPlanSummary } from './eventMarketTool.js'

function sendJson(res, statusCode, payload) {
  res.writeHead(statusCode, { 'content-type': 'application/json' })
  res.end(JSON.stringify(payload))
}

function normalizePath(url) {
  try {
    return new URL(url, 'http://localhost').pathname
  } catch {
    return url
  }
}

function parseJsonBody(req) {
  return new Promise((resolve, reject) => {
    const chunks = []
    req.on('data', (chunk) => chunks.push(chunk))
    req.on('end', () => {
      const raw = Buffer.concat(chunks).toString('utf8').trim()
      if (!raw) {
        resolve({})
        return
      }
      try {
        resolve(JSON.parse(raw))
      } catch (error) {
        reject(error)
      }
    })
    req.on('error', reject)
  })
}

function defaultUser(store) {
  return store.getUser?.() ?? null
}

function buildCompanionRequest(store, inputType, inputValue, responseSummary) {
  const user = defaultUser(store)
  return store.addCompanionHistory?.({
    userId: user?.id,
    inputType,
    inputValue,
    responseSummary,
  })
}

function resolveDashboardUserId(store, explicitUserId) {
  if (typeof explicitUserId === 'string' && explicitUserId.trim()) {
    return explicitUserId.trim()
  }
  return defaultUser(store)?.id ?? 'user-1'
}

async function analyzeMarket(store, body) {
  const url = String(body?.inputValue ?? body?.url ?? '').trim()
  if (!url) {
    return { statusCode: 400, payload: { error: 'inputValue or url is required' } }
  }

  const result = await buildFocusedKalshiMarketPlan(
    { url },
    { pipelineService: null }
  )
  const summary = buildEventMarketPlanSummary(result)
  const request = buildCompanionRequest(
    store,
    'market_url',
    url,
    summary?.summary?.one_line_reason ?? summary?.board_headline ?? 'Market analyzed.'
  )

  return {
    statusCode: 200,
    payload: {
      request,
      analysis: summary,
      responseSummary: request.responseSummary,
    },
  }
}

function analyzeWallet(store, body) {
  const userId = resolveDashboardUserId(store, body?.userId)
  const wallets = store.listWallets?.(userId) ?? []
  const walletId = String(body?.walletId ?? '').trim()
  const walletAddress = String(body?.inputValue ?? body?.address ?? '').trim()
  const wallet = walletId
    ? store.getWallet?.(walletId)
    : wallets.find((item) => item.address === walletAddress) ?? wallets[0] ?? null

  if (!wallet) {
    return { statusCode: 404, payload: { error: 'Wallet not found' } }
  }

  const performance = store.getWalletPerformance?.(wallet.id)
  const positions = store.getWalletPositions?.(wallet.id) ?? []
  const activity = store.getWalletActivity?.(wallet.id) ?? []
  const responseSummary = `${wallet.label} is connected to ${positions.length} positions and ${performance?.openPositions ?? 0} open positions.`
  const request = buildCompanionRequest(store, 'wallet', wallet.address, responseSummary)

  return {
    statusCode: 200,
    payload: {
      request,
      wallet,
      positions,
      activity,
      performance,
      responseSummary,
    },
  }
}

function analyzePosition(store, body) {
  const userId = resolveDashboardUserId(store, body?.userId)
  const positionId = String(body?.positionId ?? body?.inputValue ?? '').trim()
  const positions = store.listDashboardPositions?.(userId) ?? []
  const position = positionId
    ? positions.find((item) => item.id === positionId) ?? positions.find((item) => item.market === positionId)
    : positions[0] ?? null

  if (!position) {
    return { statusCode: 404, payload: { error: 'Position not found' } }
  }

  const responseSummary = `${position.market} is ${position.status} with ${position.pnlDollars >= 0 ? 'positive' : 'negative'} pnl.`
  const request = buildCompanionRequest(store, 'position', position.id, responseSummary)

  return {
    statusCode: 200,
    payload: {
      request,
      position,
      responseSummary,
    },
  }
}

function analyzeFreeform(store, body) {
  const inputValue = String(body?.inputValue ?? body?.message ?? '').trim() || 'freeform request'
  const responseSummary = `Captured companion request: ${inputValue}`
  const request = buildCompanionRequest(store, 'freeform', inputValue, responseSummary)
  return {
    statusCode: 200,
    payload: {
      request,
      responseSummary,
    },
  }
}

function isBotIdPath(parts) {
  return parts[0] === 'bots' && typeof parts[1] === 'string' && parts[1].length > 0
}

function isWalletIdPath(parts) {
  return parts[0] === 'wallets' && typeof parts[1] === 'string' && parts[1].length > 0
}

export async function handleCaptainLabsApiRequest(req, res, store) {
  const pathname = normalizePath(req.url ?? '/')
  const parts = pathname.split('/').filter(Boolean)
  if (parts.length === 0) return false

  const method = (req.method ?? 'GET').toUpperCase()
  const userId = resolveDashboardUserId(store)

  if (parts[0] === 'companion') {
    if (method === 'POST' && parts[1] === 'analyze-market') {
      const body = await parseJsonBody(req)
      const result = await analyzeMarket(store, body)
      sendJson(res, result.statusCode, result.payload)
      return true
    }

    if (method === 'POST' && parts[1] === 'analyze-wallet') {
      const body = await parseJsonBody(req)
      const result = analyzeWallet(store, body)
      sendJson(res, result.statusCode, result.payload)
      return true
    }

    if (method === 'POST' && parts[1] === 'analyze-position') {
      const body = await parseJsonBody(req)
      const result = analyzePosition(store, body)
      sendJson(res, result.statusCode, result.payload)
      return true
    }

    if (method === 'POST' && parts[1] === 'analyze') {
      const body = await parseJsonBody(req)
      const inputType = String(body?.inputType ?? '').trim()
      let result
      if (inputType === 'market_url' || body?.url) {
        result = await analyzeMarket(store, body)
      } else if (inputType === 'wallet') {
        result = analyzeWallet(store, body)
      } else if (inputType === 'position') {
        result = analyzePosition(store, body)
      } else {
        result = analyzeFreeform(store, body)
      }
      sendJson(res, result.statusCode, result.payload)
      return true
    }

    if (method === 'GET' && parts[1] === 'history') {
      sendJson(res, 200, {
        history: store.listCompanionHistory?.(userId) ?? [],
      })
      return true
    }
  }

  if (parts[0] === 'dashboard') {
    if (method === 'GET' && parts[1] === 'summary') {
      sendJson(res, 200, store.getDashboardSummary?.(userId) ?? {})
      return true
    }
    if (method === 'GET' && parts[1] === 'positions') {
      sendJson(res, 200, { positions: store.listDashboardPositions?.(userId) ?? [] })
      return true
    }
    if (method === 'GET' && parts[1] === 'activity') {
      sendJson(res, 200, { activity: store.getDashboardActivity?.(userId) ?? [] })
      return true
    }
    if (method === 'GET' && parts[1] === 'performance') {
      sendJson(res, 200, { performance: store.getDashboardPerformance?.(userId) ?? null })
      return true
    }
    if (method === 'GET' && parts[1] === 'wallets') {
      sendJson(res, 200, { wallets: store.getWalletListItems?.(userId) ?? [] })
      return true
    }
  }

  if (parts[0] === 'bots') {
    if (parts.length === 1 && method === 'GET') {
      sendJson(res, 200, { bots: store.getBotListItems?.(userId) ?? [] })
      return true
    }

    if (parts.length === 1 && method === 'POST') {
      const body = await parseJsonBody(req)
      const bot = store.createBot?.({ ...body, userId })
      sendJson(res, bot ? 201 : 400, bot ?? { error: 'Unable to create bot' })
      return true
    }

    if (!isBotIdPath(parts)) {
      return false
    }

    const botId = parts[1]
    const bot = store.getBot?.(botId)
    if (!bot) {
      sendJson(res, 404, { error: 'Bot not found' })
      return true
    }

    if (parts.length === 2 && method === 'GET') {
      sendJson(res, 200, store.getBotOverview?.(botId) ?? { bot })
      return true
    }

    if (parts.length === 2 && method === 'PATCH') {
      const body = await parseJsonBody(req)
      const updated = store.updateBot?.(botId, body)
      sendJson(res, updated ? 200 : 404, updated ?? { error: 'Bot not found' })
      return true
    }

    if (parts[2] === 'status' && method === 'GET') {
      sendJson(res, 200, { status: store.getBotStatus?.(botId) })
      return true
    }

    if (parts[2] === 'positions' && method === 'GET') {
      sendJson(res, 200, { positions: store.listBotPositions?.(botId) ?? [] })
      return true
    }

    if (parts[2] === 'actions' && method === 'GET') {
      sendJson(res, 200, { actions: store.getBotActions?.(botId) ?? [] })
      return true
    }

    if (parts[2] === 'performance' && method === 'GET') {
      sendJson(res, 200, { performance: store.getBotPerformance?.(botId) ?? null })
      return true
    }

    if (parts[2] === 'logs' && method === 'GET') {
      sendJson(res, 200, { logs: store.getBotLogs?.(botId) ?? [] })
      return true
    }

    if (parts[2] === 'start' && method === 'POST') {
      const updated = store.startBot?.(botId)
      sendJson(res, updated ? 200 : 404, updated ? { bot: updated, status: store.getBotStatus?.(botId) } : { error: 'Bot not found' })
      return true
    }

    if (parts[2] === 'stop' && method === 'POST') {
      const updated = store.stopBot?.(botId)
      sendJson(res, updated ? 200 : 404, updated ? { bot: updated, status: store.getBotStatus?.(botId) } : { error: 'Bot not found' })
      return true
    }
  }

  if (parts[0] === 'wallets') {
    if (parts.length === 1 && method === 'GET') {
      sendJson(res, 200, { wallets: store.getWalletListItems?.(userId) ?? [] })
      return true
    }

    if (parts.length === 1 && method === 'POST') {
      const body = await parseJsonBody(req)
      const wallet = store.createWallet?.({ ...body, userId })
      sendJson(res, wallet ? 201 : 400, wallet ?? { error: 'Unable to create wallet' })
      return true
    }

    if (!isWalletIdPath(parts)) {
      return false
    }

    const walletId = parts[1]
    const wallet = store.getWallet?.(walletId)
    if (!wallet) {
      sendJson(res, 404, { error: 'Wallet not found' })
      return true
    }

    if (parts.length === 2 && method === 'DELETE') {
      const deleted = store.deleteWallet?.(walletId)
      sendJson(res, deleted ? 200 : 404, deleted ? { wallet: deleted } : { error: 'Wallet not found' })
      return true
    }

    if (parts[2] === 'positions' && method === 'GET') {
      sendJson(res, 200, { positions: store.getWalletPositions?.(walletId) ?? [] })
      return true
    }

    if (parts[2] === 'activity' && method === 'GET') {
      sendJson(res, 200, { activity: store.getWalletActivity?.(walletId) ?? [] })
      return true
    }

    if (parts[2] === 'performance' && method === 'GET') {
      sendJson(res, 200, { performance: store.getWalletPerformance?.(walletId) ?? null })
      return true
    }
  }

  return false
}
