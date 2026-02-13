<script setup lang="ts">
import { useRoute } from 'vue-router'
import { computed } from 'vue'

const route = useRoute()
const currentPath = computed(() => route.path)
</script>

<template>
  <div class="min-h-screen bg-gray-50">
    <!-- Header -->
    <header class="bg-white shadow-sm border-b border-gray-200">
      <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div class="flex items-center justify-between h-14">
          <div class="flex items-center space-x-2">
            <span class="text-xl font-bold text-blue-700">BOC</span>
            <span class="text-lg font-medium text-gray-700">理财净值看板</span>
          </div>
          <nav class="flex space-x-1">
            <router-link
              to="/"
              class="px-4 py-2 rounded-lg text-sm font-medium transition-colors"
              :class="currentPath === '/' ? 'bg-blue-50 text-blue-700' : 'text-gray-600 hover:bg-gray-100'"
            >
              首页看板
            </router-link>
            <router-link
              to="/compare"
              class="px-4 py-2 rounded-lg text-sm font-medium transition-colors"
              :class="currentPath === '/compare' ? 'bg-blue-50 text-blue-700' : 'text-gray-600 hover:bg-gray-100'"
            >
              趋势对比
            </router-link>
            <router-link
              to="/positions"
              class="px-4 py-2 rounded-lg text-sm font-medium transition-colors"
              :class="currentPath === '/positions' ? 'bg-blue-50 text-blue-700' : 'text-gray-600 hover:bg-gray-100'"
            >
              我的持仓
            </router-link>
          </nav>
        </div>
      </div>
    </header>

    <!-- Main -->
    <main class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
      <router-view />
    </main>
  </div>
</template>
