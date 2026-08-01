import { motion } from 'framer-motion'

import { useCountUp } from '@/hooks/useCountUp'
import { SEVERITY, severityFromHealth } from '@/utils/severity'

interface HealthScoreProps {
  /** 0–100. */
  score: number
  size?: number
  label?: string
}

/**
 * Animated circular governance score. The ring color follows the same
 * severity bands as every badge, so an 86 ring is emerald everywhere an
 * 86 badge would be.
 */
export function HealthScore({ score, size = 168, label = 'Governance Health' }: HealthScoreProps) {
  const animated = useCountUp(score, 1200)
  const severity = severityFromHealth(score)
  const color = SEVERITY[severity].hex

  const stroke = 11
  const radius = (size - stroke) / 2
  const circumference = 2 * Math.PI * radius

  return (
    <div className="flex flex-col items-center gap-3">
      <div className="relative" style={{ width: size, height: size }}>
        <svg width={size} height={size} className="-rotate-90">
          <circle
            cx={size / 2}
            cy={size / 2}
            r={radius}
            fill="none"
            stroke="var(--t-line)"
            strokeWidth={stroke}
          />
          <motion.circle
            cx={size / 2}
            cy={size / 2}
            r={radius}
            fill="none"
            stroke={color}
            strokeWidth={stroke}
            strokeLinecap="round"
            strokeDasharray={circumference}
            initial={{ strokeDashoffset: circumference }}
            animate={{ strokeDashoffset: circumference * (1 - score / 100) }}
            transition={{ duration: 1.2, ease: [0.22, 1, 0.36, 1] }}
            style={{ filter: `drop-shadow(0 0 10px ${color})`, opacity: 0.95 }}
          />
        </svg>
        <div className="absolute inset-0 grid place-items-center">
          <div className="text-center">
            <p className="text-ink text-4xl font-semibold tracking-tight tabular-nums">
              {Math.round(animated)}
            </p>
            <p className="text-faint text-[11px] font-medium tracking-widest uppercase">
              / 100
            </p>
          </div>
        </div>
      </div>
      <p className="text-muted text-[13px] font-medium">{label}</p>
    </div>
  )
}
