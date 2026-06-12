/**
 * Компонент: основной лейаут с сайдбаром.
 */
const AppLayout = {
    template: `
        <a-layout class="app-layout">
            <a-layout-sider :width="220" class="sidebar" theme="dark">
                <div class="sidebar-header">
                    <span class="sidebar-logo">📊</span>
                    <span class="sidebar-title">AppMonitor</span>
                </div>
                <a-menu :selectedKeys="[currentTab]" mode="inline" theme="dark"
                    @click="onMenuClick" class="sidebar-menu">
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
                        <span class="server-uptime" v-if="serverStatus === 'ok'">{{ uptime }}</span>
                    </div>
                    <a-button size="small" @click="handleLogout" block>Выйти</a-button>
                </div>
            </a-layout-sider>
            <a-layout-content class="main-content">
                <slot />
            </a-layout-content>
        </a-layout>
    `,
    props: {
        currentTab: String,
        serverStatus: String,
        uptime: String,
        appsCount: Number,
        limitsCount: Number,
    },
    emits: ['tab-change', 'logout'],
    setup(props, { emit }) {
        function onMenuClick({ key }) {
            emit('tab-change', key);
        }
        function handleLogout() {
            AppMonitorApi.token = '';
            emit('logout');
        }
        return { onMenuClick, handleLogout };
    },
};
