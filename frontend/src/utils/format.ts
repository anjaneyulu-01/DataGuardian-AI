/** Formatting helpers shared across pages. */

const RELATIVE_UNITS: [Intl.RelativeTimeFormatUnit, number][] = [
  ['year', 31536000],
  ['month', 2592000],
  ['week', 604800],
  ['day', 86400],
  ['hour', 3600],
  ['minute', 60],
]

const relativeFormatter = new Intl.RelativeTimeFormat('en', { numeric: 'auto' })

/** "3 hours ago" / "last week" from an ISO timestamp. */
export function timeAgo(iso: string): string {
  const seconds = (Date.now() - new Date(iso).getTime()) / 1000
  for (const [unit, unitSeconds] of RELATIVE_UNITS) {
    if (Math.abs(seconds) >= unitSeconds) {
      return relativeFormatter.format(-Math.round(seconds / unitSeconds), unit)
    }
  }
  return 'just now'
}

/** 1234 → "1,234". */
export function formatNumber(value: number): string {
  return new Intl.NumberFormat('en').format(Math.round(value))
}

/** Signed delta label: 4 → "+4", -3 → "−3". */
export function formatDelta(value: number): string {
  return value >= 0 ? `+${value}` : `−${Math.abs(value)}`
}
