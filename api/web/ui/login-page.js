/**
 * Компонент: страница логина.
 */
const LoginPage = {
    template: `
        <div class="login-page">
            <a-card class="login-card" :bordered="false">
                <div class="login-header">
                    <div class="login-icon">🛡️</div>
                    <h1>AppMonitor Admin</h1>
                    <p class="login-subtitle">Вход в панель управления</p>
                </div>
                <a-form :model="form" @finish="handleLogin" layout="vertical">
                    <a-form-item label="Логин" name="username"
                        :rules="[{ required: true, message: 'Введите логин' }]">
                        <a-input v-model:value="form.username" placeholder="admin" />
                    </a-form-item>
                    <a-form-item label="Пароль" name="password"
                        :rules="[{ required: true, message: 'Введите пароль' }]">
                        <a-input-password v-model:value="form.password" placeholder="••••••" />
                    </a-form-item>
                    <a-alert v-if="error" :message="error" type="error" show-icon style="margin-bottom:16px" />
                    <a-button type="primary" html-type="submit" :loading="loading" block>
                        Войти
                    </a-button>
                </a-form>
            </a-card>
        </div>
    `,
    emits: ['login-success'],
    setup(props, { emit }) {
        const form = ref({ username: 'admin', password: 'admin' });
        const error = ref('');
        const loading = ref(false);

        async function handleLogin() {
            error.value = '';
            loading.value = true;
            try {
                const data = await AppMonitorApi.login(form.value.username, form.value.password);
                AppMonitorApi.token = data.token;
                emit('login-success', data);
            } catch (e) {
                error.value = e.message || 'Ошибка входа';
            } finally {
                loading.value = false;
            }
        }

        return { form, error, loading, handleLogin };
    },
};
