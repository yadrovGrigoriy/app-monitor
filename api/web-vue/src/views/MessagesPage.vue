<COMPRESSED>
<COMPRESSED>
<script setup>
import { ref } from 'vue'
import { api } from '../api'
import { SendOutlined } from '@ant-design/icons-vue'
import { message } from 'ant-design-vue'

const messageText = ref('')
const messageSending = ref(false)
const messageSent = ref(false)

async function handleSendMessage() {
  const text = messageText.value.trim()
  if (!text) return
  messageSending.value = true
  messageSent.value = false
  try {
    await api.sendMessage(text)
    messageSent.value = true
    messageText.value = ''
    setTimeout(() => { messageSent.value = false }, 3000)
  } catch (e) {
    message.error('Ошибка отправки: ' + e.message)
  } finally {
    messageSending.value = false
  }
}
</script>

<template>
  <div class="messages-page">
    <h2 class="page-title">Чат с пользователем</h2>
    <p class="page-desc">
      Отправьте сообщение, которое появится в трей-уведомлении на всех запущенных клиентах AppMonitor.
    </p>

    <div class="chat-card">
      <div class="chat-header">
        <SendOutlined class="chat-icon" />
        <span>Новое сообщение</span>
      </div>
      <div class="chat-body">
        <a-textarea
          v-model:value="messageText"
          placeholder="Введите сообщение для пользователя..."
          :rows="4"
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
          <span v-if="messageSent" class="sent-ok">
            ✓ Сообщение отправлено
          </span>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.messages-page {
  max-width: 640px;
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
.chat-body {
  padding: 20px;
}
.chat-actions {
  margin-top: 16px;
  display: flex;
  align-items: center;
  gap: 12px;
}
.sent-ok {
  color: #52c41a;
  font-size: 14px;
}
</style>
</COMPRESSED>