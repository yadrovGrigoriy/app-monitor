/**
 * Компонент: управление лимитами.
 */
const LimitsPage = {
    template: `
        <div>
            <div class="page-header">
                <h2>Лимиты</h2>
                <a-button type="primary" @click="$emit('add-limit')">+ Добавить лимит</a-button>
            </div>

            <a-card :bordered="false">
                <a-table :dataSource="limits" :columns="columns" :pagination="{ pageSize: 20 }"
                    :loading="loading" rowKey="system_id" size="small">
                    <template #bodyCell="{ column, record }">
                        <template v-if="column.key === 'app'">
                            <div class="app-name">{{ record.app_name }}</div>
                            <div class="app-sid">{{ record.system_id }}</div>
                        </template>
                        <template v-if="column.key === 'limit'">
                            <strong>{{ record.limit_minutes }} мин</strong>
                        </template>
                        <template v-if="column.key === 'status'">
                            <a-tag :color="record.enabled ? 'green' : 'default'">
                                {{ record.enabled ? 'Активен' : 'Отключён' }}
                            </a-tag>
                        </template>
                        <template v-if="column.key === 'actions'">
                            <a-button size="small" @click="$emit('edit-limit', record)" style="margin-right:8px">✏️</a-button>
                            <a-popconfirm title="Удалить лимит?" @confirm="$emit('delete-limit', record)"
                                okText="Да" cancelText="Нет">
                                <a-button size="small" danger>🗑️</a-button>
                            </a-popconfirm>
                        </template>
                    </template>
                </a-table>
            </a-card>
        </div>
    `,
    props: {
        limits: Array,
        loading: Boolean,
    },
    emits: ['add-limit', 'edit-limit', 'delete-limit'],
    setup() {
        const columns = [
            { title: 'Приложение', key: 'app' },
            { title: 'Лимит', key: 'limit', width: 100 },
            { title: 'Статус', key: 'status', width: 100 },
            { title: 'Действия', key: 'actions', width: 120 },
        ];
        return { columns };
    },
};
