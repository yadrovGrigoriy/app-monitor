/**
 * API-клиент для AppMonitor REST API.
 * Все запросы проходят через единую функцию api().
 */
const AppMonitorApi = {
    _token: localStorage.getItem('token') || '',

    get token() { return this._token; },
    set token(val) {
        this._token = val;
        if (val) localStorage.setItem('token', val);
        else localStorage.removeItem('token');
    },

    async request(path, options = {}) {
        const headers = { 'Content-Type': 'application/json', ...options.headers };
        if (this._token) {
            headers['Authorization'] = `Bearer ${this._token}`;
        }
        const res = await fetch(path, { ...options, headers });
        if (res.status === 401) {
            this.token = '';
            throw new Error('Требуется авторизация');
        }
        if (!res.ok) {
            const text = await res.text();
            throw new Error(text || `HTTP ${res.status}`);
        }
        const ct = res.headers.get('content-type') || '';
        if (ct.includes('json')) return res.json();
        return res.text();
    },

    // ─── Авторизация ──────────────────────────────────────────────
    login(username, password) {
        return this.request('/api/auth/login', {
            method: 'POST',
            body: JSON.stringify({ username, password }),
        });
    },

    // ─── Статус ───────────────────────────────────────────────────
    getStatus() {
        return this.request('/api/status');
    },

    // ─── Активность ───────────────────────────────────────────────
    getTodayActivity() {
        return this.request('/api/activity/today');
    },

    getActivityForPeriod(startDate, endDate) {
        return this.request('/api/activity/period', {
            method: 'POST',
            body: JSON.stringify({ start_date: startDate, end_date: endDate }),
        });
    },

    // ─── Приложения ───────────────────────────────────────────────
    getApps() {
        return this.request('/api/apps');
    },

    toggleTracked(systemId, tracked) {
        return this.request('/api/apps/tracked', {
            method: 'POST',
            body: JSON.stringify({ system_id: systemId, tracked }),
        });
    },

    // ─── Лимиты ───────────────────────────────────────────────────
    getLimits() {
        return this.request('/api/limits');
    },

    saveLimit(data) {
        return this.request('/api/limits', {
            method: 'POST',
            body: JSON.stringify(data),
        });
    },

    deleteLimit(systemId) {
        return this.request(`/api/limits/${systemId}`, { method: 'DELETE' });
    },

    // ─── Настройки ────────────────────────────────────────────────
    getSettings() {
        return this.request('/api/settings');
    },

    // ─── Очистка ──────────────────────────────────────────────────
    clearData() {
        return this.request('/api/data/clear', { method: 'POST' });
    },
};
