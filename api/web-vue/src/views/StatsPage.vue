<script setup>
import { ref, inject, onMounted, computed } from 'vue'
import { api } from '../api'
import { formatDuration, percentOfTotal } from '../utils'
import dayjs from 'dayjs'

const loading = inject('loading')
const limits = inject('limits')
const periodStats = ref({ total_seconds: 0, apps: [] })
const startDate = ref(dayjs())
const endDate = ref(dayjs())

const columns = [
  { title: '#', key: 'index', width: 40 },
  { title: 'Приложение', key: 'app' },
  { title: 'Время', key: 'duration' },
  { title: 'Доля', key: 'bar' },
]

// ─── Цвета для диаграммы ──────────────────────────────────────────
const COLORS = [
  '#6366f1', '#22c55e', '#f59e0b', '#ef4444', '#3b82f6',
  '#ec4899', '#14b8a6', '#f97316', '#8b5cf6', '#06b6d4',
  '#84cc16', '#e11d48', '#0ea5e9', '#a855f7', '#10b981',
]

// ─── Данные для круговой диаграммы ────────────────────────────────
const pieData = computed(() => {
  const apps = periodStats.value.apps || []
  const total = periodStats.value.total_seconds || 1
  let startAngle = 0
  return apps.slice(0, 10).map((app, i) => {
    const percent = (app.duration_seconds / total) * 100
    const angle = (percent / 100) * 360
    const endAngle = startAngle + angle
    const largeArc = angle > 180 ? 1 : 0
    const startRad = ((startAngle - 90) * Math.PI) / 180
    const endRad = ((endAngle - 90) * Math.PI) / 180
    const r = 80
    const x1 = 100 + r * Math.cos(startRad)
    const y1 = 100 + r * Math.sin(startRad)
    const x2 = 100 + r * Math.cos(endRad)
    const y2 = 100 + r * Math.sin(endRad)
    const d = percent >= 100
      ? `M 100 20 A 80 80 0 1 1 99.9 20 Z`
      : `M 100 100 L ${x1} ${y1} A 80 80 0 ${largeArc} 1 ${x2} ${y2} Z`
    const item = { d, color: COLORS[i % COLORS.length], percent: Math.round(percent), app: app }
    startAngle = endAngle
    return item
  })
})

// ─── Превышения лимитов ───────────────────────────────────────────
const limitExceeded = computed(() => {
  const today = periodStats.value.apps || []
  const activeLimits = limits.value.filter(l => l.enabled)
  return activeLimits
    .map(limit => {
      const app = today.find(a => a.system_id === limit.system_id)
      const used = app ? app.duration_seconds : 0
      const max = limit.limit_minutes * 60
      return {
        app_name: limit.app_name,
        system_id: limit.system_id,
        limit_minutes: limit.limit_minutes,
        used_seconds: used,
        max_seconds: max,
        percent: max > 0 ? Math.round((used / max) * 100) : 0,
        exceeded: used > max,
      }
    })
    .sort((a, b) => b.percent - a.percent)
})

const limitColumns = [
  { title: 'Приложение', key: 'app' },
  { title: 'Лимит', key: 'limit', width: 80 },
  { title: 'Использовано', key: 'used', width: 100 },
  { title: 'Прогресс', key: 'bar' },
]

// ─── Загрузка ─────────────────────────────────────────────────────
async function loadStats() {
  loading.value = true
  try {
    periodStats.value = await api.getActivityForPeriod(
      startDate.value.format('YYYY-MM-DD'),
      endDate.value.format('YYYY-MM-DD')
    )
  } catch {
    periodStats.value = { total_seconds: 0, apps: [] }
    message.error('Ошибка загрузки статистики')
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  loadStats()
})
</script>

<template>
  <div>
    <div class="page-header">
      <h2>Статистика</h2>
      <div class="header-actions">
        <a-date-picker v-model:value="startDate" @change="loadStats" />
        <span class="text-muted">—</span>
        <a-date-picker v-model:value="endDate" @change="loadStats" />
        <a-button type="primary" @click="loadStats" :loading="loading">Показать</a-button>
      </div>
    </div>

    <a-row :gutter="[12, 12]" style="margin-bottom:20px">
      <a-col :xs="24" :sm="8">
        <a-card size="small" class="stat-card">
          <a-statistic :value="formatDuration(periodStats.total_seconds)" title="Всего за период" />
        </a-card>
      </a-col>
      <a-col :xs="12" :sm="8">
        <a-card size="small" class="stat-card">
          <a-statistic :value="periodStats.apps.length" title="Приложений" />
        </a-card>
      </a-col>
      <a-col :xs="12" :sm="8">
        <a-card size="small" class="stat-card">
          <a-statistic :value="periodStats.apps.length > 0 ? (periodStats.total_seconds / periodStats.apps.length / 60).toFixed(0) : 0" title="Среднее, мин" />
        </a-card>
      </a-col>
    </a-row>

    <!-- Превышения лимитов -->
    <a-card v-if="limitExceeded.length > 0" title="Лимиты" :bordered="false" style="margin-bottom:16px">
      <a-table class="desktop-table" :dataSource="limitExceeded" :columns="limitColumns"
        :pagination="false" rowKey="system_id" size="small">
        <template #bodyCell="{ column, record }">
          <template v-if="column.key === 'app'">
            <div class="app-name">{{ record.app_name }}</div>
            <div class="app-sid">{{ record.system_id }}</div>
          </template>
          <template v-if="column.key === 'limit'">
            <strong>{{ record.limit_minutes }} мин</strong>
          </template>
          <template v-if="column.key === 'used'">
            <span :class="{ 'text-danger': record.exceeded }">
              {{ formatDuration(record.used_seconds) }}
            </span>
          </template>
          <template v-if="column.key === 'bar'">
            <a-progress
              :percent="Math.min(record.percent, 100)"
              :status="record.exceeded ? 'exception' : 'active'"
              :strokeColor="record.exceeded ? '#ef4444' : record.percent > 80 ? '#f59e0b' : '#22c55e'"
              :format="() => `${record.percent}%`" />
          </template>
        </template>
      </a-table>

      <!-- Мобильные карточки лимитов -->
      <div class="mobile-cards">
        <div v-for="item in limitExceeded" :key="item.system_id" class="limit-card">
          <div class="limit-card-header">
            <div class="app-name">{{ item.app_name }}</div>
            <span :class="{ 'text-danger': item.exceeded }">
              {{ formatDuration(item.used_seconds) }} / {{ item.limit_minutes }} мин
            </span>
          </div>
          <a-progress
            :percent="Math.min(item.percent, 100)"
            :status="item.exceeded ? 'exception' : 'active'"
            :strokeColor="item.exceeded ? '#ef4444' : item.percent > 80 ? '#f59e0b' : '#22c55e'"
            :format="() => `${item.percent}%`" />
        </div>
      </div>
    </a-card>

    <a-row :gutter="[12, 12]">
      <!-- Круговая диаграмма -->
      <a-col :xs="24" :sm="10">
        <a-card title="Распределение" :bordered="false" style="height:100%">
          <div v-if="pieData.length > 0" class="pie-chart-container">
            <svg viewBox="0 0 200 200" class="pie-chart">
              <path v-for="(slice, i) in pieData" :key="i"
                :d="slice.d" :fill="slice.color" stroke="#0f1117" stroke-width="2" />
            </svg>
            <div class="pie-center">
              <div class="pie-total">{{ formatDuration(periodStats.total_seconds) }}</div>
              <div class="pie-label">всего</div>
            </div>
            <div class="pie-legend">
              <div v-for="(slice, i) in pieData" :key="i" class="legend-item">
                <span class="legend-dot" :style="{ background: slice.color }"></span>
                <span class="legend-name">{{ slice.app.app_name }}</span>
                <span class="legend-percent">{{ slice.percent }}%</span>
              </div>
              <div v-if="periodStats.apps.length > 10" class="legend-more">
                + ещё {{ periodStats.apps.length - 10 }} приложений
              </div>
            </div>
          </div>
          <a-empty v-else description="Нет данных за выбранный период" />
        </a-card>
      </a-col>

      <!-- Таблица -->
      <a-col :xs="24" :sm="14">
        <a-card title="Детализация" :bordered="false">
          <!-- Десктоп: таблица -->
          <a-table class="desktop-table" :dataSource="periodStats.apps" :columns="columns"
            :pagination="false" :loading="loading" rowKey="system_id" size="small">
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
                <a-progress :percent="percentOfTotal(record.duration_seconds, periodStats.total_seconds)"
                  :showInfo="false" :strokeColor="{ from: '#6366f1', to: '#22c55e' }" />
              </template>
            </template>
            <template #emptyText>
              <a-empty description="Выберите период и нажмите «Показать»" />
            </template>
          </a-table>

          <!-- Мобильные карточки -->
          <div class="mobile-cards">
            <div v-for="(item, i) in periodStats.apps" :key="item.system_id" class="activity-card">
              <div class="activity-card-top">
                <span class="activity-card-index">#{{ i + 1 }}</span>
                <div class="activity-card-app">
                  <div class="app-name">{{ item.app_name }}</div>
                  <div class="app-sid">{{ item.system_id }}</div>
                </div>
                <strong class="activity-card-time">{{ formatDuration(item.duration_seconds) }}</strong>
              </div>
              <a-progress :percent="percentOfTotal(item.duration_seconds, periodStats.total_seconds)"
                :showInfo="false" :strokeColor="{ from: '#6366f1', to: '#22c55e' }" />
            </div>
          </div>
        </a-card>
      </a-col>
    </a-row>
  </div>
</template>

<style scoped>
.pie-chart-container {
  display: flex; flex-direction: column; align-items: center; gap: 16px;
  position: relative;
}
.pie-chart { width: 200px; height: 200px; }
.pie-center {
  position: absolute; top: 60px; text-align: center; pointer-events: none;
}
.pie-total { font-size: 18px; font-weight: 700; color: #e1e4ed; }
.pie-label { font-size: 11px; color: #7a7f94; margin-top: 2px; }
.pie-legend { width: 100%; display: flex; flex-direction: column; gap: 6px; }
.legend-item {
  display: flex; align-items: center; gap: 8px; font-size: 12px;
}
.legend-dot {
  width: 10px; height: 10px; border-radius: 50%; flex-shrink: 0;
}
.legend-name { flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.legend-percent { color: #7a7f94; font-weight: 500; }
.legend-more { text-align: center; color: #7a7f94; font-size: 11px; padding-top: 4px; }
.text-danger { color: #ef4444; font-weight: 600; }

/* Мобильные карточки */
.mobile-cards { display: none; }
.activity-card {
  background: #1a1a1a;
  border: 1px solid #2a2a2a;
  border-radius: 8px;
  padding: 10px 12px;
  margin-bottom: 8px;
}
.activity-card-top {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 8px;
}
.activity-card-index { font-size: 12px; color: #666; min-width: 24px; }
.activity-card-app { flex: 1; }
.activity-card-time { font-size: 14px; white-space: nowrap; }
.limit-card {
  background: #1a1a1a;
  border: 1px solid #2a2a2a;
  border-radius: 8px;
  padding: 12px;
  margin-bottom: 10px;
}
.limit-card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 8px;
}

@media (max-width: 768px) {
  .desktop-table { display: none; }
  .mobile-cards { display: block; }
}
</style>
