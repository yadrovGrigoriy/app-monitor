<script setup>
import { computed } from 'vue'
import { formatDuration, percentOfTotal } from '../utils'

const props = defineProps({
  stats: Object,
  todayActivity: Array,
  limitsCount: Number,
  appsCount: Number,
  loading: Boolean,
})

const emit = defineEmits(['refresh'])

const today = computed(() => {
  const d = new Date()
  return d.toLocaleDateString('ru-RU', { day: 'numeric', month: 'long', year: 'numeric' })
})

const columns = [
  { title: '#', key: 'index', width: 40 },
  { title: 'Приложение', key: 'app' },
  { title: 'Время', key: 'duration' },
  { title: 'Доля', key: 'bar' },
]
</script>

<template>
  <div>
    <div class="page-header">
      <h2>Дашборд</h2>
      <div class="header-actions">
        <span class="date-range">{{ today }}</span>
        <a-button type="text" @click="emit('refresh')" :loading="loading">🔄</a-button>
      </div>
    </div>

    <a-row :gutter="[12, 12]" style="margin-bottom:20px">
      <a-col :xs="12" :sm="6">
        <a-card size="small" class="stat-card">
          <a-statistic :value="stats.monitored_apps" title="Приложений сегодня" />
        </a-card>
      </a-col>
      <a-col :xs="12" :sm="6">
        <a-card size="small" class="stat-card">
          <a-statistic :value="formatDuration(stats.total_today)" title="Всего времени сегодня" />
        </a-card>
      </a-col>
      <a-col :xs="12" :sm="6">
        <a-card size="small" class="stat-card">
          <a-statistic :value="limitsCount" title="Активных лимитов" />
        </a-card>
      </a-col>
      <a-col :xs="12" :sm="6">
        <a-card size="small" class="stat-card">
          <a-statistic :value="appsCount" title="Всего приложений" />
        </a-card>
      </a-col>
    </a-row>

    <a-card title="Активность сегодня" :bordered="false">
      <a-table :dataSource="todayActivity" :columns="columns" :pagination="false"
        :loading="loading" rowKey="system_id" size="small">
        <template #bodyCell="{ column, record, index }">
          <template v-if="column.key === 'index'">{{ index + 1 }}</template>
          <template v-if="column.key === 'app'">
            <div class="app-name">{{ record.app_name }}</div>
            <div class="app-sid">{{ record.system_id }}</div>
          </template>
          <template v-if="column.key === 'duration'">
            <strong>{{ formatDuration(record.duration_seconds) }}</strong>
          </template>
          <template v-if="column.key === 'bar'">
            <a-progress :percent="percentOfTotal(record.duration_seconds, stats.total_today)"
              :showInfo="false" :strokeColor="{ from: '#6366f1', to: '#22c55e' }" />
          </template>
        </template>
        <template #emptyText>
          <a-empty description="Сегодня активности пока нет" />
        </template>
      </a-table>
    </a-card>
  </div>
</template>
