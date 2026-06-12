export function formatDuration(seconds) {
  if (!seconds || seconds <= 0) return '0 мин'
  const h = Math.floor(seconds / 3600)
  const m = Math.floor((seconds % 3600) / 60)
  if (h > 0) return `${h} ч ${m} мин`
  return `${m} мин`
}

export function formatUptime(seconds) {
  if (!seconds || seconds <= 0) return '0 сек'
  const h = Math.floor(seconds / 3600)
  const m = Math.floor((seconds % 3600) / 60)
  const s = seconds % 60
  const parts = []
  if (h > 0) parts.push(`${h} ч`)
  if (m > 0) parts.push(`${m} мин`)
  parts.push(`${s} сек`)
  return parts.join(' ')
}

export function percentOfTotal(value, total) {
  if (!total || total <= 0) return 0
  return Math.round((value / total) * 100)
}
