<script setup lang="ts">
import { computed } from 'vue'
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { LineChart } from 'echarts/charts'
import {
  GridComponent,
  TooltipComponent,
  LegendComponent,
  DataZoomComponent,
  MarkLineComponent,
} from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'
import type { ProductHistory, HistoryPoint } from '../api'

use([
  LineChart,
  GridComponent,
  TooltipComponent,
  LegendComponent,
  DataZoomComponent,
  MarkLineComponent,
  CanvasRenderer,
])

const props = defineProps<{
  series: ProductHistory[]
  title?: string
  /** 图表高度 class，默认 h-80 */
  heightClass?: string
}>()

const COLORS = [
  '#3b82f6', '#ef4444', '#10b981', '#f59e0b', '#8b5cf6',
  '#ec4899', '#06b6d4', '#84cc16', '#f97316', '#6366f1',
]

/** 判断一个产品是否是现金管理类（cumulative_nav 全为 1.0 或全为 null） */
function isCashProduct(history: HistoryPoint[]): boolean {
  return history.every(
    h => h.cumulative_nav == null || h.cumulative_nav === 1.0
  )
}

/** 归一化到基准 100 */
function rebaseToHundred(history: HistoryPoint[]) {
  const valid = history.filter(
    (h): h is HistoryPoint & { cumulative_nav: number } =>
      h.cumulative_nav != null && h.cumulative_nav !== 1.0
  )
  if (valid.length === 0) return []
  const first = valid[0]
  if (!first) return []
  const base = first.cumulative_nav
  return valid.map(h => ({
    date: h.as_of_date,
    value: Number(((h.cumulative_nav / base) * 100).toFixed(4)),
    rawNav: h.cumulative_nav,
  }))
}

/** 是否为多产品模式 */
const isMulti = computed(() => props.series.length > 1)

/** 现金管理类产品列表（降级显示七日年化） */
const cashProducts = computed(() =>
  props.series.filter(s => isCashProduct(s.history))
)

/** 净值型产品列表 */
const navProducts = computed(() =>
  props.series.filter(s => !isCashProduct(s.history))
)

const chartOption = computed(() => {
  if (!props.series.length) return null

  // 多产品模式：归一化对比
  if (isMulti.value) {
    return buildMultiChart()
  }
  // 单产品模式
  return buildSingleChart()
})

function buildSingleChart() {
  const s = props.series[0]
  if (!s) return null
  const isCash = isCashProduct(s.history)

  if (isCash) {
    // 现金管理类：展示七日年化走势
    const points = s.history.filter(h => h.annualized_7d != null)
    if (points.length === 0) return null
    const dates = points.map(h => h.as_of_date)
    return {
      tooltip: {
        trigger: 'axis',
        valueFormatter: (v: any) => (v != null ? v.toFixed(4) + '%' : '-'),
      },
      grid: { top: 16, right: 16, bottom: 24, left: 55 },
      xAxis: {
        type: 'category',
        data: dates,
        axisLabel: { fontSize: 11, rotate: dates.length > 20 ? 45 : 0 },
        boundaryGap: false,
      },
      yAxis: {
        type: 'value',
        axisLabel: { fontSize: 11, formatter: '{value}%' },
        splitLine: { lineStyle: { type: 'dashed', color: '#e5e7eb' } },
        min: 'dataMin',
      },
      series: [
        {
          name: '七日年化',
          type: 'line',
          smooth: true,
          symbol: 'circle',
          symbolSize: 4,
          lineStyle: { width: 2 },
          itemStyle: { color: COLORS[0] },
          areaStyle: { color: 'rgba(59,130,246,0.08)' },
          data: points.map(h => h.annualized_7d),
          connectNulls: true,
        },
      ],
    }
  }

  // 净值型：展示累计净值走势
  const points = s.history.filter(h => h.cumulative_nav != null && h.cumulative_nav !== 1.0)
  if (points.length === 0) return null
  const dates = points.map(h => h.as_of_date)
  const navValues = points.map(h => h.cumulative_nav!)

  return {
    tooltip: {
      trigger: 'axis',
      valueFormatter: (v: any) => (v != null ? v.toFixed(6) : '-'),
    },
    grid: { top: 16, right: 16, bottom: 24, left: 65 },
    xAxis: {
      type: 'category',
      data: dates,
      axisLabel: { fontSize: 11, rotate: dates.length > 20 ? 45 : 0 },
      boundaryGap: false,
    },
    yAxis: {
      type: 'value',
      axisLabel: { fontSize: 11 },
      splitLine: { lineStyle: { type: 'dashed', color: '#e5e7eb' } },
      min: 'dataMin',
    },
    series: [
      {
        name: '累计净值',
        type: 'line',
        smooth: true,
        symbol: 'circle',
        symbolSize: 4,
        lineStyle: { width: 2 },
        itemStyle: { color: COLORS[0] },
        areaStyle: { color: 'rgba(59,130,246,0.08)' },
        data: navValues,
        connectNulls: true,
      },
    ],
  }
}

function buildMultiChart() {
  // 收集所有日期
  const dateSet = new Set<string>()
  for (const s of props.series) {
    for (const h of s.history) dateSet.add(h.as_of_date)
  }
  const dates = Array.from(dateSet).sort()

  // 构建各产品的归一化数据
  const seriesData = props.series.map((s, idx) => {
    const isCash = isCashProduct(s.history)
    const label = s.product_name || s.product_code

    if (isCash) {
      // 现金管理类：用七日年化数据，标记为降级
      const valMap = new Map(s.history.map(h => [h.as_of_date, h.annualized_7d]))
      return {
        name: label + ' (年化%)',
        type: 'line' as const,
        smooth: true,
        symbol: 'circle',
        symbolSize: 4,
        lineStyle: { width: 2, type: 'dashed' as const },
        itemStyle: { color: COLORS[idx % COLORS.length] },
        data: dates.map(d => valMap.get(d) ?? null),
        connectNulls: true,
        yAxisIndex: 1,
        _isCash: true,
      }
    }

    // 净值型：归一化到 100
    const rebased = rebaseToHundred(s.history)
    const valMap = new Map(rebased.map(r => [r.date, r.value]))
    const rawMap = new Map(rebased.map(r => [r.date, r.rawNav]))

    return {
      name: label,
      type: 'line' as const,
      smooth: true,
      symbol: 'circle',
      symbolSize: 4,
      lineStyle: { width: 2 },
      itemStyle: { color: COLORS[idx % COLORS.length] },
      data: dates.map(d => valMap.get(d) ?? null),
      connectNulls: true,
      yAxisIndex: 0,
      _isCash: false,
      _rawMap: rawMap,
    }
  })

  const hasCash = seriesData.some((s: any) => s._isCash)
  const hasNav = seriesData.some((s: any) => !s._isCash)

  // 构建 Y 轴
  const yAxes: any[] = [
    {
      type: 'value',
      name: hasNav ? '归一化净值' : '',
      axisLabel: { fontSize: 11 },
      splitLine: { lineStyle: { type: 'dashed', color: '#e5e7eb' } },
      min: hasNav ? 'dataMin' : undefined,
    },
  ]
  if (hasCash) {
    yAxes.push({
      type: 'value',
      name: '七日年化(%)',
      position: 'right',
      axisLabel: { fontSize: 11, formatter: '{value}%' },
      splitLine: { show: false },
      min: 'dataMin',
    })
  }

  // Tooltip 格式化
  const tooltip = {
    trigger: 'axis',
    formatter: (params: any) => {
      if (!Array.isArray(params) || params.length === 0) return ''
      let html = `<div style="font-weight:600;margin-bottom:4px">${params[0].axisValue}</div>`
      for (const p of params) {
        if (p.value == null) continue
        const dot = `<span style="display:inline-block;width:10px;height:10px;border-radius:50%;background:${p.color};margin-right:6px"></span>`
        const sd = seriesData[p.seriesIndex] as any
        if (sd._isCash) {
          html += `<div>${dot}${p.seriesName}: ${p.value.toFixed(4)}%</div>`
        } else {
          const rawNav = sd._rawMap?.get(p.axisValue)
          html += `<div>${dot}${p.seriesName}: ${p.value.toFixed(2)}`
          if (rawNav != null) html += ` <span style="color:#999">(净值 ${rawNav.toFixed(6)})</span>`
          html += `</div>`
        }
      }
      return html
    },
  }

  return {
    tooltip,
    legend: {
      bottom: 0,
      type: 'scroll',
      textStyle: { fontSize: 12 },
    },
    grid: { top: 24, right: hasCash ? 70 : 16, bottom: 40, left: 55 },
    xAxis: {
      type: 'category',
      data: dates,
      axisLabel: { fontSize: 11, rotate: dates.length > 30 ? 45 : 0 },
      boundaryGap: false,
    },
    yAxis: yAxes,
    dataZoom: dates.length > 60 ? [{ type: 'inside' }, { type: 'slider', bottom: 32 }] : [],
    series: seriesData.map(({ _isCash, _rawMap, ...rest }: any) => rest),
  }
}

/** 提示信息 */
const cashWarning = computed(() => {
  if (!isMulti.value && props.series.length === 1 && props.series[0] && isCashProduct(props.series[0].history)) {
    return '该产品为现金管理类，净值恒为1.0，已降级展示七日年化收益率走势'
  }
  if (isMulti.value && cashProducts.value.length > 0 && navProducts.value.length > 0) {
    const names = cashProducts.value.map(s => s.product_name || s.product_code).join('、')
    return `${names} 为现金管理类产品（净值恒为1.0），以虚线展示七日年化收益率，使用右侧Y轴`
  }
  if (isMulti.value && cashProducts.value.length > 0 && navProducts.value.length === 0) {
    return '所选产品均为现金管理类（净值恒为1.0），展示七日年化收益率走势'
  }
  return ''
})
</script>

<template>
  <div>
    <div v-if="!chartOption" class="text-gray-400 text-sm py-8 text-center">暂无净值数据</div>
    <template v-else>
      <div v-if="cashWarning" class="mb-2 px-3 py-1.5 bg-amber-50 border border-amber-200 rounded-lg text-xs text-amber-700">
        {{ cashWarning }}
      </div>
      <div :class="heightClass || 'h-80'">
        <v-chart :option="chartOption" autoresize class="w-full h-full" />
      </div>
    </template>
  </div>
</template>
