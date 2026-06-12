<script setup>
import { computed, inject } from 'vue'
import { formatDuration, percentOfTotal } from '../utils'
import { ReloadOutlined } from '@ant-design/icons-vue'

const stats = inject('stats')
const todayActivity = inject('todayActivity')
const loading = inject('loading')
const refreshAll = inject('refreshAll')

const limits = inject('limits')
const apps = inject('apps')

const limitsCount = computed(() => limits.value.length)
const appsCount = computed(() => apps.value.length)

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
        <a-button type="text" @click="refreshAll" :loading="loading">
          <ReloadOutlined />
        </a-button>
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
          <a-statistic :value="formatDuration(stats.total_today)" title="Всего времени" />
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
      <template v-if="todayActivity.length > 0">
        <!-- Десктоп: таблица -->
        <a-table class="desktop-table" :dataSource="todayActivity" :columns="columns"
          :pagination="false" :loading="loading" rowKey="system_id" size="small">
          <template #bodyCell="{ column, record, index }">
            <template v-if="column.key === 'index'">{{ index + 1 }}</template>
            <template v-else-if="column.key === 'app'">
              <div class="app-name">{{ record.app_name }}</div>
              <div class="app-sid">{{ record.system_id }}</div>
            </template>
            <template v-else-if="column.key === 'duration'">
              <strong>{{ formatDuration(record.duration_seconds) }}</strong>
            </template>
            <template v-else-if="column.key === 'bar'">
              <a-progress :percent="percentOfTotal(record.duration_seconds, stats.total_today)"
                :showInfo="false" :strokeColor="{ from: '#6366f1', to: '#22c55e' }" />
            </template>
          </template>
          <template #emptyText>
            <a-empty description="Сегодня активности пока нет" />
          </template>
        </a-table>

        <!-- Мобильные: карточки -->
        <div class="mobile-cards">
          <div v-for="(item, i) in todayActivity" :key="item.system_id" class="activity-card">
            <div class="activity-card-top">
              <span class="activity-card-index">#{{ i + 1 }}</span>
              <div class="activity-card-app">
                <div class="app-name">{{ item.app_name }}</div>
                <div class="app-sid">{{ item.system_id }}</div>
              </div>
              <strong class="activity-card-time">{{ formatDuration(item.duration_seconds) }}</strong>
            </div>
            <a-progress :percent="percentOfTotal(item.duration_seconds, stats.total_today)"
              :showInfo="false" :strokeColor="{ from: '#6366f1', to: '#22c55e' }" />
          </div>
        </div>
      </template>
      <div v-else-if="!loading" class="empty-container">
        <a-empty description="Сегодня активности пока нет" />
      </div>
    </a-card>
  </div>
</template>

<style scoped>
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
.activity-card-index {
  font-size: 12px;
  color: #666;
  min-width: 24px;
}
.activity-card-app { flex: 1; }
.activity-card-time { font-size: 14px; white-space: nowrap; }

@media (max-width: 768px) {
  .desktop-table { display: none; }
  .mobile-cards { display: block; }
}
</style>
