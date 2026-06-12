<script setup>
import { ref, inject, onMounted } from 'vue'
import { api } from '../api'
import { formatUptime } from '../utils'
import { DeleteOutlined, UserAddOutlined, CloudUploadOutlined } from '@ant-design/icons-vue'
import { message } from 'ant-design-vue'

const settings = inject('settings')
const stats = inject('stats')
const serverStatus = inject('serverStatus')
const serverVersion = inject('serverVersion')
const uptime = inject('uptime')
const refreshAll = inject('refreshAll')

const admins = ref([])
const newAdminUsername = ref('')
const newAdminPassword = ref('')
const newAdminPasswordConfirm = ref('')
const showAddForm = ref(false)

// ─── Загрузка обновления ────────────────────────────────────────
const uploading = ref(false)
const uploadProgress = ref(0)
const uploadResult = ref(null)
const fileInput = ref(null)

function handleSelectFile() {
  fileInput.value?.click()
}

async function handleFileChange(e) {
  const file = e.target.files?.[0]
  if (!file) return

  if (!file.name.endsWith('.exe')) {
    message.warning('Пожалуйста, выберите .exe файл установщика')
    return
  }

  uploading.value = true
  uploadProgress.value = 0
  uploadResult.value = null

  try {
    const result = await api.uploadUpdate(file, (pct) => {
      uploadProgress.value = pct
    })
    uploadResult.value = result
    message.success(`Установщик ${result.filename} загружен`)
  } catch (e) {
    message.error('Ошибка загрузки: ' + e.message)
  } finally {
    uploading.value = false
    // Сбрасываем input, чтобы можно было загрузить тот же файл снова
    e.target.value = ''
  }
}

async function loadAdmins() {
  try {
    admins.value = await api.getAdmins()
  } catch (e) {
    console.error('Ошибка загрузки администраторов:', e)
  }
}

async function handleAddAdmin() {
  const username = newAdminUsername.value.trim()
  const password = newAdminPassword.value
  const confirm = newAdminPasswordConfirm.value

  if (!username) { message.warning('Введите логин'); return }
  if (!password) { message.warning('Введите пароль'); return }
  if (password !== confirm) { message.warning('Пароли не совпадают'); return }

  try {
    await api.addAdmin(username, password)
    message.success(`Администратор "${username}" добавлен`)
    newAdminUsername.value = ''
    newAdminPassword.value = ''
    newAdminPasswordConfirm.value = ''
    showAddForm.value = false
    await loadAdmins()
  } catch (e) {
    message.error('Ошибка: ' + e.message)
  }
}

async function handleDeleteAdmin(username) {
  try {
    await api.deleteAdmin(username)
    message.success(`Администратор "${username}" удалён`)
    await loadAdmins()
  } catch (e) {
    message.error('Ошибка: ' + e.message)
  }
}

async function handleClear() {
  try {
    await api.clearAllData()
    message.success('Все данные удалены')
    refreshAll()
  } catch (e) {
    message.error('Ошибка: ' + e.message)
  }
}

onMounted(loadAdmins)
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

    <a-card title="Администраторы" :bordered="false" style="margin-bottom:16px">
      <a-table
        :dataSource="admins"
        :columns="[
          { title: 'Логин', dataIndex: 'username', key: 'username' },
          { title: 'Действия', key: 'actions', width: 100 },
        ]"
        :pagination="false"
        size="small"
        rowKey="id"
        :locale="{ emptyText: 'Нет администраторов' }"
      >
        <template #bodyCell="{ record, column }">
          <template v-if="column.key === 'actions'">
            <a-popconfirm
              title="Удалить этого администратора?"
              @confirm="handleDeleteAdmin(record.username)"
              okText="Да" cancelText="Отмена"
            >
              <a-button type="link" danger size="small">
                <DeleteOutlined /> Удалить
              </a-button>
            </a-popconfirm>
          </template>
        </template>
      </a-table>

      <div style="margin-top:12px">
        <a-button type="dashed" @click="showAddForm = !showAddForm" v-if="!showAddForm">
          <UserAddOutlined /> Добавить администратора
        </a-button>

        <div v-if="showAddForm" style="margin-top:12px; max-width:400px">
          <a-input
            v-model:value="newAdminUsername"
            placeholder="Логин"
            style="margin-bottom:8px"
          />
          <a-input-password
            v-model:value="newAdminPassword"
            placeholder="Пароль"
            style="margin-bottom:8px"
          />
          <a-input-password
            v-model:value="newAdminPasswordConfirm"
            placeholder="Повторите пароль"
            style="margin-bottom:8px"
          />
          <div style="display:flex; gap:8px">
            <a-button type="primary" @click="handleAddAdmin">Добавить</a-button>
            <a-button @click="showAddForm = false">Отмена</a-button>
          </div>
        </div>
      </div>
    </a-card>

    <a-card title="О системе" :bordered="false" style="margin-bottom:16px">
      <a-descriptions :column="1" size="small" bordered>
        <a-descriptions-item label="Версия">
          <a-typography-text code>v{{ serverVersion || '—' }}</a-typography-text>
        </a-descriptions-item>
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

    <a-card title="Обновление" :bordered="false" style="margin-bottom:16px">
      <a-alert
        message="Загрузка установщика"
        description="Загрузите файл AppMonitor_Setup_X.X.X.exe на сервер. После загрузки клиенты смогут скачать новую версию через автообновление."
        type="info" show-icon style="margin-bottom:16px" />

      <input
        ref="fileInput"
        type="file"
        accept=".exe"
        style="display:none"
        @change="handleFileChange"
      />

      <div style="display:flex; flex-direction:column; gap:12px">
        <a-button
          type="primary"
          @click="handleSelectFile"
          :loading="uploading"
          :disabled="uploading"
          style="width:fit-content"
        >
          <CloudUploadOutlined />
          {{ uploading ? 'Загрузка...' : 'Выбрать установщик' }}
        </a-button>

        <a-progress
          v-if="uploading"
          :percent="uploadProgress"
          :status="uploadProgress === 100 ? 'success' : 'active'"
          style="max-width:400px"
        />

        <a-alert
          v-if="uploadResult"
          type="success"
          show-icon
          closable
          @close="uploadResult = null"
        >
          <template #message>
            <strong>{{ uploadResult.filename }}</strong> загружен
            <span v-if="uploadResult.version">(версия {{ uploadResult.version }})</span>
            — {{ (uploadResult.file_size / 1024 / 1024).toFixed(1) }} МБ
          </template>
        </a-alert>
      </div>
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
