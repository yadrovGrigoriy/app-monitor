<script setup>
import { inject } from 'vue'
import { api } from '../api'
import { formatUptime } from '../utils'
import { DeleteOutlined } from '@ant-design/icons-vue'

const settings = inject('settings')
const stats = inject('stats')
const serverStatus = inject('serverStatus')
const uptime = inject('uptime')
const refreshAll = inject('refreshAll')

async function handleClear() {
  try {
    await api.clearAllData()
    message.success('Все данные удалены')
    refreshAll()
  } catch (e) {
    message.error('Ошибка: ' + e.message)
  }
}
</script>

<template>
  <div>
    <div class="page-header">
      <h2>Настройки</h2>
    </div>

    <a-card title="Системные настройки" :bordered="false" style="margin-bottom:16px">
      <a-descriptions :column="1" size="small" bordered>
        <a-descriptions-item v-for="(val, key) in settings" :key="key" :label="key">
          <a-typography-text code>{{ val }}</a-typography-text>
        </a-descriptions-item>
        <a-descriptions-item v-if="Object.keys(settings).length === 0" label="—">
          Нет сохранённых настроек
        </a-descriptions-item>
      </a-descriptions>
    </a-card>

    <a-card title="О системе" :bordered="false" style="margin-bottom:16px">
      <a-descriptions :column="1" size="small" bordered>
        <a-descriptions-item label="Статус сервера">
          <a-badge :status="serverStatus === 'ok' ? 'success' : 'error'" />
          {{ serverStatus }}
        </a-descriptions-item>
        <a-descriptions-item label="Время работы">
          {{ formatUptime(uptime) }}
        </a-descriptions-item>
        <a-descriptions-item label="Отслеживается сегодня">
          {{ stats.monitored_apps }} приложений
        </a-descriptions-item>
      </a-descriptions>
    </a-card>

    <a-card title="Опасная зона" :bordered="false" class="card-danger">
      <a-alert
        message="Сброс всех данных"
        description="Удалит всю активность, лимиты и настройки. Действие необратимо."
        type="warning" show-icon style="margin-bottom:16px" />
      <a-popconfirm
        title="Вы уверены? Это удалит ВСЕ данные!"
        @confirm="handleClear"
        okText="Да, сбросить" cancelText="Отмена"
        :okButtonProps="{ danger: true }">
        <a-button danger block class="danger-btn">
          <DeleteOutlined /> Сбросить все данные
        </a-button>
      </a-popconfirm>
    </a-card>
  </div>
</template>

<style scoped>
@media (max-width: 768px) {
  .danger-btn { width: 100%; }
}
</style>
