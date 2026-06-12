<script setup>
import { useRouter, useRoute } from 'vue-router'
import { formatUptime } from '../utils'

defineProps({
  serverStatus: String,
  uptime: Number,
  appsCount: Number,
  limitsCount: Number,
})

const emit = defineEmits(['logout'])
const router = useRouter()
const route = useRoute()

const currentTab = route.name || 'dashboard'
</script>

<template>
  <a-layout class="app-layout">
    <a-layout-sider :width="220" class="sidebar" theme="dark">
      <div class="sidebar-header">
        <span class="sidebar-logo">📊</span>
        <span class="sidebar-title">AppMonitor</span>
      </div>
      <a-menu :selectedKeys="[route.name || 'dashboard']" mode="inline" theme="dark"
        @click="({ key }) => router.push({ name: key })" class="sidebar-menu">
        <a-menu-item key="dashboard">
          <span class="anticon">📊</span>
          <span>Дашборд</span>
        </a-menu-item>
        <a-menu-item key="apps">
          <span class="anticon">📱</span>
          <span>Приложения</span>
          <a-badge :count="appsCount" :overflow-count="999" size="small" class="menu-badge" />
        </a-menu-item>
        <a-menu-item key="limits">
          <span class="anticon">⏱</span>
          <span>Лимиты</span>
          <a-badge :count="limitsCount" :overflow-count="999" size="small" class="menu-badge" />
        </a-menu-item>
        <a-menu-item key="stats">
          <span class="anticon">📈</span>
          <span>Статистика</span>
        </a-menu-item>
        <a-menu-item key="settings">
          <span class="anticon">⚙️</span>
          <span>Настройки</span>
        </a-menu-item>
      </a-menu>
      <div class="sidebar-footer">
        <div class="server-info">
          <a-badge :status="serverStatus === 'ok' ? 'success' : 'error'" />
          <span class="server-uptime" v-if="serverStatus === 'ok'">{{ formatUptime(uptime) }}</span>
        </div>
        <a-button size="small" @click="emit('logout')" block>Выйти</a-button>
      </div>
    </a-layout-sider>

    <a-layout-content class="main-content">
      <slot />
    </a-layout-content>
  </a-layout>
</template>

<style scoped>
.app-layout { min-height: 100vh; }
.sidebar { position: fixed; left: 0; top: 0; bottom: 0; display: flex; flex-direction: column; }
.sidebar-header {
  display: flex; align-items: center; gap: 10px;
  padding: 16px 20px; border-bottom: 1px solid rgba(255,255,255,.1);
}
.sidebar-logo { font-size: 24px; }
.sidebar-title { font-size: 16px; font-weight: 700; color: #fff; }
.sidebar-menu { flex: 1; border-inline-end: none !important; }
.sidebar-footer {
  padding: 12px 16px; border-top: 1px solid rgba(255,255,255,.1);
  display: flex; flex-direction: column; gap: 8px;
}
.server-info { display: flex; align-items: center; gap: 8px; padding: 0 4px; color: rgba(255,255,255,.65); }
.server-uptime { font-size: 12px; }
.main-content { margin-left: 220px; padding: 24px; min-height: 100vh; }
.menu-badge { margin-left: auto; }
</style>
