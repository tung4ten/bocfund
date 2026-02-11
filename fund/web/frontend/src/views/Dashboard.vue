<script setup lang="ts">
import { useRouter } from 'vue-router'
import PortfolioCards from '../components/PortfolioCards.vue'
import TopRanking from '../components/TopRanking.vue'

const router = useRouter()

function goCompare(codes: string[]) {
  router.push({ path: '/compare', query: { codes: codes.join(',') } })
}
</script>

<template>
  <div>
    <PortfolioCards @compare="goCompare" />
    <TopRanking @compare="goCompare" />
  </div>
</template>
