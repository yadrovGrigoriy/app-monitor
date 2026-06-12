<script setup>
import { ref, onMounted, onUnmounted, provide } from 'vue'
import { useRouter } from 'vue-router'
import { theme, message } from 'ant-design-vue'
import { api, getToken, setToken } from './api'
import { connect, disconnect, send, on } from './websocket'
import AppLayout from './components/AppLayout.vue'
import LoginPage from './components/LoginPage.vue'

const router = useRouter()
const isAuthenticated = ref(false)
const initialLoading = ref(true)
const serverStatus = ref('checking')
const uptime = ref(0)
const stats = ref({ monitored_apps: 0, total_today: 0 })
const apps = ref([])
const limits = ref([])
const settings = ref({})
const todayActivity = ref([])
const loading = ref(false)

async function onLoginSuccess() {
  message.success('Вход выполнен')
  await refreshAll()
  isAuthenticated.value = true
}

function onLogout() {
  setToken('')
  isAuthenticated.value = false
  router.push('/')
  message.info('Вы вышли из системы')
}

async function loadStatus() {
  try {
    const data = await api.getStatus()
    serverStatus.value = data.status
    uptime.value = data.uptime_seconds
    stats.value.monitored_apps = data.monitored_apps
  } catch { serverStatus.value = 'error' }
}

async function loadTodayActivity() {
  try {
    const data = await api.getTodayActivity()
    todayActivity.value = data
    stats.value.total_today = data.reduce((s, a) => s + a.duration_seconds, 0)
  } catch { todayActivity.value = [] }
}

async function loadApps() {
  try { apps.value = await api.getApps() }
  catch { apps.value = [] }
}

async function loadLimits() {
  try { limits.value = await api.getLimits() }
  catch { limits.value = [] }
}

async function loadSettings() {
  try {
    const data = await api.getSettings()
    const map = {}
    data.forEach(s => map[s.key] = s.value)
    settings.value = map
  } catch { settings.value = {} }
}

async function refreshAll() {
  loading.value = true
  await Promise.all([
    loadStatus(), loadTodayActivity(), loadApps(),
    loadLimits(), loadSettings(),
  ])
  loading.value = false
}

provide('stats', stats)
provide('todayActivity', todayActivity)
provide('apps', apps)
provide('limits', limits)
provide('settings', settings)
provide('loading', loading)
provide('serverStatus', serverStatus)
provide('uptime', uptime)
provide('refreshAll', refreshAll)
provide('wsSend', send)

// WebSocket — real-time обновления
let wsCleanups = []

function setupWebSocket() {
  wsCleanups.push(on('activity', (msg) => {
    if (msg.date === new Date().toISOString().slice(0, 10)) {
      todayActivity.value = msg.data
      stats.value.total_today = msg.data.reduce((s, a) => s + a.duration_seconds, 0)
    }
  }))
  wsCleanups.push(on('limits', (msg) => {
    limits.value = msg.data
  }))
  wsCleanups.push(on('connected', () => {
    send('get_today')
    send('get_limits')
  }))
  connect()
}

onMounted(async () => {
  // Проверяем, есть ли сохранённый токен
  const savedToken = getToken()
  if (savedToken) {
    // Пробуем загрузить данные — если токен протух, api.js сам его сбросит
    try {
      await refreshAll()
      isAuthenticated.value = true
      setInterval(refreshAll, 30000)
      setupWebSocket()
    } catch {
      // Токен недействителен — сбрасываем
      setToken('')
    }
  }
  initialLoading.value = false
})

onUnmounted(() => {
  disconnect()
  wsCleanups.forEach(fn => fn())
})
</script>

<template>
  <a-config-provider
    :theme="{
      algorithm: theme.darkAlgorithm,
      token: {
        colorPrimary: '#6366f1',
        borderRadius: 6,
        colorBgContainer: '#1a1d27',
        colorBgElevated: '#242736',
        colorBgLayout: '#0f1117',
        colorText: '#e1e4ed',
        colorTextSecondary: '#7a7f94',
        colorBorder: '#2a2d3a',
        colorBgMask: 'rgba(0,0,0,0.6)',
      },
    }">
    <div v-if="initialLoading" class="loading-screen">
      <a-spin size="large" tip="Загрузка..." />
    </div>
    <LoginPage v-else-if="!isAuthenticated" @login-success="onLoginSuccess" />
    <AppLayout v-else
      :serverStatus="serverStatus"
      :uptime="uptime"
      :appsCount="apps.length"
      :limitsCount="limits.length"
      @logout="onLogout">
      <router-view />
    </AppLayout>
  </a-config-provider>
</template>
