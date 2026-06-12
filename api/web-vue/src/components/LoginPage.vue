<script setup>
import { ref } from 'vue'
import { api, setToken } from '../api'
import { SafetyCertificateOutlined } from '@ant-design/icons-vue'

const emit = defineEmits(['login-success'])

const form = ref({ username: 'admin', password: 'admin' })
const error = ref('')
const loading = ref(false)

async function handleLogin() {
  loading.value = true
  error.value = ''
  try {
    const data = await api.login(form.value.username, form.value.password)
    setToken(data.token)
    emit('login-success')
  } catch (e) {
    error.value = e.message || 'Ошибка входа'
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="login-page">
    <a-card class="login-card" :bordered="false">
      <div class="login-header">
        <SafetyCertificateOutlined class="login-icon" />
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
</template>

<style scoped>
.login-page {
  display: flex; align-items: center; justify-content: center;
  min-height: 100vh; background: #0f1117;
}
.login-card { width: 380px; max-width: 90vw; }
.login-header { text-align: center; margin-bottom: 24px; }
.login-icon { font-size: 48px; color: #6366f1; margin-bottom: 8px; }
.login-header h1 { margin: 0; font-size: 22px; }
.login-subtitle { color: #7a7f94; margin-top: 4px; }
</style>
