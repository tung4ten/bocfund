<script setup lang="ts">
import { ref, watch, onMounted, computed } from 'vue'
import { useRoute } from 'vue-router'
import TrendChart from '../components/TrendChart.vue'
import NavTrendChart from '../components/NavTrendChart.vue'
import { fetchCompare, fetchPortfolio } from '../api'
import type { ProductHistory, ProductSnapshot } from '../api'

const route = useRoute()

const codeInput = ref('')
const selectedCodes = ref<string[]>([])
const days = ref(30)
const series = ref<ProductHistory[]>([])
const loading = ref(false)
const portfolioProducts = ref<ProductSnapshot[]>([])

/** 图表类型切换 */
const chartType = ref<'annualized' | 'nav'>('nav')

const dayOptions = [
  { label: '7天', value: 7 },
  { label: '30天', value: 30 },
  { label: '90天', value: 90 },
  { label: '180天', value: 180 },
]

async function loadPortfolio() {
  try {
    const res = await fetchPortfolio()
    portfolioProducts.value = res.products
  } catch { /* ignore */ }
}

async function loadCompare() {
  if (selectedCodes.value.length === 0) {
    series.value = []
    return
  }
  loading.value = true
  try {
    const res = await fetchCompare(selectedCodes.value, days.value)
    series.value = res.series
  } finally {
    loading.value = false
  }
}

function addCode() {
  const code = codeInput.value.trim().toUpperCase()
  if (code && !selectedCodes.value.includes(code)) {
    selectedCodes.value = [...selectedCodes.value, code]
  }
  codeInput.value = ''
}

function removeCode(code: string) {
  selectedCodes.value = selectedCodes.value.filter(c => c !== code)
}

function togglePortfolioProduct(code: string) {
  if (selectedCodes.value.includes(code)) {
    removeCode(code)
  } else {
    selectedCodes.value = [...selectedCodes.value, code]
  }
}

// Latest value table
const latestTable = computed(() => {
  return series.value.map(s => {
    const last = s.history.length > 0 ? s.history[s.history.length - 1] : null
    return {
      product_code: s.product_code,
      product_name: s.product_name,
      annualized_7d: last?.annualized_7d,
      income_per_10k: last?.income_per_10k,
      cumulative_nav: last?.cumulative_nav,
      as_of_date: last?.as_of_date,
    }
  })
})

// Watch for changes
watch([selectedCodes, days], loadCompare)

// Init from query params
onMounted(async () => {
  await loadPortfolio()
  const q = route.query.codes
  if (q && typeof q === 'string') {
    selectedCodes.value = q.split(',').filter(Boolean)
  }
})
</script>

<template>
  <div>
    <h2 class="text-lg font-semibold text-gray-800 mb-4">趋势对比</h2>

    <!-- Controls -->
    <div class="bg-white rounded-xl shadow-sm border border-gray-100 p-4 mb-4">
      <div class="flex flex-wrap items-start gap-4">
        <!-- Add from portfolio -->
        <div v-if="portfolioProducts.length > 0" class="flex-1 min-w-[200px]">
          <div class="text-xs text-gray-500 mb-2">从持仓中选择</div>
          <div class="flex flex-wrap gap-2">
            <button
              v-for="p in portfolioProducts"
              :key="p.product_code"
              @click="togglePortfolioProduct(p.product_code)"
              class="px-2.5 py-1 rounded-full text-xs font-medium border transition-colors"
              :class="selectedCodes.includes(p.product_code)
                ? 'bg-blue-600 text-white border-blue-600'
                : 'bg-white text-gray-600 border-gray-200 hover:border-blue-300'"
            >
              {{ p.product_name || p.product_code }}
            </button>
          </div>
        </div>

        <!-- Manual add -->
        <div class="min-w-[200px]">
          <div class="text-xs text-gray-500 mb-2">手动添加产品代码</div>
          <div class="flex gap-2">
            <input
              v-model="codeInput"
              @keyup.enter="addCode"
              type="text"
              placeholder="输入产品代码"
              class="px-3 py-1.5 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 w-40"
            />
            <button
              @click="addCode"
              class="px-3 py-1.5 bg-blue-600 text-white text-sm rounded-lg hover:bg-blue-700"
            >
              添加
            </button>
          </div>
        </div>

        <!-- Time range -->
        <div>
          <div class="text-xs text-gray-500 mb-2">时间范围</div>
          <div class="flex gap-1">
            <button
              v-for="opt in dayOptions"
              :key="opt.value"
              @click="days = opt.value"
              class="px-3 py-1.5 rounded-lg text-sm font-medium transition-colors"
              :class="days === opt.value ? 'bg-blue-600 text-white' : 'bg-gray-100 text-gray-600 hover:bg-gray-200'"
            >
              {{ opt.label }}
            </button>
          </div>
        </div>
      </div>

      <!-- Selected tags -->
      <div v-if="selectedCodes.length > 0" class="mt-3 flex flex-wrap gap-2">
        <span
          v-for="code in selectedCodes"
          :key="code"
          class="inline-flex items-center gap-1 px-2.5 py-1 bg-blue-50 text-blue-700 rounded-full text-xs font-medium"
        >
          {{ code }}
          <button @click="removeCode(code)" class="hover:text-red-500 text-base leading-none">&times;</button>
        </span>
      </div>
    </div>

    <!-- Loading -->
    <div v-if="loading" class="text-gray-400 text-sm py-12 text-center">加载中...</div>

    <!-- Chart -->
    <div v-else-if="series.length > 0">
      <!-- 图表类型切换 -->
      <div class="flex items-center gap-2 mb-3">
        <span class="text-xs text-gray-500">图表类型：</span>
        <div class="inline-flex rounded-lg border border-gray-200 overflow-hidden">
          <button
            @click="chartType = 'nav'"
            class="px-3 py-1.5 text-sm font-medium transition-colors"
            :class="chartType === 'nav' ? 'bg-blue-600 text-white' : 'bg-white text-gray-600 hover:bg-gray-50'"
          >
            归一化净值
          </button>
          <button
            @click="chartType = 'annualized'"
            class="px-3 py-1.5 text-sm font-medium transition-colors"
            :class="chartType === 'annualized' ? 'bg-blue-600 text-white' : 'bg-white text-gray-600 hover:bg-gray-50'"
          >
            七日年化
          </button>
        </div>
      </div>

      <div class="bg-white rounded-xl shadow-sm border border-gray-100 p-4">
        <h3 class="text-base font-semibold text-gray-800 mb-3">
          {{ chartType === 'nav' ? '归一化净值走势（基准=100）' : '七日年化收益率走势' }}
        </h3>
        <NavTrendChart v-if="chartType === 'nav'" :series="series" />
        <TrendChart v-else :series="series" />
      </div>

      <!-- Data table -->
      <div class="mt-4 bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
        <table class="w-full text-sm">
          <thead>
            <tr class="bg-gray-50 text-gray-500 text-xs uppercase">
              <th class="py-3 px-4 text-left">产品代码</th>
              <th class="py-3 px-4 text-left">产品名称</th>
              <th class="py-3 px-4 text-right">七日年化</th>
              <th class="py-3 px-4 text-right">万份收益</th>
              <th class="py-3 px-4 text-right">累计净值</th>
              <th class="py-3 px-4 text-right">截止日期</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="item in latestTable" :key="item.product_code" class="border-t border-gray-50">
              <td class="py-2.5 px-4 font-mono text-gray-600">{{ item.product_code }}</td>
              <td class="py-2.5 px-4 text-gray-800">{{ item.product_name }}</td>
              <td class="py-2.5 px-4 text-right font-semibold" :class="(item.annualized_7d ?? 0) >= 1.2 ? 'text-red-500' : 'text-blue-600'">
                {{ item.annualized_7d != null ? item.annualized_7d.toFixed(4) + '%' : '-' }}
              </td>
              <td class="py-2.5 px-4 text-right text-gray-600">
                {{ item.income_per_10k != null ? item.income_per_10k.toFixed(5) : '-' }}
              </td>
              <td class="py-2.5 px-4 text-right text-gray-600">
                {{ item.cumulative_nav != null ? item.cumulative_nav.toFixed(6) : '-' }}
              </td>
              <td class="py-2.5 px-4 text-right text-gray-400">{{ item.as_of_date ?? '-' }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <div v-else-if="selectedCodes.length === 0" class="text-gray-400 text-sm py-12 text-center">
      请选择至少一个产品进行对比
    </div>
  </div>
</template>
