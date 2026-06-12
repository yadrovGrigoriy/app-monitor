<script setup>
import { ref, inject } from 'vue'
import { api } from '../api'
import LimitModal from '../components/LimitModal.vue'
import { PlusOutlined, EditOutlined, DeleteOutlined } from '@ant-design/icons-vue'

const limits = inject('limits')
const loading = inject('loading')
const refreshAll = inject('refreshAll')

const modalVisible = ref(false)
const editingLimit = ref(null)

const columns = [
  { title: 'Приложение', key: 'app' },
  { title: 'Лимит', key: 'limit', width: 100 },
  { title: 'Статус', key: 'status', width: 100 },
  { title: 'Действия', key: 'actions', width: 120 },
]

function openNew() {
  editingLimit.value = null
  modalVisible.value = true
}

function openEdit(limit) {
  editingLimit.value = { ...limit }
  modalVisible.value = true
}

async function handleDelete(limit) {
  try {
    await api.deleteLimit(limit.system_id)
    message.success(`Лимит для "${limit.app_name}" удалён`)
    refreshAll()
  } catch (e) {
    message.error('Ошибка: ' + e.message)
  }
}

function handleSaved() {
  modalVisible.value = false
  refreshAll()
}
</script>

<template>
  <div>
    <div class="page-header">
      <h2>Лимиты</h2>
      <a-button type="primary" @click="openNew">
        <PlusOutlined /> Добавить
      </a-button>
    </div>

    <a-card :bordered="false">
      <!-- Десктоп: таблица -->
      <a-table class="desktop-table" :dataSource="limits" :columns="columns"
        :pagination="{ pageSize: 20 }" :loading="loading" rowKey="system_id" size="small">
        <template #bodyCell="{ column, record }">
          <template v-if="column.key === 'app'">
            <div class="app-name">{{ record.app_name }}</div>
            <div class="app-sid">{{ record.system_id }}</div>
          </template>
          <template v-if="column.key === 'limit'">
            <strong>{{ record.limit_minutes }} мин</strong>
          </template>
          <template v-if="column.key === 'status'">
            <a-tag :color="record.enabled ? 'green' : 'default'">
              {{ record.enabled ? 'Активен' : 'Отключён' }}
            </a-tag>
          </template>
          <template v-if="column.key === 'actions'">
            <a-button size="small" @click="openEdit(record)" style="margin-right:8px">
              <EditOutlined />
            </a-button>
            <a-popconfirm title="Удалить лимит?" @confirm="handleDelete(record)" okText="Да" cancelText="Нет">
              <a-button size="small" danger>
                <DeleteOutlined />
              </a-button>
            </a-popconfirm>
          </template>
        </template>
      </a-table>

      <!-- Мобильные: карточки -->
      <div class="mobile-cards">
        <div v-for="limit in limits" :key="limit.system_id" class="limit-card">
          <div class="limit-card-header">
            <div class="app-name">{{ limit.app_name }}</div>
            <a-tag :color="limit.enabled ? 'green' : 'default'" size="small">
              {{ limit.enabled ? 'Активен' : 'Отключён' }}
            </a-tag>
          </div>
          <div class="app-sid">{{ limit.system_id }}</div>
          <div class="limit-card-body">
            <span class="limit-card-value">{{ limit.limit_minutes }} мин</span>
          </div>
          <div class="limit-card-actions">
            <a-button size="small" @click="openEdit(limit)" style="margin-right:8px">
              <EditOutlined /> Редактировать
            </a-button>
            <a-popconfirm title="Удалить лимит?" @confirm="handleDelete(limit)" okText="Да" cancelText="Нет">
              <a-button size="small" danger>
                <DeleteOutlined /> Удалить
              </a-button>
            </a-popconfirm>
          </div>
        </div>
      </div>
    </a-card>

    <LimitModal v-model:visible="modalVisible" :limit="editingLimit" @saved="handleSaved" />
  </div>
</template>

<style scoped>
.mobile-cards { display: none; }
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
  margin-bottom: 4px;
}
.limit-card-body { margin: 8px 0; }
.limit-card-value { font-size: 18px; font-weight: 700; color: #6366f1; }
.limit-card-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: 8px;
}

@media (max-width: 768px) {
  .desktop-table { display: none; }
  .mobile-cards { display: block; }
}
</style>
