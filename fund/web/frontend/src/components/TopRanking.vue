<script setup lang="ts">
import { ref, computed, onMounted, nextTick } from 'vue'
import { fetchTop50, fetchProductHistory, setRiskLevel, deleteRiskLevel } from '../api'
import type { ProductSnapshot, ProductHistory } from '../api'
import NavTrendChart from './NavTrendChart.vue'

const emit = defineEmits<{
  (e: 'compare', codes: string[]): void
}>()

const items = ref<ProductSnapshot[]>([])
const asOfDate = ref('')
const loading = ref(true)
const searchQuery = ref('')
const selectedCodes = ref<Set<string>>(new Set())
const riskFilter = ref('')   // '' = 全部, 'R1', 'R2', 'R3', 'R4'

// 风险等级编辑状态
const editingRiskCode = ref<string | null>(null)

// 展开净值趋势面板
const expandedCode = ref<string | null>(null)
const expandedHistory = ref<ProductHistory | null>(null)
const expandLoading = ref(false)

const riskOptions = [
  { value: '', label: '全部风险等级' },
  { value: 'R1', label: 'R1 低风险' },
  { value: 'R2', label: 'R2 中低风险' },
  { value: 'R3', label: 'R3 中风险' },
  { value: 'R4', label: 'R4 中高风险' },
]

const riskEditOptions = [
  { value: '', label: '清除' },
  { value: 'R1', label: 'R1 低风险' },
  { value: 'R2', label: 'R2 中低风险' },
  { value: 'R3', label: 'R3 中风险' },
  { value: 'R4', label: 'R4 中高风险' },
  { value: 'R5', label: 'R5 高风险' },
]

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

async function loadData() {
  loading.value = true
  try {
    const res = await fetchTop50(200, riskFilter.value || undefined)
    items.value = res.items
    asOfDate.value = res.as_of_date
  } finally {
    loading.value = false
  }
}

const filtered = computed(() => {
  if (!searchQuery.value) return items.value
  const q = searchQuery.value.toLowerCase()
  return items.value.filter(
    i => i.product_code.toLowerCase().includes(q) || i.product_name.toLowerCase().includes(q)
  )
})

function toggleSelect(code: string) {
  const s = new Set(selectedCodes.value)
  if (s.has(code)) s.delete(code)
  else s.add(code)
  selectedCodes.value = s
}

function handleCompare() {
  emit('compare', Array.from(selectedCodes.value))
}

function onRiskFilterChange() {
  selectedCodes.value = new Set()
  loadData()
}

// ---- 风险等级编辑 ----
function openRiskEdit(e: Event, code: string) {
  e.stopPropagation()
  editingRiskCode.value = code
}

async function onRiskSelect(e: Event, item: ProductSnapshot) {
  const val = (e.target as HTMLSelectElement).value
  editingRiskCode.value = null

  try {
    if (val === '') {
      // 清除风险等级
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
  // 延迟关闭以允许 change 事件先触发
  setTimeout(() => { editingRiskCode.value = null }, 150)
}

// ---- 展开净值趋势面板 ----
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
    // 确保还没切到别的行
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
  // 如果点击的是 checkbox、select、button 等交互区域，不展开
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

<template>
  <div>
    <div class="flex items-center justify-between mb-3 flex-wrap gap-2">
      <h2 class="text-lg font-semibold text-gray-800">
        七日年化收益率排行
        <span v-if="asOfDate" class="text-sm font-normal text-gray-400 ml-2">{{ asOfDate }}</span>
      </h2>
      <div class="flex items-center gap-3 flex-wrap">
        <button
          v-if="selectedCodes.size >= 2"
          @click="handleCompare"
          class="px-3 py-1.5 bg-blue-600 text-white text-sm rounded-lg hover:bg-blue-700 transition-colors"
        >
          对比所选 ({{ selectedCodes.size }})
        </button>
        <select
          v-model="riskFilter"
          @change="onRiskFilterChange"
          class="px-3 py-1.5 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent bg-white"
        >
          <option v-for="opt in riskOptions" :key="opt.value" :value="opt.value">
            {{ opt.label }}
          </option>
        </select>
        <input
          v-model="searchQuery"
          type="text"
          placeholder="搜索产品..."
          class="px-3 py-1.5 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent w-48"
        />
      </div>
    </div>

    <div v-if="loading" class="text-gray-400 text-sm py-8 text-center">加载中...</div>

    <div v-else class="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
      <table class="w-full text-sm">
        <thead>
          <tr class="bg-gray-50 text-gray-500 text-xs uppercase">
            <th class="py-3 px-4 text-left w-10"></th>
            <th class="py-3 px-4 text-left w-12">排名</th>
            <th class="py-3 px-4 text-left">产品代码</th>
            <th class="py-3 px-4 text-left">产品名称</th>
            <th class="py-3 px-4 text-center">风险</th>
            <th class="py-3 px-4 text-right">七日年化</th>
            <th class="py-3 px-4 text-right">万份收益 / 累计净值</th>
            <th class="py-3 px-4 text-center">来源</th>
            <th class="py-3 px-4 text-right">截止日期</th>
          </tr>
        </thead>
        <tbody>
          <template v-for="(item, idx) in filtered" :key="item.product_code">
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
                :class="idx < 3 ? 'bg-red-100 text-red-600' : 'bg-gray-100 text-gray-500'"
              >
                {{ idx + 1 }}
              </span>
            </td>
            <td class="py-2.5 px-4 font-mono text-gray-600">{{ item.product_code }}</td>
            <td class="py-2.5 px-4 text-gray-800 truncate max-w-[240px]" :title="item.product_name">
              {{ item.product_name }}
            </td>
            <td class="py-2.5 px-4 text-center" @click.stop>
              <!-- 编辑模式 -->
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
              <!-- 展示模式 - 可点击编辑 -->
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
            <td class="py-2.5 px-4 text-center">
              <span
                v-if="item.annualized_7d_source === 'direct'"
                class="inline-flex items-center px-1.5 py-0.5 rounded text-xs font-medium bg-green-100 text-green-700"
                title="数据由官网直接提供"
              >直接</span>
              <span
                v-else-if="item.annualized_7d_source === 'calculated'"
                class="inline-flex items-center px-1.5 py-0.5 rounded text-xs font-medium bg-amber-100 text-amber-700"
                title="根据近7天累计净值变化计算得出"
              >计算</span>
              <span v-else class="text-gray-300">-</span>
            </td>
            <td class="py-2.5 px-4 text-right text-gray-400">{{ item.as_of_date }}</td>
          </tr>
          <!-- 展开的净值趋势面板 -->
          <tr v-if="expandedCode === item.product_code">
            <td :colspan="9" class="p-0">
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
  </div>
</template>
