
<template>
  <div>
    <div class="flex items-center justify-between mb-3 flex-wrap gap-2">
      <div>
        <h2 class="text-lg font-semibold text-gray-800">
          高级排名
          <span v-if="asOfDate" class="text-sm font-normal text-gray-400 ml-2">{{ asOfDate }}</span>
        </h2>
        <p class="text-gray-500 text-sm">根据不同时间周期的年化收益率对产品进行排名。</p>
      </div>
      <div class="flex items-center gap-3 flex-wrap">
        <div class="flex items-center gap-2">
          <label for="time-period" class="text-xs text-gray-500">时间周期</label>
          <input
            type="number"
            id="time-period"
            v-model.number="timePeriodDays"
            class="w-24 rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 text-sm"
            min="7"
            max="1825"
          />
          <button
            @click="loadData"
            :disabled="loading"
            class="px-3 py-1.5 bg-indigo-600 text-white text-sm rounded-lg hover:bg-indigo-500 disabled:opacity-50"
          >
            {{ loading ? '加载中...' : '查询' }}
          </button>
        </div>
        <div class="flex items-center gap-1">
          <button
            v-for="opt in timePeriodOptions"
            :key="opt.value"
            @click="applyTimePeriod(opt.days)"
            class="px-2 py-1 rounded-full text-xs font-medium border transition-colors"
            :class="timePeriodDays === opt.days ? 'bg-indigo-600 text-white border-indigo-600' : 'bg-white text-gray-600 border-gray-200 hover:border-indigo-300'"
          >
            {{ opt.label }}
          </button>
        </div>
        <button
          v-if="selectedCodes.size >= 2"
          @click="handleCompare"
          class="px-3 py-1.5 bg-blue-600 text-white text-sm rounded-lg hover:bg-blue-700 transition-colors"
        >
          对比所选 ({{ selectedCodes.size }})
        </button>
        <div class="flex items-center gap-2 flex-wrap">
          <button
            @click="clearRiskFilters"
            class="px-2.5 py-1 rounded-full text-xs font-medium border transition-colors"
            :class="riskFilters.length === 0 ? 'bg-blue-600 text-white border-blue-600' : 'bg-white text-gray-600 border-gray-200 hover:border-blue-300'"
          >
            全部风险等级
          </button>
          <button
            v-for="opt in riskOptions"
            :key="opt.value"
            @click="toggleRiskFilter(opt.value)"
            class="px-2.5 py-1 rounded-full text-xs font-medium border transition-colors"
            :class="isRiskSelected(opt.value) ? 'bg-blue-600 text-white border-blue-600' : 'bg-white text-gray-600 border-gray-200 hover:border-blue-300'"
          >
            {{ opt.label }}
          </button>
        </div>
        <div class="flex items-center gap-2 flex-wrap">
          <button
            @click="clearLockupFilters"
            class="px-2.5 py-1 rounded-full text-xs font-medium border transition-colors"
            :class="lockupFilters.length === 0 ? 'bg-indigo-600 text-white border-indigo-600' : 'bg-white text-gray-600 border-gray-200 hover:border-indigo-300'"
          >
            全部期限
          </button>
          <button
            v-for="opt in lockupOptions"
            :key="opt.value"
            @click="toggleLockupFilter(opt.value)"
            class="px-2.5 py-1 rounded-full text-xs font-medium border transition-colors"
            :class="isLockupSelected(opt.value) ? 'bg-indigo-600 text-white border-indigo-600' : 'bg-white text-gray-600 border-gray-200 hover:border-indigo-300'"
          >
            {{ opt.label }}
          </button>
        </div>
        <input
          v-model="searchQuery"
          type="text"
          placeholder="搜索产品..."
          class="px-3 py-1.5 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent w-48"
        />
      </div>
    </div>

    <div v-if="loading" class="text-gray-400 text-sm py-8 text-center">加载中...</div>
    <div v-else-if="error" class="text-center text-red-500">
      <p>{{ error }}</p>
    </div>
    <div v-else-if="products.length === 0" class="text-center text-gray-500">
      <p>没有找到符合条件的产品。</p>
    </div>
    <div v-else class="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
      <table class="w-full text-sm">
        <thead>
          <tr class="bg-gray-50 text-gray-500 text-xs uppercase">
            <th class="py-3 px-4 text-left w-10"></th>
            <th class="py-3 px-4 text-left w-12">排名</th>
            <th class="py-3 px-4 text-left">产品代码</th>
            <th class="py-3 px-4 text-left">产品名称</th>
            <th class="py-3 px-4 text-center">风险</th>
            <th class="py-3 px-4 text-center">区间天数</th>
            <th class="py-3 px-4 text-center">封闭期限</th>
            <th class="py-3 px-4 text-right">区间年化</th>
            <th class="py-3 px-4 text-right">万份收益 / 累计净值</th>
            <th class="py-3 px-4 text-right">日增长率</th>
            <th class="py-3 px-4 text-center">来源</th>
            <th class="py-3 px-4 text-right">截止日期</th>
          </tr>
        </thead>
        <tbody>
          <template v-for="(item, idx) in paginatedItems" :key="item.product_code">
            <tr
              class="border-t border-gray-50 hover:bg-blue-50/30 transition-colors cursor-pointer"
              :class="[
                selectedCodes.has(item.product_code) ? 'bg-blue-50/50' : '',
                expandedCode === item.product_code ? 'bg-blue-50/60' : '',
              ]"
              @click="onRowClick($event, item.product_code)"
            >
              <td class="py-2.5 px-4" @click.stop>
                <input
                  type="checkbox"
                  :checked="selectedCodes.has(item.product_code)"
                  @click.stop="toggleSelect(item.product_code)"
                  class="rounded text-blue-600"
                />
              </td>
              <td class="py-2.5 px-4">
                <span
                  class="inline-flex items-center justify-center w-6 h-6 rounded-full text-xs font-bold"
                  :class="(currentPage - 1) * pageSize + idx < 3 ? 'bg-red-100 text-red-600' : 'bg-gray-100 text-gray-500'"
                >
                  {{ (currentPage - 1) * pageSize + idx + 1 }}
                </span>
              </td>
              <td class="py-2.5 px-4 font-mono text-gray-600">{{ item.product_code }}</td>
              <td class="py-2.5 px-4 text-gray-800 truncate max-w-[240px]" :title="item.product_name">
                {{ item.product_name }}
              </td>
              <td class="py-2.5 px-4 text-center" @click.stop>
                <select
                  v-if="editingRiskCode === item.product_code"
                  :value="item.risk_level || ''"
                  @change="onRiskSelect($event, item)"
                  @blur="onRiskBlur"
                  class="px-1 py-0.5 border border-blue-300 rounded text-xs focus:outline-none focus:ring-1 focus:ring-blue-500 bg-white"
                  autofocus
                >
                  <option v-for="opt in riskEditOptions" :key="opt.value" :value="opt.value">
                    {{ opt.label }}
                  </option>
                </select>
                <span
                  v-else-if="item.risk_level"
                  class="inline-flex items-center px-1.5 py-0.5 rounded text-xs font-medium cursor-pointer hover:ring-2 hover:ring-blue-300 transition-shadow"
                  :class="riskColorMap[item.risk_level] || 'bg-gray-100 text-gray-600'"
                  :title="(item.risk_label || '') + ' (点击修改)'"
                  @click="openRiskEdit($event, item.product_code)"
                >{{ item.risk_level }}</span>
                <button
                  v-else
                  class="text-gray-300 text-xs hover:text-blue-500 hover:bg-blue-50 px-1.5 py-0.5 rounded transition-colors"
                  title="点击设置风险等级"
                  @click="openRiskEdit($event, item.product_code)"
                >+</button>
              </td>
              <td class="py-2.5 px-4 text-center text-gray-500">
                {{ item.period_days ?? timePeriodDays }}
              </td>
              <td class="py-2.5 px-4 text-center text-gray-500">
                {{ formatLockup(item) }}
              </td>
              <td class="py-2.5 px-4 text-right font-semibold" :class="(item.annualized_7d ?? 0) >= 1.2 ? 'text-red-500' : 'text-blue-600'">
                {{ item.annualized_7d != null ? item.annualized_7d.toFixed(4) + '%' : '-' }}
              </td>
              <td class="py-2.5 px-4 text-right text-gray-600">
                <template v-if="item.annualized_7d_source === 'calculated'">
                  {{ item.cumulative_nav != null ? item.cumulative_nav.toFixed(6) : '-' }}
                </template>
                <template v-else>
                  {{ item.income_per_10k != null ? item.income_per_10k.toFixed(5) : '-' }}
                </template>
              </td>
              <td class="py-2.5 px-4 text-right text-gray-500">
                {{ formatPercent(item.daily_growth_rate, 4) }}
              </td>
              <td class="py-2.5 px-4 text-center">
                <span
                  v-if="item.annualized_7d_source === 'direct'"
                  class="inline-flex items-center px-1.5 py-0.5 rounded text-xs font-medium bg-green-100 text-green-700"
                >直接</span>
                <span
                  v-else-if="item.annualized_7d_source === 'calculated'"
                  class="inline-flex items-center px-1.5 py-0.5 rounded text-xs font-medium bg-amber-100 text-amber-700"
                >区间计算</span>
                <span v-else class="text-gray-300">-</span>
              </td>
              <td class="py-2.5 px-4 text-right text-gray-400">{{ item.as_of_date }}</td>
            </tr>
            <tr v-if="expandedCode === item.product_code">
              <td :colspan="12" class="p-0">
                <div class="bg-blue-50/40 border-l-4 border-blue-400 px-4 py-3">
                  <div class="flex items-center justify-between mb-2">
                    <h4 class="text-sm font-semibold text-gray-700">
                      {{ item.product_name }}
                      <span class="font-normal text-gray-400 ml-1">近30天净值走势</span>
                    </h4>
                    <button
                      class="text-gray-400 hover:text-gray-600 text-xs px-2 py-1 rounded hover:bg-gray-200 transition-colors"
                      @click.stop="expandedCode = null; expandedHistory = null"
                    >收起 ✕</button>
                  </div>
                  <div v-if="expandLoading" class="text-gray-400 text-sm py-6 text-center">加载趋势数据...</div>
                  <NavTrendChart
                    v-else-if="expandedHistory"
                    :series="[expandedHistory]"
                    height-class="h-56"
                  />
                  <div v-else class="text-gray-400 text-sm py-6 text-center">暂无数据</div>
                </div>
              </td>
            </tr>
          </template>
        </tbody>
      </table>
      <div v-if="filtered.length === 0" class="py-6 text-center text-gray-400 text-sm">
        无匹配结果
      </div>
    </div>

    <!-- 分页控件 -->
    <div v-if="filtered.length > pageSize" class="flex items-center justify-between mt-3 px-1">
      <span class="text-xs text-gray-400">
        共 {{ filtered.length }} 条，第 {{ currentPage }}/{{ totalPages }} 页
      </span>
      <div class="flex items-center gap-1">
        <button
          @click="currentPage = 1"
          :disabled="currentPage === 1"
          class="px-2 py-1 text-xs rounded border border-gray-200 text-gray-600 disabled:opacity-40 hover:bg-gray-50 transition-colors"
        >首页</button>
        <button
          @click="currentPage--"
          :disabled="currentPage === 1"
          class="px-2.5 py-1 text-xs rounded border border-gray-200 text-gray-600 disabled:opacity-40 hover:bg-gray-50 transition-colors"
        >‹ 上一页</button>
        <template v-for="p in pageRangeDisplayed" :key="p">
          <span v-if="p === '...'" class="px-1 text-gray-400 text-xs">…</span>
          <button
            v-else
            @click="currentPage = Number(p)"
            class="px-2.5 py-1 text-xs rounded border transition-colors"
            :class="currentPage === Number(p)
              ? 'bg-indigo-600 text-white border-indigo-600'
              : 'border-gray-200 text-gray-600 hover:bg-gray-50'"
          >{{ p }}</button>
        </template>
        <button
          @click="currentPage++"
          :disabled="currentPage === totalPages"
          class="px-2.5 py-1 text-xs rounded border border-gray-200 text-gray-600 disabled:opacity-40 hover:bg-gray-50 transition-colors"
        >下一页 ›</button>
        <button
          @click="currentPage = totalPages"
          :disabled="currentPage === totalPages"
          class="px-2 py-1 text-xs rounded border border-gray-200 text-gray-600 disabled:opacity-40 hover:bg-gray-50 transition-colors"
        >末页</button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import {
  fetchAdvancedRanking,
  fetchProductHistory,
  setRiskLevel,
  deleteRiskLevel,
  type ProductSnapshot,
  type ProductHistory,
} from '../api'
import NavTrendChart from '../components/NavTrendChart.vue'

const router = useRouter()
const timePeriodDays = ref(90)
const products = ref<ProductSnapshot[]>([])
const loading = ref(false)
const error = ref<string | null>(null)
const searchQuery = ref('')
const selectedCodes = ref<Set<string>>(new Set())
const riskFilters = ref<string[]>([])
const editingRiskCode = ref<string | null>(null)
const expandedCode = ref<string | null>(null)
const expandedHistory = ref<ProductHistory | null>(null)
const expandLoading = ref(false)

const riskOptions = [
  { value: 'R1', label: 'R1 低风险' },
  { value: 'R2', label: 'R2 中低风险' },
  { value: 'R3', label: 'R3 中风险' },
  { value: 'R4', label: 'R4 中高风险' },
  { value: 'R5', label: 'R5 高风险' },
  { value: 'UNDEFINED', label: '未定义风险等级' },
]

const riskEditOptions = [
  { value: '', label: '清除' },
  { value: 'R1', label: 'R1 低风险' },
  { value: 'R2', label: 'R2 中低风险' },
  { value: 'R3', label: 'R3 中风险' },
  { value: 'R4', label: 'R4 中高风险' },
  { value: 'R5', label: 'R5 高风险' },
]

const timePeriodOptions = [
  { value: '7d', label: '七天', days: 7 },
  { value: '14d', label: '两周', days: 14 },
  { value: '30d', label: '一个月', days: 30 },
]

const lockupOptions = [
  { value: 'open', label: '日开', days: 1 },
  { value: '7d', label: '七天', days: 7 },
  { value: '14d', label: '两周', days: 14 },
  { value: '30d', label: '一个月', days: 30 },
  { value: 'UNDEFINED', label: '未定义期限', days: -1 },
]

const lockupFilters = ref<string[]>([])
const pageSize = 100
const currentPage = ref(1)

const riskColorMap: Record<string, string> = {
  R1: 'bg-green-100 text-green-700',
  R2: 'bg-blue-100 text-blue-700',
  R3: 'bg-amber-100 text-amber-700',
  R4: 'bg-red-100 text-red-700',
  R5: 'bg-red-200 text-red-800',
}

const riskLabelMap: Record<string, string> = {
  R1: '低风险',
  R2: '中低风险',
  R3: '中风险',
  R4: '中高风险',
  R5: '高风险',
}

const asOfDate = computed(() => {
  const first = products.value[0]
  if (!first?.as_of_date) return ''
  return products.value.reduce((max, item) => (item.as_of_date > max ? item.as_of_date : max), first.as_of_date)
})

const filtered = computed(() => {
  let items = products.value
  if (riskFilters.value.length > 0) {
    const includeUndefined = riskFilters.value.includes('UNDEFINED')
    items = items.filter(item => {
      const level = item.risk_level?.trim()
      if (!level) return includeUndefined
      return riskFilters.value.includes(level)
    })
  }
  if (lockupFilters.value.length > 0) {
    items = items.filter(item => lockupFilters.value.some(value => matchesLockup(item, value)))
  }
  if (!searchQuery.value) return items
  const q = searchQuery.value.toLowerCase()
  return items.filter(
    i => i.product_code.toLowerCase().includes(q) || i.product_name.toLowerCase().includes(q)
  )
})

const totalPages = computed(() => Math.max(1, Math.ceil(filtered.value.length / pageSize)))

const paginatedItems = computed(() => {
  const start = (currentPage.value - 1) * pageSize
  return filtered.value.slice(start, start + pageSize)
})

// 筛选条件变化时重置到第一页
watch(filtered, () => { currentPage.value = 1 })

const pageRangeDisplayed = computed<(number | '...')[]>(() => {
  const total = totalPages.value
  const cur = currentPage.value
  if (total <= 7) return Array.from({ length: total }, (_, i) => i + 1)
  const pages: (number | '...')[] = [1]
  if (cur > 3) pages.push('...')
  for (let p = Math.max(2, cur - 1); p <= Math.min(total - 1, cur + 1); p++) pages.push(p)
  if (cur < total - 2) pages.push('...')
  pages.push(total)
  return pages
})

function formatPercent(value: number | null, digits = 2) {
  if (value == null || Number.isNaN(value)) return '-'
  return `${value.toFixed(digits)}%`
}

function formatLockup(item: ProductSnapshot) {
  if (item.lockup_period_text) return item.lockup_period_text
  if (item.lockup_period_days != null) return `${item.lockup_period_days}天`
  return '-'
}

function getLockupDays(item: ProductSnapshot) {
  if (item.lockup_period_days != null) return item.lockup_period_days
  if (item.product_name.includes('日开')) return 1
  return null
}

function matchesLockup(item: ProductSnapshot, value: string) {
  if (value === 'UNDEFINED') return getLockupDays(item) == null
  const days = getLockupDays(item)
  if (value === 'open') return days != null && days <= 1
  const target = lockupOptions.find(opt => opt.value === value)?.days
  if (target == null || days == null) return false
  return days === target
}

async function loadData() {
  loading.value = true
  error.value = null
  try {
    products.value = await fetchAdvancedRanking(timePeriodDays.value)
    selectedCodes.value = new Set()
  } catch (err) {
    error.value = '数据加载失败，请稍后再试。'
    console.error(err)
  } finally {
    loading.value = false
  }
}

function toggleSelect(code: string) {
  const s = new Set(selectedCodes.value)
  if (s.has(code)) s.delete(code)
  else s.add(code)
  selectedCodes.value = s
}

function handleCompare() {
  router.push({ path: '/compare', query: { codes: Array.from(selectedCodes.value).join(',') } })
}

function isRiskSelected(value: string) {
  return riskFilters.value.includes(value)
}

function onFilterChange() {
  selectedCodes.value = new Set()
}

function toggleRiskFilter(value: string) {
  if (riskFilters.value.includes(value)) {
    riskFilters.value = riskFilters.value.filter(v => v !== value)
  } else {
    riskFilters.value = [...riskFilters.value, value]
  }
  onFilterChange()
}

function clearRiskFilters() {
  if (riskFilters.value.length === 0) return
  riskFilters.value = []
  onFilterChange()
}

function isLockupSelected(value: string) {
  return lockupFilters.value.includes(value)
}

function toggleLockupFilter(value: string) {
  if (lockupFilters.value.includes(value)) {
    lockupFilters.value = lockupFilters.value.filter(v => v !== value)
  } else {
    lockupFilters.value = [...lockupFilters.value, value]
  }
  onFilterChange()
}

function clearLockupFilters() {
  if (lockupFilters.value.length === 0) return
  lockupFilters.value = []
  onFilterChange()
}

function applyTimePeriod(days: number) {
  if (timePeriodDays.value === days) return
  timePeriodDays.value = days
  loadData()
}

function openRiskEdit(e: Event, code: string) {
  e.stopPropagation()
  editingRiskCode.value = code
}

async function onRiskSelect(e: Event, item: ProductSnapshot) {
  const val = (e.target as HTMLSelectElement).value
  editingRiskCode.value = null
  try {
    if (val === '') {
      await deleteRiskLevel(item.product_code)
      item.risk_level = null
      item.risk_label = null
    } else {
      await setRiskLevel(item.product_code, val)
      item.risk_level = val
      item.risk_label = riskLabelMap[val] || ''
    }
  } catch (err) {
    console.error('设置风险等级失败', err)
  }
}

function onRiskBlur() {
  setTimeout(() => { editingRiskCode.value = null }, 150)
}

async function toggleExpand(code: string) {
  if (expandedCode.value === code) {
    expandedCode.value = null
    expandedHistory.value = null
    return
  }
  expandedCode.value = code
  expandedHistory.value = null
  expandLoading.value = true
  try {
    const hist = await fetchProductHistory(code, 30)
    if (expandedCode.value === code) {
      expandedHistory.value = hist
    }
  } catch (err) {
    console.error('获取历史数据失败', err)
  } finally {
    expandLoading.value = false
  }
}

function onRowClick(e: MouseEvent, code: string) {
  const target = e.target as HTMLElement
  if (
    target.tagName === 'INPUT' ||
    target.tagName === 'SELECT' ||
    target.tagName === 'OPTION' ||
    target.tagName === 'BUTTON' ||
    target.closest('select') ||
    target.closest('button')
  ) {
    return
  }
  toggleExpand(code)
}

onMounted(loadData)
</script>
