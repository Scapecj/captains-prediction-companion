import { redirect } from 'next/navigation'

export interface Position {
  position_id: string
  state: string
  target_position: string
  target_question: string
  target_balance: number
  target_unwanted_balance: number
  target_clob_order_id: string | null
  target_clob_filled: boolean
  target_split_tx: string | null
  target_entry_price: number
  target_current_price: number
  target_group_slug: string
  cover_position: string
  cover_question: string
  cover_balance: number
  cover_unwanted_balance: number
  cover_clob_order_id: string | null
  cover_clob_filled: boolean
  cover_split_tx: string | null
  cover_entry_price: number
  cover_current_price: number
  entry_net_cost: number | null
  entry_total_cost: number
  current_value: number
  pnl: number
  pnl_pct: number
  entry_time: string
}

export default function PositionsPage() {
  redirect('/dashboard')
}
