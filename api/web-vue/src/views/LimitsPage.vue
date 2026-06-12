<script setup>
import { ref } from 'vue'
import { api } from '../api'
import LimitModal from '../components/LimitModal.vue'

const props = defineProps({
  limits: Array,
  loading: Boolean,
})

const emit = defineEmits(['refresh'])
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
    emit('refresh')
  } catch (e) {
    message.error('Ошибка: ' + e.message)
  }
}

function handleSaved() {
  modalVisible.value = false
  emit('refresh')
}
</script>

<template>
  <div>
    <div class="page-header">
      <h2>Лимиты</h2>
      <a-button type="primary" @click="openNew">+ Добавить лимит</a-button>
    </div>

    <a-card :bordered="false">
      <a-table :dataSource="limits" :columns="columns" :pagination="{ pageSize: 20 }"
        :loading="loading" rowKey="system_id" size="small">
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
            <a-button size="small" @click="openEdit(record)" style="margin-right:8px">✏️</a-button>
            <a-popconfirm title="Удалить лимит?" @confirm="handleDelete(record)" okText="Да" cancelText="Нет">
              <a-button size="small" danger>🗑️</a-button>
            </a-popconfirm>
          </template>
        </template>
      </a-table>
    </a-card>

    <LimitModal v-model:visible="modalVisible" :limit="editingLimit" @saved="handleSaved" />
  </div>
</template>
