<script setup>
import { ref } from 'vue'
import { api } from '../api'
import { formatDuration, percentOfTotal } from '../utils'
import dayjs from 'dayjs'

const props = defineProps({
  stats: Object,
  loading: Boolean,
})

const emit = defineEmits(['load'])
const startDate = ref(dayjs())
const endDate = ref(dayjs())

const columns = [
  { title: '#', key: 'index', width: 40 },
  { title: 'Приложение', key: 'app' },
  { title: 'Время', key: 'duration' },
  { title: 'Доля', key: 'bar' },
]

function loadStats() {
  emit('load', {
    start: startDate.value.format('YYYY-MM-DD'),
    end: endDate.value.format('YYYY-MM-DD'),
  })
}
</script>

<template>
  <div>
    <div class="page-header">
      <h2>Статистика за период</h2>
      <div class="header-actions">
        <a-date-picker v-model:value="startDate" />
        <span class="text-muted">—</span>
        <a-date-picker v-model:value="endDate" />
        <a-button type="primary" @click="loadStats" :loading="loading">Показать</a-button>
      </div>
    </div>

    <a-row :gutter="[12, 12]" style="margin-bottom:20px">
      <a-col :xs="12" :sm="12">
        <a-card size="small" class="stat-card">
          <a-statistic :value="formatDuration(stats.total_seconds)" title="Всего за период" />
        </a-card>
      </a-col>
      <a-col :xs="12" :sm="12">
        <a-card size="small" class="stat-card">
          <a-statistic :value="stats.apps.length" title="Приложений" />
        </a-card>
      </a-col>
    </a-row>

    <a-card title="Детализация по приложениям" :bordered="false">
      <a-table :dataSource="stats.apps" :columns="columns" :pagination="false"
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
            <a-progress :percent="percentOfTotal(record.duration_seconds, stats.total_seconds)"
              :showInfo="false" :strokeColor="{ from: '#6366f1', to: '#22c55e' }" />
          </template>
        </template>
        <template #emptyText>
          <a-empty description="Выберите период и нажмите «Показать»" />
        </template>
      </a-table>
    </a-card>
  </div>
</template>
