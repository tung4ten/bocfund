<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { fetchTransactions, addTransaction, deleteTransaction, fetchIncome } from '../api'
import type { TransactionItem, IncomeResponse } from '../api'
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { BarChart, LineChart } from 'echarts/charts'
import { GridComponent, TooltipComponent, LegendComponent, DataZoomComponent } from 'echarts/components'

use([CanvasRenderer, BarChart, LineChart, GridComponent, TooltipComponent, LegendComponent, DataZoomComponent])

const transactions = ref<TransactionItem[]>([])
const incomeData = ref<IncomeResponse | null>(null)
const loading = ref(false)

// Form
const formVisible = ref(false)
const form = ref({
  product_code: '',
  date: new Date().toISOString().split('T')[0],
  shares: 0,
  amount: 0
})

async function refresh() {
  loading.value = true
  try {
    const [txs, inc] = await Promise.all([fetchTransactions(), fetchIncome()])
    transactions.value = txs
    incomeData.value = inc
  } catch (e) {
    console.error(e)
  } finally {
    loading.value = false
  }
}

async function submitTx() {
  if (!form.value.product_code || !form.value.date) return
  try {
    await addTransaction({
      product_code: form.value.product_code,
      date: form.value.date,
      shares: Number(form.value.shares),
      amount: form.value.amount ? Number(form.value.amount) : 0
    })
    formVisible.value = false
    // Reset form partially
    form.value.shares = 0
    form.value.amount = 0
    refresh()
  } catch (e) {
    alert('添加失败')
  }
}

async function removeTx(id: number) {
  if (!confirm('确定删除?')) return
  try {
    await deleteTransaction(id)
    refresh()
  } catch (e) {
    alert('删除失败')
  }
}

const chartOption = computed(() => {
  if (!incomeData.value || !incomeData.value.series.length) return null
  
  const dates = incomeData.value.series.map(p => p.date)
  const incomes = incomeData.value.series.map(p => parseFloat(p.income.toFixed(2)))
  const assets = incomeData.value.series.map(p => parseFloat(p.total_asset.toFixed(2)))
  
  return {
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'cross' },
      formatter: (params: any) => {
        let res = params[0].name + '<br/>'
        params.forEach((p: any) => {
          res += p.marker + p.seriesName + ': ' + p.value.toLocaleString() + '<br/>'
        })
        return res
      }
    },
    legend: {
      data: ['日收益', '总资产']
    },
    grid: { left: 50, right: 50, bottom: 40, top: 40 },
    xAxis: {
      type: 'category',
      data: dates,
      axisPointer: { type: 'shadow' }
    },
    yAxis: [
      {
        type: 'value',
        name: '日收益',
        axisLabel: { formatter: '{value}' }
      },
      {
        type: 'value',
        name: '总资产',
        axisLabel: { formatter: '{value}' },
        splitLine: { show: false }
      }
    ],
    series: [
      {
        name: '日收益',
        type: 'bar',
        data: incomes,
        itemStyle: { color: '#3b82f6' }
      },
      {
        name: '总资产',
        type: 'line',
        yAxisIndex: 1,
        data: assets,
        itemStyle: { color: '#10b981' },
        showSymbol: false
      }
    ],
    dataZoom: [
      { type: 'inside' },
      { type: 'slider', bottom: 0 }
    ]
  }
})

onMounted(refresh)
</script>

<template>
  <div class="space-y-6">
    <!-- Header -->
    <div class="flex justify-between items-center">
      <h1 class="text-2xl font-bold text-gray-800">我的持仓</h1>
      <button 
        @click="formVisible = !formVisible"
        class="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition"
      >
        {{ formVisible ? '取消' : '添加交易' }}
      </button>
    </div>

    <!-- Add Form -->
    <div v-if="formVisible" class="bg-white p-4 rounded-xl shadow border border-gray-100">
      <h3 class="font-semibold mb-3">记一笔</h3>
      <div class="grid grid-cols-1 md:grid-cols-5 gap-4">
        <input v-model="form.product_code" placeholder="产品代码" class="border p-2 rounded" />
        <input v-model="form.date" type="date" class="border p-2 rounded" />
        <input v-model="form.shares" type="number" step="0.01" placeholder="持有份额 (+买/-卖)" class="border p-2 rounded" />
        <input v-model="form.amount" type="number" step="0.01" placeholder="交易金额 (选填)" class="border p-2 rounded" />
        <button @click="submitTx" class="bg-green-600 text-white px-4 py-2 rounded hover:bg-green-700">提交</button>
      </div>
    </div>

    <!-- Summary Cards -->
    <div v-if="incomeData" class="grid grid-cols-1 md:grid-cols-2 gap-4">
      <div class="bg-white p-6 rounded-xl shadow-sm border border-gray-100">
        <div class="text-gray-500 text-sm">当前估算总资产</div>
        <div class="text-3xl font-bold text-gray-900 mt-1">
          {{ incomeData.current_asset.toLocaleString('zh-CN', { style: 'currency', currency: 'CNY' }) }}
        </div>
      </div>
      <div class="bg-white p-6 rounded-xl shadow-sm border border-gray-100">
        <div class="text-gray-500 text-sm">累计计算收益</div>
        <div class="text-3xl font-bold mt-1" :class="incomeData.total_income >= 0 ? 'text-red-600' : 'text-green-600'">
          {{ incomeData.total_income > 0 ? '+' : '' }}{{ incomeData.total_income.toFixed(2) }}
        </div>
      </div>
    </div>

    <!-- Chart -->
    <div class="bg-white p-4 rounded-xl shadow-sm border border-gray-100 h-96">
      <h3 class="text-lg font-semibold mb-2">收益与资产走势</h3>
      <v-chart v-if="chartOption" :option="chartOption" autoresize class="w-full h-full" />
      <div v-else class="flex h-full items-center justify-center text-gray-400">
        暂无数据，请先添加持仓交易
      </div>
    </div>

    <!-- Holdings Detail Table -->
    <div v-if="incomeData && incomeData.holdings && incomeData.holdings.length > 0" class="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
      <div class="px-6 py-4 border-b border-gray-100 font-semibold text-gray-800">当前持仓明细</div>
      <div class="overflow-x-auto">
        <table class="w-full text-sm text-left">
          <thead class="bg-gray-50 text-gray-500 font-medium">
            <tr>
              <th class="px-6 py-3">产品名称</th>
              <th class="px-6 py-3">产品代码</th>
              <th class="px-6 py-3 text-right">持有份额</th>
              <th class="px-6 py-3 text-right">估算金额(CNY)</th>
              <th class="px-6 py-3 text-right">今日收益(CNY)</th>
              <th class="px-6 py-3 text-right">数据日期</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="h in incomeData.holdings" :key="h.product_code" class="border-t border-gray-50 hover:bg-gray-50">
              <td class="px-6 py-3 font-medium text-gray-900">{{ h.product_name }}</td>
              <td class="px-6 py-3 text-gray-500 font-mono">{{ h.product_code }}</td>
              <td class="px-6 py-3 text-right font-mono">{{ h.shares.toLocaleString() }}</td>
              <td class="px-6 py-3 text-right font-bold text-gray-800">
                {{ h.amount.toLocaleString('zh-CN', { style: 'currency', currency: 'CNY' }) }}
              </td>
              <td class="px-6 py-3 text-right font-bold" :class="h.today_income >= 0 ? 'text-red-600' : 'text-green-600'">
                {{ h.today_income > 0 ? '+' : '' }}{{ h.today_income.toFixed(2) }}
              </td>
              <td class="px-6 py-3 text-right text-gray-400 text-xs">{{ h.as_of_date }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- Transaction List -->
    <div class="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
      <div class="px-6 py-4 border-b border-gray-100 font-semibold">交易记录</div>
      <table class="w-full text-sm text-left">
        <thead class="bg-gray-50 text-gray-500">
          <tr>
            <th class="px-6 py-3">日期</th>
            <th class="px-6 py-3">代码</th>
            <th class="px-6 py-3 text-right">份额</th>
            <th class="px-6 py-3 text-right">金额</th>
            <th class="px-6 py-3 text-center">操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="tx in transactions" :key="tx.id" class="border-t border-gray-50 hover:bg-gray-50">
            <td class="px-6 py-3">{{ tx.date }}</td>
            <td class="px-6 py-3 font-mono">{{ tx.product_code }}</td>
            <td class="px-6 py-3 text-right font-medium" :class="tx.shares >= 0 ? 'text-red-600' : 'text-green-600'">
              {{ tx.shares > 0 ? '+' : '' }}{{ tx.shares }}
            </td>
            <td class="px-6 py-3 text-right text-gray-600">{{ tx.amount }}</td>
            <td class="px-6 py-3 text-center">
              <button @click="removeTx(tx.id)" class="text-red-500 hover:text-red-700">删除</button>
            </td>
          </tr>
          <tr v-if="transactions.length === 0">
            <td colspan="5" class="px-6 py-8 text-center text-gray-400">暂无记录</td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>
