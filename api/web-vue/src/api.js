const API_BASE = ''

let token = localStorage.getItem('token') || ''

export function setToken(val) {
  token = val
  if (val) localStorage.setItem('token', val)
  else localStorage.removeItem('token')
}

export function getToken() {
  return token
}

async function request(path, options = {}) {
  const headers = { 'Content-Type': 'application/json', ...options.headers }
  const activeToken = token || localStorage.getItem('token')
  if (activeToken) {
    headers['Authorization'] = `Bearer ${activeToken}`
  }
  const res = await fetch(`${API_BASE}${path}`, { ...options, headers })
  if (res.status === 401) {
    setToken('')
    throw new Error('Требуется авторизация')
  }
  if (!res.ok) {
    const text = await res.text()
    throw new Error(text || `HTTP ${res.status}`)
  }
  const ct = res.headers.get('content-type') || ''
  if (ct.includes('json')) return res.json()
  return res.text()
}

export const api = {
  login(username, password) {
    return request('/api/auth/login', {
      method: 'POST',
      body: JSON.stringify({ username, password }),
    })
  },

  getStatus() {
    return request('/api/status')
  },

  getTodayActivity() {
    return request('/api/activity/today')
  },

  getActivityForPeriod(start, end) {
    return request(`/api/activity/period?start=${start}&end=${end}`)
  },

  getApps() {
    return request('/api/apps')
  },

  toggleTracking(systemId, tracked) {
    return request('/api/apps/tracked', {
      method: 'POST',
      body: JSON.stringify({ system_id: systemId, tracked: tracked }),
    })
  },

  getLimits() {
    return request('/api/limits')
  },

  saveLimit(limit) {
    return request('/api/limits', {
      method: 'POST',
      body: JSON.stringify(limit),
    })
  },

  deleteLimit(systemId) {
    return request(`/api/limits/${encodeURIComponent(systemId)}`, {
      method: 'DELETE',
    })
  },

  getSettings() {
    return request('/api/settings')
  },

  clearAllData() {
    return request('/api/data/clear', {
      method: 'DELETE',
    })
  },

  getExcluded() {
    return request('/api/excluded')
  },

  addExcluded(systemId) {
    return request('/api/excluded', {
      method: 'POST',
      body: JSON.stringify({ system_id: systemId }),
    })
  },

  removeExcluded(systemId) {
    return request(`/api/excluded/${encodeURIComponent(systemId)}`, {
      method: 'DELETE',
    })
  },

  getAdmins() {
    return request('/api/admins')
  },

  addAdmin(username, password) {
    return request('/api/admins', {
      method: 'POST',
      body: JSON.stringify({ username, password }),
    })
  },

  deleteAdmin(username) {
    return request(`/api/admins/${encodeURIComponent(username)}`, {
      method: 'DELETE',
    })
  },

  uploadUpdate(file, onProgress) {
    return new Promise((resolve, reject) => {
      const formData = new FormData()
      formData.append('file', file)

      const xhr = new XMLHttpRequest()
      const activeToken = token || localStorage.getItem('token')

      xhr.upload.addEventListener('progress', (e) => {
        if (e.lengthComputable && onProgress) {
          onProgress(Math.round((e.loaded / e.total) * 100))
        }
      })

      xhr.addEventListener('load', () => {
        if (xhr.status === 200) {
          resolve(JSON.parse(xhr.responseText))
        } else if (xhr.status === 401) {
          setToken('')
          reject(new Error('Требуется авторизация'))
        } else {
          try {
            const err = JSON.parse(xhr.responseText)
            reject(new Error(err.detail || `HTTP ${xhr.status}`))
          } catch {
            reject(new Error(`HTTP ${xhr.status}`))
          }
        }
      })

      xhr.addEventListener('error', () => reject(new Error('Ошибка сети')))

      xhr.open('POST', `${API_BASE}/api/update/upload`)
      if (activeToken) {
        xhr.setRequestHeader('Authorization', `Bearer ${activeToken}`)
      }
      xhr.send(formData)
    })
  },
}
