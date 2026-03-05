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
  period_days: number | null
  annualized_7d_source: 'direct' | 'calculated' | null
  risk_level: string | null
  risk_label: string | null
  lockup_period_text: string | null
  lockup_period_days: number | null
  lockup_period_source: 'manual' | 'name' | null
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
  risk_level?: string | null
  lockup_period_text?: string | null
  lockup_period_days?: number | null
  lockup_period_source?: 'manual' | 'name' | null
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

export interface HoldingDetail {
  product_code: string
  product_name: string
  shares: number
  amount: number
  today_income: number
  as_of_date: string
}

export interface IncomeResponse {
  series: DailyIncomePoint[]
  total_income: number
  current_asset: number
  holdings: HoldingDetail[]
}

function toDays(value: number, unit: string) {
  if (unit === '天' || unit === '日') return value
  if (unit === '月' || unit === '个月') return value * 30
  if (unit === '年') return value * 365
  return value
}

const CHINESE_NUMERALS: Record<string, number> = {
  '一': 1, '二': 2, '三': 3, '四': 4, '五': 5,
  '六': 6, '七': 7, '八': 8, '九': 9, '十': 10,
  '十一': 11, '十二': 12, '十八': 18, '二十四': 24,
}

function parseLockupPeriod(productName: string): { text: string; days: number } | null {
  const name = productName.replace(/\s+/g, '')

  // 1. 日日开 / 日开 / 每日开放 / 按日开放式 → 日开（完全流动性，days=1）
  if (/日日开|每日开|按日开|日开|按日开放/.test(name)) {
    return { text: '日开', days: 1 }
  }
  // 注：月月开 / 季季开 / 开放式 描述的是赎回频率而非封闭期，不作为封闭期解析

  // 2. 中文数字月份 + 持有/封闭/锁定，如「三个月持有」
  const cnMatch = name.match(/(十[一二]?|[一二三四五六七八九十])(个月)(持有|封闭|锁定)/)
  if (cnMatch) {
    const cnKey = cnMatch[1] ?? ''
    const months = CHINESE_NUMERALS[cnKey]
    if (months) return { text: `${cnKey}个月`, days: months * 30 }
  }

  // 3. 括号内期限 + 持有/封闭关键词，如「（9个月）最短持有期」「（1年）封闭」
  const parenMatch = name.match(/[（(](\d+)\s*(天|日|个月|月|年)[）)]/)
  if (parenMatch && /(持有|封闭|最短持有|锁定)/.test(name)) {
    const value = Number(parenMatch[1])
    const unit = parenMatch[2] ?? '天'
    return { text: `${value}${unit}`, days: toDays(value, unit) }
  }

  // 4. 关键词 + 数字 + 单位，如「封闭14天」「持有期6个月」「最短持有90天」
  let match = name.match(/(封闭|持有期|最短持有|锁定期?)\s*(\d+)\s*(天|日|个月|月|年)/)
  if (match) {
    const value = Number(match[2])
    const unit = match[3] ?? '天'
    return { text: `${value}${unit}`, days: toDays(value, unit) }
  }

  // 5. 数字 + 单位 + 关键词，如「14天封闭」「6个月持有期」「7天最低持有」
  match = name.match(/(\d+)\s*(天|日|个月|月|年)\s*(封闭|持有期|最短持有|锁定|持有|最低持有)/)
  if (match) {
    const value = Number(match[1])
    const unit = match[2] ?? '天'
    return { text: `${value}${unit}`, days: toDays(value, unit) }
  }

  // 6. 含封闭/持有关键词但未找到明确数字+单位 → 尝试从名称任意位置抓数字+单位
  if (/(封闭|持有期|最短持有|锁定)/.test(name)) {
    match = name.match(/(\d+)\s*(天|日|个月|月|年)/)
    if (match) {
      const value = Number(match[1])
      const unit = match[2] ?? '天'
      return { text: `${value}${unit}`, days: toDays(value, unit) }
    }
  }

  return null
}

/** 从产品名称解析封闭期展示文本，供趋势对比等使用 */
export function getLockupText(productName: string): string | null {
  const parsed = parseLockupPeriod(productName || '')
  return parsed?.text ?? null
}

function withLockupPeriod(item: ProductSnapshot): ProductSnapshot {
  // 手动设置优先，不覆盖
  if (item.lockup_period_source === 'manual' && item.lockup_period_text) {
    return { ...item, lockup_period_source: 'manual' }
  }
  const parsed = parseLockupPeriod(item.product_name || '')
  if (!parsed) {
    return {
      ...item,
      lockup_period_text: null,
      lockup_period_days: null,
      lockup_period_source: null,
    }
  }
  return {
    ...item,
    lockup_period_text: parsed.text,
    lockup_period_days: parsed.days,
    lockup_period_source: 'name',
  }
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
  return { ...data, items: data.items.map(withLockupPeriod) }
}

export async function fetchPortfolio(): Promise<PortfolioResponse> {
  const { data } = await api.get<PortfolioResponse>('/portfolio')
  return { ...data, products: data.products.map(withLockupPeriod) }
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

// ---- Lockup Period management ----
export async function setLockupPeriod(productCode: string, lockupPeriodText: string, lockupPeriodDays?: number) {
  const { data } = await api.put(`/lockup-periods/${productCode}`, {
    lockup_period_text: lockupPeriodText,
    lockup_period_days: lockupPeriodDays ?? undefined,
  })
  return data
}

export async function deleteLockupPeriod(productCode: string) {
  const { data } = await api.delete(`/lockup-periods/${productCode}`)
  return data
}

export async function fetchAdvancedRanking(timePeriodDays = 90, limit = 10000): Promise<ProductSnapshot[]> {
  const params = { time_period_days: timePeriodDays, limit };
  const { data } = await api.get<ProductSnapshot[]>('/ranking/advanced', { params });
  return data.map(withLockupPeriod);
}
