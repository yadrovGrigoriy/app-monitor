/**
 * Утилиты для форматирования и вычислений.
 */
const AppMonitorUtils = {
    formatDuration(seconds) {
        if (!seconds || seconds <= 0) return '0 мин';
        const h = Math.floor(seconds / 3600);
        const m = Math.floor((seconds % 3600) / 60);
        if (h > 0) return `${h} ч ${m} мин`;
        return `${m} мин`;
    },

    formatUptime(seconds) {
        if (!seconds) return '—';
        const h = Math.floor(seconds / 3600);
        const m = Math.floor((seconds % 3600) / 60);
        const s = seconds % 60;
        return `${h}ч ${m}м ${s}с`;
    },

    percentOfTotal(seconds, total) {
        if (!total) return 0;
        return Math.round((seconds / total) * 100);
    },
};
