<script setup lang="ts">
import { useRouter } from 'vue-router'
import { ref, onMounted } from 'vue'
import PortfolioCards from '../components/PortfolioCards.vue'
import TopRanking from '../components/TopRanking.vue'
import { fetchIncome } from '../api'
import type { IncomeResponse } from '../api'

const router = useRouter()
const incomeData = ref<IncomeResponse | null>(null)

function goCompare(codes: string[]) {
  router.push({ path: '/compare', query: { codes: codes.join(',') } })
}

onMounted(async () => {
  try {
    incomeData.value = await fetchIncome()
  } catch (e) {
    console.error(e)
  }
})
</script>

<template>
  <div>
    <!-- My Assets Summary -->
    <div v-if="incomeData && incomeData.current_asset > 0" class="mb-6 bg-white rounded-xl shadow-sm border border-gray-100 p-6">
      <div class="flex items-center justify-between">
        <div>
          <h2 class="text-lg font-semibold text-gray-800 mb-2">我的总资产</h2>
          <div class="text-3xl font-bold text-gray-900">
            {{ incomeData.current_asset.toLocaleString('zh-CN', { style: 'currency', currency: 'CNY' }) }}
          </div>
        </div>
        <div class="text-right">
          <div class="text-sm text-gray-500 mb-1">累计收益</div>
          <div class="text-xl font-bold" :class="incomeData.total_income >= 0 ? 'text-red-600' : 'text-green-600'">
            {{ incomeData.total_income > 0 ? '+' : '' }}{{ incomeData.total_income.toFixed(2) }}
          </div>
        </div>
      </div>
    </div>

    <PortfolioCards @compare="goCompare" />
    <TopRanking @compare="goCompare" />
  </div>
</template>
