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

// ---- API calls ----
export async function fetchTop50(limit = 50, risk?: string): Promise<RankingResponse> {
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
