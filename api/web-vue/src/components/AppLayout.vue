<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { formatUptime } from '../utils'
import { getConnectionStatus, on } from '../websocket'
import {
  DashboardOutlined,
  AppstoreOutlined,
  ClockCircleOutlined,
  BarChartOutlined,
  SettingOutlined,
  LogoutOutlined,
  SafetyCertificateOutlined,
  MenuOutlined,
  CloseOutlined,
} from '@ant-design/icons-vue'

const emit = defineEmits(['logout'])
const router = useRouter()
const route = useRoute()
const wsConnected = ref(getConnectionStatus())
const sidebarOpen = ref(false)

let wsCleanups = []
onMounted(() => {
  wsCleanups.push(on('connected', () => wsConnected.value = true))
  wsCleanups.push(on('disconnected', () => wsConnected.value = false))
})
onUnmounted(() => {
  wsCleanups.forEach(fn => fn())
})

function navigate(key) {
  router.push({ name: key })
  sidebarOpen.value = false
}

const props = defineProps({
  serverStatus: String,
  uptime: Number,
  appsCount: Number,
  limitsCount: Number,
})

const navItems = [
  { key: 'dashboard', icon: DashboardOutlined, label: 'Дашборд' },
  { key: 'apps', icon: AppstoreOutlined, label: 'Приложения', badge: () => props.appsCount },
  { key: 'limits', icon: ClockCircleOutlined, label: 'Лимиты', badge: () => props.limitsCount },
  { key: 'stats', icon: BarChartOutlined, label: 'Статистика' },
  { key: 'settings', icon: SettingOutlined, label: 'Настройки' },
]
</script>

<template>
  <div class="app-layout">
    <!-- Мобильный хедер -->
    <div class="mobile-header">
      <div class="mobile-header-left">
        <SafetyCertificateOutlined class="mobile-logo" />
        <span class="mobile-title">AppMonitor</span>
      </div>
      <div class="mobile-header-right">
        <div class="conn-block">
          <span class="conn-label">Сервер</span>
          <span class="conn-value" :class="{ ok: serverStatus === 'ok' }">
            {{ serverStatus === 'ok' ? 'онлайн' : 'ошибка' }}
          </span>
        </div>
        <div class="conn-block">
          <span class="conn-label">WS</span>
          <span class="conn-value" :class="{ ok: wsConnected }">
            {{ wsConnected ? 'онлайн' : 'офлайн' }}
          </span>
        </div>
        <a-button type="text" class="menu-btn" @click="emit('logout')">
          <LogoutOutlined />
        </a-button>
      </div>
    </div>

    <div class="layout-body">
      <!-- Затемнение фона на мобильных -->
      <div v-if="sidebarOpen" class="sidebar-overlay" @click="sidebarOpen = false" />

      <!-- Сайдбар (десктоп) -->
      <div class="sidebar" :class="{ 'sidebar-open': sidebarOpen }">
        <div class="sidebar-header">
          <SafetyCertificateOutlined class="sidebar-logo" />
          <span class="sidebar-title">AppMonitor</span>
        </div>
        <a-menu :selectedKeys="[route.name || 'dashboard']" mode="inline" theme="dark"
          @click="({ key }) => navigate(key)" class="sidebar-menu">
          <a-menu-item key="dashboard">
            <DashboardOutlined />
            <span>Дашборд</span>
          </a-menu-item>
          <a-menu-item key="apps">
            <AppstoreOutlined />
            <span>Приложения</span>
            <a-badge :count="appsCount" :overflow-count="999" size="small" class="menu-badge" />
          </a-menu-item>
          <a-menu-item key="limits">
            <ClockCircleOutlined />
            <span>Лимиты</span>
            <a-badge :count="limitsCount" :overflow-count="999" size="small" class="menu-badge" />
          </a-menu-item>
          <a-menu-item key="stats">
            <BarChartOutlined />
            <span>Статистика</span>
          </a-menu-item>
          <a-menu-item key="settings">
            <SettingOutlined />
            <span>Настройки</span>
          </a-menu-item>
        </a-menu>
        <div class="sidebar-footer">
          <div class="server-info">
            <a-badge :status="serverStatus === 'ok' ? 'success' : 'error'" />
            <span class="server-uptime" v-if="serverStatus === 'ok'">{{ formatUptime(uptime) }}</span>
          </div>
          <div class="ws-status">
            <a-badge :status="wsConnected ? 'success' : 'default'" />
            <span class="ws-label">{{ wsConnected ? 'WS: онлайн' : 'WS: офлайн' }}</span>
          </div>
          <a-button size="small" @click="emit('logout')" block>
            <LogoutOutlined /> Выйти
          </a-button>
        </div>
      </div>

      <div class="main-content">
        <slot />
      </div>
    </div>

    <!-- Док-панель (мобильная) -->
    <div class="dock-bar">
      <div v-for="item in navItems" :key="item.key" class="dock-item"
        :class="{ active: route.name === item.key }" @click="navigate(item.key)">
        <component :is="item.icon" class="dock-icon" />
        <span class="dock-label">{{ item.label }}</span>
<a-badge v-if="item.badge && item.badge() > 0"
          :count="item.badge()" :overflow-count="99" size="small" class="dock-badge" />
      </div>
    </div>
  </div>
</template>

<style scoped>
.app-layout {
  display: flex;
  flex-direction: column;
  min-height: 100vh;
  background: #0f1117;
}

.layout-body {
  display: flex;
  flex: 1;
  min-height: 0;
}

/* Сайдбар (десктоп) */
.sidebar {
  width: 220px;
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  background: #141414;
  z-index: 1000;
  transition: transform 0.25s ease;
}
.sidebar-header {
  display: flex; align-items: center; gap: 10px;
  padding: 16px 20px; border-bottom: 1px solid rgba(255,255,255,.1);
}
.sidebar-logo { font-size: 24px; color: #6366f1; }
.sidebar-title { font-size: 16px; font-weight: 700; color: #fff; }
.sidebar-menu { flex: 1; border-inline-end: none !important; }
.sidebar-footer {
  padding: 12px 16px; border-top: 1px solid rgba(255,255,255,.1);
  display: flex; flex-direction: column; gap: 8px;
}
.server-info { display: flex; align-items: center; gap: 8px; padding: 0 4px; color: rgba(255,255,255,.65); }
.server-uptime { font-size: 12px; }
.main-content {
  flex: 1;
  padding: 24px;
  min-height: 100vh;
  overflow-y: auto;
}
.menu-badge { margin-left: auto; }
.ws-status { display: flex; align-items: center; gap: 8px; padding: 0 4px; color: rgba(255,255,255,.45); }
.ws-label { font-size: 11px; }

/* Мобильный хедер */
.mobile-header {
  display: none;
  align-items: center;
  justify-content: space-between;
  padding: 8px 12px;
  background: #141414;
  border-bottom: 1px solid rgba(255,255,255,.1);
  position: sticky;
  top: 0;
  z-index: 999;
}
.mobile-header-left { display: flex; align-items: center; gap: 8px; }
.mobile-header-right { display: flex; align-items: center; gap: 8px; }
.mobile-logo { font-size: 20px; color: #6366f1; }
.mobile-title { font-size: 15px; font-weight: 700; color: #fff; }
.menu-btn { color: #fff; font-size: 16px; }
.conn-block { display: flex; flex-direction: column; align-items: center; gap: 0; }
.conn-label { font-size: 9px; color: #7a7f94; line-height: 1; }
.conn-value { font-size: 11px; color: #ef4444; font-weight: 600; line-height: 1.2; }
.conn-value.ok { color: #22c55e; }

/* Затемнение */
.sidebar-overlay {
  display: none;
  position: fixed;
  inset: 0;
  background: rgba(0,0,0,.5);
  z-index: 999;
}

/* Док-панель (мобильная) */
.dock-bar {
  display: none;
  position: fixed;
  bottom: 0; left: 0; right: 0;
  height: 60px;
  background: #141414;
  border-top: 1px solid rgba(255,255,255,.1);
  z-index: 1001;
  justify-content: space-around;
  align-items: center;
  padding: 4px 0 env(safe-area-inset-bottom, 4px) 0;
}
.dock-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2px;
  padding: 4px 8px;
  cursor: pointer;
  color: #7a7f94;
  transition: color 0.2s;
  position: relative;
  -webkit-tap-highlight-color: transparent;
}
.dock-item.active { color: #6366f1; }
.dock-item:active { opacity: 0.7; }
.dock-icon { font-size: 20px; }
.dock-label { font-size: 10px; line-height: 1; }
.dock-badge {
  position: absolute;
  top: 0; right: 2px;
}

/* ─── Мобильная адаптация ─────────────────────────────────────── */
@media (max-width: 768px) {
  .mobile-header { display: flex; }
  .sidebar { display: none; }
  .sidebar.sidebar-open {
    display: flex;
    position: fixed;
    left: 0; top: 48px; bottom: 60px;
    width: 100% !important;
    max-width: 100vw;
    z-index: 1000;
  }
  .sidebar-overlay { display: block; }
  .dock-bar { display: flex; }
  .main-content {
    padding: 12px;
    padding-bottom: 72px;
    min-height: calc(100vh - 48px);
  }
}
</style>
