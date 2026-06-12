/**
 * Компонент: дашборд — активность за сегодня.
 */
const DashboardPage = {
    template: `
        <div>
            <div class="page-header">
                <h2>Дашборд</h2>
                <div class="header-actions">
                    <span class="date-range">{{ today }}</span>
                    <a-button type="text" @click="$emit('refresh')" :loading="loading">🔄</a-button>
                </div>
            </div>

            <a-row :gutter="[12, 12]" style="margin-bottom:20px">
                <a-col :xs="12" :sm="6">
                    <a-card size="small" class="stat-card">
                        <statistic :value="stats.monitored_apps" title="Приложений сегодня" />
                    </a-card>
                </a-col>
                <a-col :xs="12" :sm="6">
                    <a-card size="small" class="stat-card">
                        <statistic :value="formatDuration(stats.total_today)" title="Всего времени сегодня" />
                    </a-card>
                </a-col>
                <a-col :xs="12" :sm="6">
                    <a-card size="small" class="stat-card">
                        <statistic :value="limitsCount" title="Активных лимитов" />
                    </a-card>
                </a-col>
                <a-col :xs="12" :sm="6">
                    <a-card size="small" class="stat-card">
                        <statistic :value="appsCount" title="Всего приложений" />
                    </a-card>
                </a-col>
            </a-row>

            <a-card title="Активность сегодня" :bordered="false">
                <a-table :dataSource="activity" :columns="columns" :pagination="false"
                    :loading="loading" rowKey="system_id" size="small">
                    <template #bodyCell="{ column, record, index }">
                        <template v-if="column.key === 'index'">{{ index + 1 }}</template>
                        <template v-if="column.key === 'app'">
                            <div class="app-name">{{ record.app_name }}</div>
                            <div class="app-sid">{{ record.system_id }}</div>
                        </template>
                        <template v-if="column.key === 'duration'">
                            <strong>{{ formatDuration(record.duration_seconds) }}</strong>
                        </template>
                        <template v-if="column.key === 'bar'">
                            <a-progress :percent="percentOfTotal(record.duration_seconds, stats.total_today)"
                                :showInfo="false" size="small" style="max-width:200px" />
                            <span class="progress-label">{{ percentOfTotal(record.duration_seconds, stats.total_today) }}%</span>
                        </template>
                    </template>
                    <template v-if="activity.length === 0">
                        <a-empty description="Нет данных за сегодня" />
                    </template>
                </a-table>
            </a-card>
        </div>
    `,
    props: {
        stats: Object,
        activity: Array,
        limitsCount: Number,
        appsCount: Number,
        loading: Boolean,
    },
    emits: ['refresh'],
    setup(props) {
        const today = ref(dayjs().format('DD MMMM YYYY'));
        const columns = [
            { title: '#', dataIndex: 'index', key: 'index', width: 40 },
            { title: 'Приложение', dataIndex: 'app_name', key: 'app' },
            { title: 'Время', dataIndex: 'duration_seconds', key: 'duration' },
            { title: 'Доля', key: 'bar' },
        ];
        return { today, columns, ...AppMonitorUtils };
    },
};
