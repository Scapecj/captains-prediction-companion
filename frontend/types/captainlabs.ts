export type SurfaceName = 'companion' | 'dashboard' | 'bot-dash'

export interface UserProfile {
  name?: string | null
  email?: string | null
  role?: string | null
}

export interface UserPreferences {
  defaultSurface?: SurfaceName
  theme?: 'dark' | 'light' | string
  walletFirstOnboarding?: boolean
}

export interface User {
  id: string
  profile: UserProfile
  preferences: UserPreferences
}

export interface Wallet {
  id: string
  userId: string
  label: string
  address: string
  chain: string
  createdAt: string
}

export type BotType = 'wallet_only' | 'api_connected' | 'internal_bot'
export type BotStatus = 'active' | 'paused' | 'error' | 'disconnected'

export interface BotProfile {
  id: string
  userId: string
  name: string
  type: BotType
  status: BotStatus
  strategyLabel: string
  walletAddress: string | null
  chain: string
  exchange: string
  apiBaseUrl: string | null
  lastHeartbeatAt: string | null
  createdAt: string
  updatedAt: string
}

export type OwnerType = 'user' | 'bot'
export type PositionSide = 'yes' | 'no' | 'watch' | 'hold'
export type PositionStatus = 'open' | 'closed' | 'pending' | 'partial'

export interface Position {
  id: string
  ownerType: OwnerType
  ownerId: string
  market: string
  side: PositionSide
  entryPrice: number
  currentPrice: number
  quantity: number
  pnlDollars: number
  pnlPercent: number
  status: PositionStatus | string
  openedAt: string
  updatedAt: string
}

export interface BotAction {
  id: string
  botId: string
  timestamp: string
  type: string
  market: string
  price: number | null
  quantity: number
  reason: string | null
}

export interface PerformanceSnapshot {
  id?: string
  ownerType: OwnerType
  ownerId: string
  totalPnl: number
  todayPnl: number
  winRate: number
  tradesToday: number
  openPositions: number
  updatedAt: string
}

export type CompanionInputType = 'market_url' | 'wallet' | 'position' | 'freeform'

export interface CompanionRequest {
  id: string
  userId: string
  inputType: CompanionInputType
  inputValue: string
  responseSummary: string
  createdAt: string
}

export interface DashboardSummary {
  user: User | null
  summary: {
    walletCount: number
    botCount: number
    activeBots: number
    openPositions: number
    totalPnl: number
    todayPnl: number
    winRate: number
    tradesToday: number
    updatedAt: string
  }
}

export interface DashboardPerformance {
  user: PerformanceSnapshot
  bots: Array<PerformanceSnapshot & { botId: string; botName: string }>
}

export interface DashboardResponseSet {
  summary: DashboardSummary
  positions: Position[]
  activity: Array<Record<string, unknown>>
  performance: DashboardPerformance
  wallets: Array<Wallet & { positionCount?: number; performance?: PerformanceSnapshot | null }>
}

export interface BotListItem extends BotProfile {
  positionCount?: number
  actionCount?: number
  lastAction?: string | null
  lastUpdate?: string | null
}

export interface BotStatusSnapshot {
  status?: BotStatus | string
  strategyLabel?: string
  lastAction?: string | null
  lastUpdate?: string | null
}

export interface BotOverview {
  bot: BotProfile
  status: BotStatusSnapshot | null
  positions: Position[]
  actions: BotAction[]
  performance: PerformanceSnapshot | null
  logs: string[]
}
