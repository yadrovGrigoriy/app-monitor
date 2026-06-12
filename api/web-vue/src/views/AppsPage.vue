<script setup>
import { ref, computed, inject } from 'vue'
import { api } from '../api'
import { SearchOutlined, StopOutlined, EyeOutlined, EyeInvisibleOutlined } from '@ant-design/icons-vue'
import { message } from 'ant-design-vue'

const apps = inject('apps')
const limits = inject('limits')
const loading = inject('loading')
const refreshAll = inject('refreshAll')

const search = ref('')
const filterTracked = ref('all')

const columns = [
  { title: 'Приложение', key: 'app' },
  { title: 'System ID', key: 'sid' },
  { title: 'Отслеживается', key: 'tracked', width: 120 },
  { title: 'Лимит', key: 'limit', width: 100 },
  { title: 'Действия', key: 'actions', width: 100 }
]

const filteredApps = computed(() => {
  let result = apps.value
  const q = (search.value || '').toLowerCase()
  if (q) {
    result = result.filter(a =>
      a.app_name.toLowerCase().includes(q) ||
      a.system_id.toLowerCase().includes(q)
    )
  }
  if (filterTracked.value === 'tracked') {
    result = result.filter(a => a.is_tracked)
  } else if (filterTracked.value === 'untracked') {
    result = result.filter(a => !a.is_tracked)
  }
  return result
})

function getLimit(systemId) {
  return limits.value.find(l => l.system_id === systemId)
}

async function toggleTracked(app) {
  try {
    await api.toggleTracking(app.system_id, !app.is_tracked)
    message.success(app.is_tracked ? 'Отслеживание отключено' : 'Отслеживание включено')
    refreshAll()
  } catch (e) {
    message.error('Ошибка: ' + e.message)
  }
}

async function excludeApp(app) {
  try {
    await api.addExcluded(app.system_id)
    message.success(`"${app.app_name}" добавлен в исключения`)
    refreshAll()
  } catch (e) {
    message.error('Ошибка: ' + e.message)
  }
}
</script>

<template>
  <div>
    <div class="page-header">
      <h2>Приложения</h2>
      <div class="header-actions">
        <a-select v-model:value="filterTracked" style="width:160px" allowClear>
          <a-select-option value="all">Все</a-select-option>
          <a-select-option value="tracked">Отслеживаемые</a-select-option>
          <a-select-option value="untracked">Неотслеживаемые</a-select-option>
        </a-select>
        <a-input-search v-model:value="search" placeholder="Поиск..."
          style="width:240px" allowClear>
          <template #prefix><SearchOutlined /></template>
        </a-input-search>
      </div>
    </div>

    <a-card :bordered="false">
      <div v-if="loading && filteredApps.length === 0" class="loading-container">
        <a-spin size="large" />
        <p class="loading-text">Загрузка приложений...</p>
      </div>

      <template v-else>
        <!-- Десктоп: таблица -->
        <a-table class="desktop-table" :dataSource="filteredApps" :columns="columns"
          :pagination="{ pageSize: 20 }"
          :loading="loading && filteredApps.length > 0" rowKey="system_id" size="small">
          <template #bodyCell="{ column, record }">
            <template v-if="column.key === 'app'">
              <div class="app-name">{{ record.app_name }}</div>
            </template>
            <template v-else-if="column.key === 'sid'">
              <a-typography-text code>{{ record.system_id }}</a-typography-text>
            </template>
            <template v-else-if="column.key === 'tracked'">
              <a-tag :color="record.is_tracked ? 'green' : 'default'">
                {{ record.is_tracked ? 'Да' : 'Нет' }}
              </a-tag>
            </template>
            <template v-else-if="column.key === 'limit'">
              <a-tag v-if="getLimit(record.system_id)" color="blue">
                {{ getLimit(record.system_id).limit_minutes }} мин
              </a-tag>
              <span v-else class="text-muted">—</span>
            </template>
            <template v-else-if="column.key === 'actions'">
              <a-tooltip :title="record.is_tracked ? 'Отключить отслеживание' : 'Включить отслеживание'">
                <a-button size="small" :type="record.is_tracked ? 'default' : 'primary'"
                  @click="toggleTracked(record)" style="margin-right:4px">
                  <template #icon>
                    <EyeInvisibleOutlined v-if="record.is_tracked" />
                    <EyeOutlined v-else />
                  </template>
                </a-button>
              </a-tooltip>
              <a-popconfirm title="Исключить это приложение?"
                @confirm="excludeApp(record)" okText="Исключить" cancelText="Отмена">
                <a-tooltip title="Исключить из мониторинга">
                  <a-button size="small" danger>
                    <template #icon><StopOutlined /></template>
                  </a-button>
                </a-tooltip>
              </a-popconfirm>
            </template>
          </template>
        </a-table>

        <!-- Мобильные: карточки -->
        <div class="mobile-cards">
          <div v-for="app in filteredApps" :key="app.system_id" class="app-card">
            <div class="app-card-header">
              <div class="app-card-name">{{ app.app_name }}</div>
              <a-tag :color="app.is_tracked ? 'green' : 'default'" size="small">
                {{ app.is_tracked ? 'Отслеживается' : 'Не отслеживается' }}
              </a-tag>
            </div>
            <div class="app-card-sid">
              <a-typography-text code>{{ app.system_id }}</a-typography-text>
            </div>
            <div class="app-card-meta">
              <span v-if="getLimit(app.system_id)" class="app-card-limit">
                Лимит: <strong>{{ getLimit(app.system_id).limit_minutes }} мин</strong>
              </span>
              <span v-else class="text-muted">Лимит не задан</span>
            </div>
            <div class="app-card-actions">
              <a-button size="small" :type="app.is_tracked ? 'default' : 'primary'"
                @click="toggleTracked(app)" style="margin-right:6px">
                <template #icon>
                  <EyeInvisibleOutlined v-if="app.is_tracked" />
                  <EyeOutlined v-else />
                </template>
                {{ app.is_tracked ? 'Отключить' : 'Включить' }}
              </a-button>
              <a-popconfirm title="Исключить это приложение?"
                @confirm="excludeApp(app)" okText="Исключить" cancelText="Отмена">
                <a-button size="small" danger>
                  <StopOutlined /> Исключить
                </a-button>
              </a-popconfirm>
            </div>
          </div>
        </div>
      </template>
    </a-card>
  </div>
</template>

<style scoped>
.loading-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 64px 0;
}
.loading-text {
  margin-top: 16px;
  color: rgba(255,255,255,.45);
  font-size: 14px;
}

/* Мобильные карточки */
.mobile-cards { display: none; }
.app-card {
  background: #1a1a1a;
  border: 1px solid #2a2a2a;
  border-radius: 8px;
  padding: 12px;
  margin-bottom: 10px;
}
.app-card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 6px;
}
.app-card-name { font-weight: 600; font-size: 14px; }
.app-card-sid { margin-bottom: 6px; }
.app-card-meta { margin-bottom: 10px; font-size: 13px; color: #aaa; }
.app-card-limit { color: #ddd; }
.app-card-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

@media (max-width: 768px) {
  .desktop-table { display: none; }
  .mobile-cards { display: block; }
}
</style>
