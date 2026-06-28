<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { api } from '../api'
import { SendOutlined, MessageOutlined, UserOutlined } from '@ant-design/icons-vue'
import { message } from 'ant-design-vue'

const messageText = ref('')
const messageSending = ref(false)
const messages = ref([])
const loading = ref(true)
let pollTimer = null

function formatTime(isoStr) {
  if (!isoStr) return ''
  const d = new Date(isoStr)
  return d.toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit' })
}

async function loadHistory() {
  try {
    const resp = await api.get('/api/messages/history?limit=100')
    messages.value = resp.messages || []
  } catch (e) {
    console.error('Ошибка загрузки истории:', e)
  } finally {
    loading.value = false
  }
}

async function pollNewMessages() {
  try {
    const resp = await api.get('/api/messages/history?limit=100')
    if (resp.messages) {
      messages.value = resp.messages
    }
  } catch (e) {
    // игнорируем ошибки опроса
  }
}

async function handleSendMessage() {
  const text = messageText.value.trim()
  if (!text) return
  messageSending.value = true
  try {
    await api.sendMessage(text)
    messageText.value = ''
    await loadHistory()
    setTimeout(() => {
      const container = document.querySelector('.chat-feed')
      if (container) container.scrollTop = container.scrollHeight
    }, 100)
  } catch (e) {
    message.error('Ошибка отправки: ' + e.message)
  } finally {
    messageSending.value = false
  }
}

onMounted(() => {
  loadHistory()
  pollTimer = setInterval(pollNewMessages, 5000)
})

onUnmounted(() => {
  if (pollTimer) clearInterval(pollTimer)
})
</script>

<template>
  <div class="messages-page">
    <h2 class="page-title">Чат с пользователем</h2>
    <p class="page-desc">
      История сообщений между администратором и пользователем.
    </p>

    <div class="chat-card">
      <div class="chat-header">
        <MessageOutlined class="chat-icon" />
        <span>История сообщений</span>
      </div>

      <div class="chat-feed" ref="feedRef">
        <div v-if="loading" class="loading-text">Загрузка...</div>
        <div v-else-if="messages.length === 0" class="empty-text">
          Нет сообщений. Напишите пользователю.
        </div>
        <div
          v-for="msg in messages"
          :key="msg.id"
          :class="['msg-bubble', msg.sender === 'admin' ? 'msg-admin' : 'msg-user']"
        >
          <div class="msg-header">
            <span class="msg-sender">
              <template v-if="msg.sender === 'admin'">
                <UserOutlined /> Администратор
              </template>
              <template v-else>
                <UserOutlined /> Пользователь
              </template>
            </span>
            <span class="msg-time">{{ formatTime(msg.created_at) }}</span>
          </div>
          <div class="msg-text">{{ msg.text }}</div>
        </div>
      </div>

      <div class="chat-divider"></div>

      <div class="chat-body">
        <a-textarea
          v-model:value="messageText"
          placeholder="Введите сообщение для пользователя..."
          :rows="3"
          :maxlength="500"
          show-count
        />
        <div class="chat-actions">
          <a-button
            type="primary"
            size="large"
            @click="handleSendMessage"
            :loading="messageSending"
            :disabled="!messageText.trim()"
          >
            <template #icon><SendOutlined /></template>
            {{ messageSending ? 'Отправка...' : 'Отправить' }}
          </a-button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.messages-page {
  max-width: 720px;
  margin: 0 auto;
}
.page-title {
  font-size: 22px;
  font-weight: 700;
  color: #fff;
  margin-bottom: 8px;
}
.page-desc {
  color: rgba(255,255,255,.55);
  margin-bottom: 24px;
  font-size: 14px;
  line-height: 1.5;
}
.chat-card {
  background: #1a1a2e;
  border-radius: 12px;
  overflow: hidden;
  border: 1px solid rgba(255,255,255,.08);
}
.chat-header {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 16px 20px;
  background: rgba(99,102,241,.1);
  border-bottom: 1px solid rgba(255,255,255,.06);
  font-size: 15px;
  font-weight: 600;
  color: #e0e0e0;
}
.chat-icon {
  font-size: 18px;
  color: #6366f1;
}
.chat-feed {
  max-height: 400px;
  overflow-y: auto;
  padding: 16px 20px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.loading-text,
.empty-text {
  text-align: center;
  color: rgba(255,255,255,.35);
  padding: 40px 0;
  font-size: 14px;
}
.msg-bubble {
  padding: 12px 16px;
  border-radius: 10px;
  max-width: 85%;
}
.msg-admin {
  align-self: flex-start;
  background: rgba(99,102,241,.12);
  border: 1px solid rgba(99,102,241,.2);
}
.msg-user {
  align-self: flex-end;
  background: rgba(82,196,26,.1);
  border: 1px solid rgba(82,196,26,.15);
}
.msg-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 6px;
}
.msg-sender {
  font-size: 12px;
  font-weight: 600;
  color: #6366f1;
}
.msg-user .msg-sender {
  color: #52c41a;
}
.msg-time {
  font-size: 11px;
  color: rgba(255,255,255,.35);
}
.msg-text {
  font-size: 14px;
  color: #e0e0e0;
  line-height: 1.5;
  word-break: break-word;
}
.chat-divider {
  height: 1px;
  background: rgba(255,255,255,.06);
}
.chat-body {
  padding: 20px;
}
.chat-actions {
  margin-top: 16px;
  display: flex;
  align-items: center;
  gap: 12px;
}
</style>
