import { createRouter, createWebHistory } from 'vue-router'
import DashboardPage from './views/DashboardPage.vue'
import AppsPage from './views/AppsPage.vue'
import LimitsPage from './views/LimitsPage.vue'
import StatsPage from './views/StatsPage.vue'
import SettingsPage from './views/SettingsPage.vue'

const routes = [
  { path: '/', redirect: '/dashboard' },
  { path: '/dashboard', name: 'dashboard', component: DashboardPage, meta: { title: 'Дашборд' } },
  { path: '/apps', name: 'apps', component: AppsPage, meta: { title: 'Приложения' } },
  { path: '/limits', name: 'limits', component: LimitsPage, meta: { title: 'Лимиты' } },
  { path: '/stats', name: 'stats', component: StatsPage, meta: { title: 'Статистика' } },
  { path: '/settings', name: 'settings', component: SettingsPage, meta: { title: 'Настройки' } },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

// Динамический title страницы
router.afterEach((to) => {
  const title = to.meta?.title
  document.title = title ? `AppMonitor — ${title}` : 'AppMonitor Admin'
})

export default router
