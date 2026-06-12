/**
 * AppMonitor Admin — Vue.js 3 веб-интерфейс
 *
 * Подключается к REST API AppMonitor (порт 8765).
 * Требуется авторизация через Bearer token.
 */
const { createApp, ref, computed, watch, onMounted } = Vue;

const API_BASE = '';

const app = createApp({
    setup() {
        // ─── Состояние ────────────────────────────────────────────
        const auth = ref({ token: localStorage.getItem('token') || '', username: '' });
        const authForm = ref({ username: 'admin', password: 'admin' });
        const authError = ref('');
        const authLoading = ref(false);

        const currentTab = ref('dashboard');
        const serverStatus = ref('checking');
        const uptime = ref(0);
        const stats = ref({ monitored_apps: 0, total_today: 0 });
        const todayActivity = ref([]);
        const apps = ref([]);
        const limits = ref([]);
        const settings = ref({});
        const periodStats = ref({ total_seconds: 0, apps: [] });
        const periodStart = ref(new Date().toISOString().slice(0, 10));
        const periodEnd = ref(new Date().toISOString().slice(0, 10));
        const appSearch = ref('');

        const limitDialog = ref({ show: false, isNew: true, system_id: '', limit_minutes: 60, enabled: true });
        const confirmDialog = ref({ show: false, title: '', message: '', onConfirm: () => {} });
        const showAddLimit = ref(false);

        const today = computed(() => new Date().toLocaleDateString('ru-RU', {
            year: 'numeric', month: 'long', day: 'numeric'
        }));

        const filteredApps = computed(() => {
            const q = appSearch.value.toLowerCase();
            if (!q) return apps.value;
            return apps.value.filter(a =>
                a.app_name.toLowerCase().includes(q) ||
                a.system_id.toLowerCase().includes(q)
            );
        });

        const navItems = [
            { id: 'dashboard', label: 'Дашборд', icon: '📊' },
            { id: 'apps', label: 'Приложения', icon: '📱', badge: computed(() => apps.value.length) },
            { id: 'limits', label: 'Лимиты', icon: '⏱', badge: computed(() => limits.value.length) },
            { id: 'stats', label: 'Статистика', icon: '📈' },
            { id: 'settings', label: 'Настройки', icon: '⚙️' },
        ];

        // ─── API-запросы ──────────────────────────────────────────
        async function api(path, options = {}) {
            const headers = { 'Content-Type': 'application/json', ...options.headers };
            if (auth.value.token) {
                headers['Authorization'] = `Bearer ${auth.value.token}`;
            }
            const res = await fetch(`${API_BASE}${path}`, { ...options, headers });
            if (res.status === 401) {
                auth.value.token = '';
                localStorage.removeItem('token');
                throw new Error('Требуется авторизация');
            }
            if (!res.ok) {
                const text = await res.text();
                throw new Error(text || `HTTP ${res.status}`);
            }
            const ct = res.headers.get('content-type') || '';
            if (ct.includes('json')) return res.json();
            return res.text();
        }

        // ─── Авторизация ──────────────────────────────────────────
        async function login() {
            authError.value = '';
            authLoading.value = true;
            try {
                const data = await api('/api/auth/login', {
                    method: 'POST',
                    body: JSON.stringify(authForm.value),
                });
                auth.value.token = data.token;
                auth.value.username = data.username;
                localStorage.setItem('token', data.token);
                refreshAll();
            } catch (e) {
                authError.value = e.message || 'Ошибка входа';
            } finally {
                authLoading.value = false;
            }
        }

        function logout() {
            auth.value.token = '';
            auth.value.username = '';
            localStorage.removeItem('token');
        }

        // ─── Загрузка данных ──────────────────────────────────────
        async function loadStatus() {
            try {
                const data = await api('/api/status');
                serverStatus.value = data.status;
                uptime.value = data.uptime_seconds;
                stats.value.monitored_apps = data.monitored_apps;
            } catch {
                serverStatus.value = 'error';
            }
        }

        async function loadTodayActivity() {
            try {
                const data = await api('/api/activity/today');
                todayActivity.value = data;
                stats.value.total_today = data.reduce((s, a) => s + a.duration_seconds, 0);
            } catch { todayActivity.value = []; }
        }

        async function loadApps() {
            try { apps.value = await api('/api/apps'); }
            catch { apps.value = []; }
        }

        async function loadLimits() {
            try { limits.value = await api('/api/limits'); }
            catch { limits.value = []; }
        }

        async function loadSettings() {
            try {
                const data = await api('/api/settings');
                const map = {};
                data.forEach(s => map[s.key] = s.value);
                settings.value = map;
            } catch { settings.value = {}; }
        }

        async function loadPeriodStats() {
            try {
                periodStats.value = await api('/api/activity/period', {
                    method: 'POST',
                    body: JSON.stringify({ start_date: periodStart.value, end_date: periodEnd.value }),
                });
            } catch { periodStats.value = { total_seconds: 0, apps: [] }; }
        }

        async function refreshAll() {
            await Promise.all([
                loadStatus(), loadTodayActivity(), loadApps(),
                loadLimits(), loadSettings(),
            ]);
        }

        // ─── Действия с приложениями ──────────────────────────────
        async function toggleTracked(app) {
            try {
                await api('/api/apps/tracked', {
                    method: 'POST',
                    body: JSON.stringify({ system_id: app.system_id, tracked: !app.is_tracked }),
                });
                await loadApps();
                await loadLimits();
            } catch (e) { alert('Ошибка: ' + e.message); }
        }

        function getLimit(systemId) {
            return limits.value.find(l => l.system_id === systemId);
        }

        // ─── Действия с лимитами ──────────────────────────────────
        function showLimitDialog(app) {
            const existing = getLimit(app.system_id);
            limitDialog.value = {
                show: true,
                isNew: !existing,
                system_id: app.system_id,
                limit_minutes: existing ? existing.limit_minutes : 60,
                enabled: existing ? existing.enabled : true,
            };
        }

        function editLimit(limit) {
            limitDialog.value = {
                show: true,
                isNew: false,
                system_id: limit.system_id,
                limit_minutes: limit.limit_minutes,
                enabled: limit.enabled,
            };
        }

        async function saveLimit() {
            try {
                const d = limitDialog.value;
                const app = apps.value.find(a => a.system_id === d.system_id);
                await api('/api/limits', {
                    method: 'POST',
                    body: JSON.stringify({
                        system_id: d.system_id,
                        limit_minutes: d.limit_minutes,
                        enabled: d.enabled,
                        app_name: app ? app.app_name : d.system_id,
                    }),
                });
                limitDialog.value.show = false;
                await loadLimits();
                await loadApps();
            } catch (e) { alert('Ошибка: ' + e.message); }
        }

        async function deleteLimit(limit) {
            confirmDialog.value = {
                show: true,
                title: 'Удалить лимит',
                message: `Удалить лимит для "${limit.app_name}"?`,
                onConfirm: async () => {
                    confirmDialog.value.show = false;
                    try {
                        await api(`/api/limits/${limit.system_id}`, { method: 'DELETE' });
                        await loadLimits();
                    } catch (e) { alert('Ошибка: ' + e.message); }
                },
            };
        }

        // ─── Опасная зона ─────────────────────────────────────────
        function confirmClearData() {
            confirmDialog.value = {
                show: true,
                title: 'Сброс всех данных',
                message: 'Вы уверены? Это удалит всю активность, лимиты, настройки и приложения. Действие необратимо.',
                onConfirm: async () => {
                    confirmDialog.value.show = false;
                    try {
                        await api('/api/data/clear', { method: 'POST' });
                        await refreshAll();
                    } catch (e) { alert('Ошибка: ' + e.message); }
                },
            };
        }

        // ─── Утилиты ──────────────────────────────────────────────
        function formatDuration(seconds) {
            if (!seconds || seconds <= 0) return '0 мин';
            const h = Math.floor(seconds / 3600);
            const m = Math.floor((seconds % 3600) / 60);
            if (h > 0) return `${h} ч ${m} мин`;
            return `${m} мин`;
        }

        function formatUptime(seconds) {
            if (!seconds) return '—';
            const h = Math.floor(seconds / 3600);
            const m = Math.floor((seconds % 3600) / 60);
            const s = seconds % 60;
            return `${h}ч ${m}м ${s}с`;
        }

        function percentOfTotal(seconds, total) {
            const t = total || stats.value.total_today;
            if (!t) return 0;
            return Math.round((seconds / t) * 100);
        }

        // ─── Следим за showAddLimit ───────────────────────────────
        watch(showAddLimit, (val) => {
            if (val) {
                limitDialog.value = {
                    show: true, isNew: true,
                    system_id: '', limit_minutes: 60, enabled: true,
                };
                showAddLimit.value = false;
            }
        });

        // ─── Инициализация ────────────────────────────────────────
        onMounted(() => {
            if (auth.value.token) {
                refreshAll();
                // Автообновление каждые 30 секунд
                setInterval(refreshAll, 30000);
            }
        });

        return {
            auth, authForm, authError, authLoading,
            login, logout,
            currentTab, navItems,
            serverStatus, uptime, stats, today,
            todayActivity, apps, limits, settings,
            periodStats, periodStart, periodEnd, loadPeriodStats,
            appSearch, filteredApps,
            limitDialog, showAddLimit, confirmDialog,
            toggleTracked, getLimit,
            showLimitDialog, editLimit, saveLimit, deleteLimit,
            confirmClearData, refreshAll,
            formatDuration, formatUptime, percentOfTotal,
        };
    },
});

app.mount('#app');
