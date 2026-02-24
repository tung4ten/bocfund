<script setup lang="ts">
import { ref, onMounted, watch } from 'vue'
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { LineChart } from 'echarts/charts'
import { GridComponent, TooltipComponent } from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'
import { fetchPortfolio, fetchPortfolioHistory } from '../api'
import type { ProductSnapshot, ProductHistory } from '../api'

use([LineChart, GridComponent, TooltipComponent, CanvasRenderer])

const emit = defineEmits<{
  (e: 'compare', codes: string[]): void
}>()

const products = ref<ProductSnapshot[]>([])
const historyMap = ref<Record<string, ProductHistory>>({})
const loading = ref(true)

async function loadData() {
  loading.value = true
  try {
    const [portfolio, history] = await Promise.all([
      fetchPortfolio(),
      fetchPortfolioHistory(15),
    ])
    products.value = portfolio.products
    const map: Record<string, ProductHistory> = {}
    for (const s of history.series) {
      map[s.product_code] = s
    }
    historyMap.value = map
  } finally {
    loading.value = false
  }
}

function miniChartOption(code: string) {
  const h = historyMap.value[code]
  if (!h || h.history.length === 0) return null
  const dates = h.history.map(p => p.as_of_date)
  const values = h.history.map(p => p.annualized_7d ?? p.daily_growth_rate ?? 0)
  return {
    grid: { top: 4, right: 4, bottom: 4, left: 4 },
    xAxis: { type: 'category', show: false, data: dates },
    yAxis: { type: 'value', show: false, min: 'dataMin', max: 'dataMax' },
    tooltip: { trigger: 'axis', formatter: (p: any) => `${p[0].axisValue}<br/>` + (p[0].value != null ? `${p[0].value}%` : '-') },
    series: [{ type: 'line', data: values, smooth: true, showSymbol: false, lineStyle: { width: 2 }, areaStyle: { opacity: 0.1 } }],
  }
}

function formatNavChange(val: number | null) {
  if (val == null) return '-'
  const s = val.toFixed(4)
  return val > 0 ? `+${s}` : s
}

function getNavChangeClass(val: number | null) {
  if (val == null || val === 0) return 'text-gray-500'
  return val > 0 ? 'text-red-500' : 'text-green-500'
}

function handleCompareAll() {
  emit('compare', products.value.map(p => p.product_code))
}

onMounted(loadData)
</script>

<template>
  <div class="mb-6">
    <div class="flex items-center justify-between mb-3">
      <h2 class="text-lg font-semibold text-gray-800">我的持仓概览</h2>
      <button
        v-if="products.length > 1"
        @click="handleCompareAll"
        class="text-sm text-blue-600 hover:text-blue-800 font-medium"
      >
        对比全部 →
      </button>
    </div>

    <div v-if="loading" class="text-gray-400 text-sm py-8 text-center">加载中...</div>

    <div v-else-if="products.length === 0" class="text-gray-400 text-sm py-8 text-center">
      暂无持仓配置，请编辑 portfolio.json
    </div>

    <div v-else class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
      <div
        v-for="p in products"
        :key="p.product_code"
        class="bg-white rounded-xl shadow-sm border border-gray-100 p-4 hover:shadow-md transition-shadow"
      >
        <div class="flex items-start justify-between mb-1">
          <div class="text-sm font-medium text-gray-800 truncate max-w-[180px]" :title="p.product_name">
            {{ p.product_name || p.product_code }}
          </div>
          <span class="text-xs text-gray-400 shrink-0 ml-2">{{ p.as_of_date }}</span>
        </div>
        <div class="text-xs text-gray-400 mb-3">{{ p.product_code }}</div>

        <div class="flex items-end justify-between mb-3">
          <div>
            <div class="text-xs text-gray-500 mb-0.5">七日年化</div>
            <div class="text-2xl font-bold" :class="(p.annualized_7d ?? 0) >= 1.2 ? 'text-red-500' : 'text-blue-600'">
              {{ p.annualized_7d != null ? p.annualized_7d.toFixed(4) + '%' : '-' }}
            </div>
          </div>
          <div class="text-right flex flex-col items-end">
            <div class="mb-0.5">
              <span class="text-xs text-gray-400 mr-1">万份</span>
              <span class="text-base font-semibold text-gray-700">
                {{ p.income_per_10k != null ? p.income_per_10k.toFixed(4) : '-' }}
              </span>
            </div>
            <div>
              <span class="text-xs text-gray-400 mr-1">增量</span>
              <span class="text-base font-semibold" :class="getNavChangeClass(p.day_nav_change)">
                {{ formatNavChange(p.day_nav_change) }}
              </span>
            </div>
          </div>
        </div>

        <div v-if="miniChartOption(p.product_code)" class="h-16 -mx-1">
          <v-chart :option="miniChartOption(p.product_code)!" autoresize class="w-full h-full" />
        </div>
      </div>
    </div>
  </div>
</template>
