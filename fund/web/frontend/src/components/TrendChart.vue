<script setup lang="ts">
import { computed } from 'vue'
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { LineChart } from 'echarts/charts'
import { GridComponent, TooltipComponent, LegendComponent, DataZoomComponent } from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'
import type { ProductHistory, HistoryPoint } from '../api'

use([LineChart, GridComponent, TooltipComponent, LegendComponent, DataZoomComponent, CanvasRenderer])

const props = defineProps<{
  series: ProductHistory[]
  title?: string
}>()

const COLORS = [
  '#3b82f6', '#ef4444', '#10b981', '#f59e0b', '#8b5cf6',
  '#ec4899', '#06b6d4', '#84cc16', '#f97316', '#6366f1',
]

/** 从累计净值历史计算各日期的七日年化：向前找约7天的净值，(nav_today/nav_7d_ago - 1) * (365/actual_days) * 100 */
function compute7dAnnualizedFromNav(history: HistoryPoint[]): Map<string, number> {
  const sorted = [...history]
    .filter((h): h is HistoryPoint & { cumulative_nav: number } =>
      h.cumulative_nav != null && h.cumulative_nav !== 1.0
    )
    .sort((a, b) => a.as_of_date.localeCompare(b.as_of_date))
  const result = new Map<string, number>()
  for (let i = 0; i < sorted.length; i++) {
    const cur = sorted[i]!
    const curDate = new Date(cur.as_of_date).getTime()
    const targetDate = curDate - 7 * 86400000
    let best: (typeof sorted)[0] | null = null
    for (let j = i - 1; j >= 0; j--) {
      const d = new Date(sorted[j]!.as_of_date).getTime()
      if (d <= targetDate + 86400000) {
        best = sorted[j]!
        break
      }
    }
    if (!best) continue
    const actualDays = Math.max(1, (curDate - new Date(best.as_of_date).getTime()) / 86400000)
    const growth = cur.cumulative_nav / best.cumulative_nav - 1
    const annualized = growth * (365 / Math.min(actualDays, 14)) * 100
    result.set(cur.as_of_date, Number(annualized.toFixed(4)))
  }
  return result
}

/** 获取产品在各日期的七日年化：优先用原始 annualized_7d，净值型且为空时用累计净值推算 */
function getAnnualized7dMap(s: ProductHistory): Map<string, number | null> {
  const directMap = new Map(s.history.map(h => [h.as_of_date, h.annualized_7d]))
  const hasDirect = [...directMap.values()].some(v => v != null)
  if (hasDirect) return directMap
  // 净值型产品无直接七日年化，从累计净值推算
  const computed = compute7dAnnualizedFromNav(s.history)
  if (computed.size === 0) return directMap
  const result = new Map<string, number | null>()
  for (const [d, v] of directMap) result.set(d, v)
  for (const [d, v] of computed) {
    if (!result.has(d) || result.get(d) == null) result.set(d, v)
  }
  return result
}

const chartOption = computed(() => {
  if (!props.series.length) return null

  // Collect all unique dates
  const dateSet = new Set<string>()
  for (const s of props.series) {
    for (const h of s.history) dateSet.add(h.as_of_date)
  }
  const dates = Array.from(dateSet).sort()

  const seriesData = props.series.map((s, idx) => {
    const valMap = getAnnualized7dMap(s)
    return {
      name: s.product_name || s.product_code,
      type: 'line' as const,
      smooth: true,
      symbol: 'circle',
      symbolSize: 4,
      lineStyle: { width: 2 },
      itemStyle: { color: COLORS[idx % COLORS.length] },
      data: dates.map(d => valMap.get(d) ?? null),
      connectNulls: true,
    }
  })

  return {
    tooltip: {
      trigger: 'axis',
      valueFormatter: (v: any) => (v != null ? v.toFixed(4) + '%' : '-'),
    },
    legend: {
      bottom: 0,
      type: 'scroll',
      textStyle: { fontSize: 12 },
    },
    grid: { top: 16, right: 16, bottom: 40, left: 50 },
    xAxis: {
      type: 'category',
      data: dates,
      axisLabel: { fontSize: 11, rotate: dates.length > 30 ? 45 : 0 },
      boundaryGap: false,
    },
    yAxis: {
      type: 'value',
      axisLabel: { fontSize: 11, formatter: '{value}%' },
      splitLine: { lineStyle: { type: 'dashed', color: '#e5e7eb' } },
      min: 'dataMin',
    },
    dataZoom: dates.length > 60 ? [{ type: 'inside' }, { type: 'slider', bottom: 32 }] : [],
    series: seriesData,
  }
})
</script>

<template>
  <div class="bg-white rounded-xl shadow-sm border border-gray-100 p-4">
    <h3 v-if="title" class="text-base font-semibold text-gray-800 mb-3">{{ title }}</h3>
    <div v-if="!chartOption" class="text-gray-400 text-sm py-12 text-center">暂无数据</div>
    <div v-else class="h-80">
      <v-chart :option="chartOption" autoresize class="w-full h-full" />
    </div>
  </div>
</template>
