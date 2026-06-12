/**
 * WebSocket клиент для real-time обновлений.
 * Подключается к /ws, автоматически переподключается при разрыве.
 */
const RECONNECT_DELAY = 3000

let ws = null
let reconnectTimer = null
let listeners = {}
let isConnected = false

function getWsUrl() {
  const proto = location.protocol === 'https:' ? 'wss:' : 'ws:'
  return `${proto}//${location.host}/ws`
}

export function connect() {
  if (ws && ws.readyState === WebSocket.OPEN) return

  ws = new WebSocket(getWsUrl())

  ws.onopen = () => {
    isConnected = true
    console.log('[WS] Подключено')
    emit('connected')
  }

  ws.onmessage = (event) => {
    try {
      const msg = JSON.parse(event.data)
      emit(msg.type, msg)
    } catch (e) {
      console.error('[WS] Ошибка парсинга:', e)
    }
  }

  ws.onclose = () => {
    isConnected = false
    console.log('[WS] Отключено, переподключение через', RECONNECT_DELAY, 'мс')
    emit('disconnected')
    reconnectTimer = setTimeout(connect, RECONNECT_DELAY)
  }

  ws.onerror = (err) => {
    console.error('[WS] Ошибка:', err)
    ws.close()
  }
}

export function disconnect() {
  if (reconnectTimer) {
    clearTimeout(reconnectTimer)
    reconnectTimer = null
  }
  if (ws) {
    ws.close()
    ws = null
  }
  isConnected = false
}

export function send(action, payload = {}) {
  if (!ws || ws.readyState !== WebSocket.OPEN) {
    console.warn('[WS] Не подключён, сообщение не отправлено')
    return
  }
  ws.send(JSON.stringify({ action, ...payload }))
}

export function on(event, callback) {
  if (!listeners[event]) listeners[event] = []
  listeners[event].push(callback)
  return () => {
    listeners[event] = listeners[event].filter(cb => cb !== callback)
  }
}

function emit(event, data) {
  if (listeners[event]) {
    listeners[event].forEach(cb => cb(data))
  }
}

export function getConnectionStatus() {
  return isConnected
}
