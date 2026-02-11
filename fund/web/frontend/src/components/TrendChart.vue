<script setup lang="ts">
import { computed } from 'vue'
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { LineChart } from 'echarts/charts'
import { GridComponent, TooltipComponent, LegendComponent, DataZoomComponent } from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'
import type { ProductHistory } from '../api'

use([LineChart, GridComponent, TooltipComponent, LegendComponent, DataZoomComponent, CanvasRenderer])

const props = defineProps<{
  series: ProductHistory[]
  title?: string
}>()

const COLORS = [
  '#3b82f6', '#ef4444', '#10b981', '#f59e0b', '#8b5cf6',
  '#ec4899', '#06b6d4', '#84cc16', '#f97316', '#6366f1',
]

const chartOption = computed(() => {
  if (!props.series.length) return null

  // Collect all unique dates
  const dateSet = new Set<string>()
  for (const s of props.series) {
    for (const h of s.history) dateSet.add(h.as_of_date)
  }
  const dates = Array.from(dateSet).sort()

  const seriesData = props.series.map((s, idx) => {
    const valMap = new Map(s.history.map(h => [h.as_of_date, h.annualized_7d]))
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
