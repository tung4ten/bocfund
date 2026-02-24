import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  timeout: 15000,
})

// ---- Types ----
export interface ProductSnapshot {
  product_code: string
  product_name: string
  unit_nav: number | null
  cumulative_nav: number | null
  income_per_10k: number | null
  annualized_7d: number | null
  daily_growth_rate: number | null
  day_nav_change: number | null  // Added
  as_of_date: string
  annualized_7d_source: 'direct' | 'calculated' | null
  risk_level: string | null
  risk_label: string | null
}

export interface HistoryPoint {
  as_of_date: string
  annualized_7d: number | null
  income_per_10k: number | null
  cumulative_nav: number | null
  daily_growth_rate: number | null
}

export interface ProductHistory {
  product_code: string
  product_name: string
  history: HistoryPoint[]
}

export interface RankingResponse {
  as_of_date: string
  items: ProductSnapshot[]
}

export interface PortfolioResponse {
  products: ProductSnapshot[]
}

export interface CompareResponse {
  series: ProductHistory[]
}

export interface TransactionItem {
  id: number
  product_code: string
  date: string
  shares: number
  amount?: number
  created_at: string
}

export interface DailyIncomePoint {
  date: string
  income: number
  total_asset: number
}

export interface IncomeResponse {
  series: DailyIncomePoint[]
  total_income: number
  current_asset: number
}

// ---- API Functions ----

export async function fetchTransactions(): Promise<TransactionItem[]> {
  const { data } = await api.get<TransactionItem[]>('/transactions')
  return data
}

export async function addTransaction(payload: { product_code: string; date: string; shares: number; amount?: number }): Promise<TransactionItem> {
  const { data } = await api.post<TransactionItem>('/transactions', payload)
  return data
}

export async function deleteTransaction(id: number): Promise<void> {
  await api.delete(`/transactions/${id}`)
}

export async function fetchIncome(): Promise<IncomeResponse> {
  const { data } = await api.get<IncomeResponse>('/transactions/income')
  return data
}

export async function fetchTop50(limit = 50, risk?: string, date?: string): Promise<RankingResponse> {
  const params: Record<string, any> = { limit }
  if (risk) params.risk = risk
  const { data } = await api.get<RankingResponse>('/ranking/top50', { params })
  return data
}

export async function fetchPortfolio(): Promise<PortfolioResponse> {
  const { data } = await api.get<PortfolioResponse>('/portfolio')
  return data
}

export async function fetchPortfolioHistory(days = 30): Promise<CompareResponse> {
  const { data } = await api.get<CompareResponse>('/portfolio/history', { params: { days } })
  return data
}

export async function fetchProductHistory(code: string, days = 30): Promise<ProductHistory> {
  const { data } = await api.get<ProductHistory>(`/products/${code}/history`, { params: { days } })
  return data
}

export async function fetchCompare(codes: string[], days = 30): Promise<CompareResponse> {
  const { data } = await api.get<CompareResponse>('/products/compare', {
    params: { codes: codes.join(','), days },
  })
  return data
}

// ---- Risk Level management ----
export async function setRiskLevel(productCode: string, riskLevel: string) {
  const { data } = await api.put(`/risk-levels/${productCode}`, { risk_level: riskLevel })
  return data
}

export async function deleteRiskLevel(productCode: string) {
  const { data } = await api.delete(`/risk-levels/${productCode}`)
  return data
}
