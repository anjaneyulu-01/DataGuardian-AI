import type { Severity } from '@/types/domain'

/**
 * The single source of truth for severity presentation.
 *
 * Restrained palette by design: red is reserved for critical, amber for high,
 * blue for medium, emerald for low/healthy. Every badge, dot, chart series,
 * and lineage node reads from here so severities look identical everywhere.
 */
export const SEVERITY: Record<
  Severity,
  { label: string; text: string; bg: string; dot: string; hex: string }
> = {
  critical: {
    label: 'Critical',
    text: 'text-critical',
    bg: 'bg-critical/10 border-critical/25',
    dot: 'bg-critical',
    hex: 'var(--t-red)',
  },
  high: {
    label: 'High',
    text: 'text-warning',
    bg: 'bg-warning/10 border-warning/25',
    dot: 'bg-warning',
    hex: 'var(--t-amber)',
  },
  medium: {
    label: 'Medium',
    text: 'text-brand-strong',
    bg: 'bg-brand/10 border-brand/25',
    dot: 'bg-brand',
    hex: 'var(--t-brand)',
  },
  low: {
    label: 'Low',
    text: 'text-positive',
    bg: 'bg-positive/10 border-positive/25',
    dot: 'bg-positive',
    hex: 'var(--t-emerald)',
  },
}

export const SEVERITY_ORDER: Severity[] = ['critical', 'high', 'medium', 'low']

/** Health % → severity band, so scores and badges never disagree. */
export function severityFromHealth(health: number): Severity {
  if (health < 40) return 'critical'
  if (health < 60) return 'high'
  if (health < 80) return 'medium'
  return 'low'
}
