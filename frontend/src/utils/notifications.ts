import type { Finding } from '@/types/domain'

/**
 * Unread count for the notification bell.
 *
 * Counts only critical and high findings: a badge that lights up for every
 * low-severity nudge stops meaning anything, and the point of the badge is
 * "something needs you now".
 *
 * Lives here rather than in `NotificationsPanel.tsx` so that file exports
 * only a component and keeps React Fast Refresh working.
 */
export function notificationCount(findings: Finding[]): number {
  return findings.filter((f) => f.severity === 'critical' || f.severity === 'high').length
}
