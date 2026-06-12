/**
 * Компонент: управление приложениями.
 */
const AppsPage = {
    template: `
        <div>
            <div class="page-header">
                <h2>Приложения</h2>
                <div class="header-actions">
                    <a-input-search v-model:value="search" placeholder="Поиск приложения..."
                        style="width:240px" allowClear />
                </div>
            </div>

            <a-card :bordered="false">
                <a-table :dataSource="filteredApps" :columns="columns" :pagination="{ pageSize: 20 }"
                    :loading="loading" rowKey="system_id" size="small">
                    <template #bodyCell="{ column, record }">
                        <template v-if="column.key === 'app'">
                            <div class="app-name">{{ record.app_name }}</div>
                        </template>
                        <template v-if="column.key === 'sid'">
                            <a-typography-text code>{{ record.system_id }}</a-typography-text>
                        </template>
                        <template v-if="column.key === 'tracked'">
                            <a-tag :color="record.is_tracked ? 'green' : 'default'">
                                {{ record.is_tracked ? 'Да' : 'Нет' }}
                            </a-tag>
                        </template>
                        <template v-if="column.key === 'limit'">
                            <a-tag v-if="getLimit(record.system_id)" color="blue">
                                {{ getLimit(record.system_id).limit_minutes }} мин
                            </a-tag>
                            <span v-else class="text-muted">—</span>
                        </template>
                        <template v-if="column.key === 'actions'">
                            <a-button size="small" :type="record.is_tracked ? 'default' : 'primary'"
                                @click="toggleTracked(record)" style="margin-right:8px">
                                {{ record.is_tracked ? 'Отключить' : 'Отслеживать' }}
                            </a-button>
                            <a-button size="small" @click="$emit('set-limit', record)">
                                ⏱ Лимит
                            </a-button>
                        </template>
                    </template>
                </a-table>
            </a-card>
        </div>
    `,
    props: {
        apps: Array,
        limits: Array,
        loading: Boolean,
    },
    emits: ['set-limit'],
    setup(props) {
        const search = ref('');
        const columns = [
            { title: 'Приложение', key: 'app' },
            { title: 'System ID', key: 'sid' },
            { title: 'Отслеживается', key: 'tracked', width: 120 },
            { title: 'Лимит', key: 'limit', width: 100 },
            { title: 'Действия', key: 'actions', width: 200 },
        ];

        const filteredApps = computed(() => {
            const q = (search.value || '').toLowerCase();
            if (!q) return props.apps;
            return props.apps.filter(a =>
                a.app_name.toLowerCase().includes(q) ||
                a.system_id.toLowerCase().includes(q)
            );
        });

        function getLimit(systemId) {
            return props.limits.find(l => l.system_id === systemId);
        }

        async function toggleTracked(app) {
            try {
                await AppMonitorApi.toggleTracked(app.system_id, !app.is_tracked);
                message.success(`Отслеживание ${app.is_tracked ? 'отключено' : 'включено'} для "${app.app_name}"`);
                emit('refresh');
            } catch (e) {
                message.error('Ошибка: ' + e.message);
            }
        }

        const emit = getCurrentInstance().emit;

        return { search, columns, filteredApps, getLimit, toggleTracked };
    },
};
