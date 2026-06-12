/**
 * Компонент: настройки и информация о системе.
 */
const SettingsPage = {
    template: `
        <div>
            <div class="page-header">
                <h2>Настройки</h2>
            </div>

            <a-card title="Системные настройки" :bordered="false" style="margin-bottom:16px">
                <a-descriptions :column="1" size="small" bordered>
                    <a-descriptions-item v-for="(val, key) in settings" :key="key" :label="key">
                        <a-typography-text code>{{ val }}</a-typography-text>
                    </a-descriptions-item>
                    <a-descriptions-item v-if="Object.keys(settings).length === 0" label="—">
                        Нет сохранённых настроек
                    </a-descriptions-item>
                </a-descriptions>
            </a-card>

            <a-card title="О системе" :bordered="false" style="margin-bottom:16px">
                <a-descriptions :column="1" size="small" bordered>
                    <a-descriptions-item label="Статус сервера">
                        <a-badge :status="serverStatus === 'ok' ? 'success' : 'error'" />
                        {{ serverStatus }}
                    </a-descriptions-item>
                    <a-descriptions-item label="Время работы">
                        {{ uptime }}
                    </a-descriptions-item>
                    <a-descriptions-item label="Отслеживается сегодня">
                        {{ monitoredApps }} приложений
                    </a-descriptions-item>
                </a-descriptions>
            </a-card>

            <a-card title="Опасная зона" :bordered="false" class="card-danger">
                <a-alert
                    message="Сброс всех данных"
                    description="Удалит всю активность, лимиты и настройки. Действие необратимо."
                    type="warning" show-icon style="margin-bottom:16px" />
                <a-popconfirm title="Вы уверены? Это удалит ВСЕ данные!" @confirm="handleClear"
                    okText="Да, сбросить" cancelText="Отмена" okType="danger">
                    <a-button danger>Сбросить все данные</a-button>
                </a-popconfirm>
            </a-card>
        </div>
    `,
    props: {
        settings: Object,
        serverStatus: String,
        uptime: String,
        monitoredApps: Number,
    },
    emits: ['clear-data'],
    setup(props, { emit }) {
        async function handleClear() {
            try {
                await AppMonitorApi.clearData();
                message.success('Все данные очищены');
                emit('clear-data');
            } catch (e) {
                message.error('Ошибка: ' + e.message);
            }
        }
        return { handleClear };
    },
};
