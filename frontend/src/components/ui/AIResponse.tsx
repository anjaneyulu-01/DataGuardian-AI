import { motion } from 'framer-motion'
import {
  Brain,
  ClipboardList,
  Lightbulb,
  ShieldAlert,
  Sparkles,
} from 'lucide-react'

import { RiskBadge } from './RiskBadge'
import type { AIAnswer } from '@/types/domain'
import { cn } from '@/utils'
import { SEVERITY } from '@/utils/severity'

interface AIResponseProps {
  answer: AIAnswer
  onAction?: (action: string) => void
  /**
   * Rendered inside the card, below the sections. Used for the agent's
   * execution trace, which belongs to the same visual unit as the answer it
   * describes rather than floating beneath it.
   */
  footer?: React.ReactNode
}

const sectionVariants = {
  hidden: { opacity: 0, y: 8 },
  visible: (index: number) => ({
    opacity: 1,
    y: 0,
    transition: { delay: 0.12 * index, duration: 0.35, ease: 'easeOut' as const },
  }),
}

/**
 * A structured investigation result: reasoning → risk → evidence →
 * recommendation → actions. Sections stagger in to read like the agent is
 * reporting, not like a page loaded.
 */
export function AIResponse({ answer, onAction, footer }: AIResponseProps) {
  return (
    <div className="card overflow-hidden">
      {/* Question echo. */}
      <div className="border-line bg-raised/50 flex items-center gap-2.5 border-b px-5 py-3.5">
        <Sparkles className="text-brand-strong size-4" />
        <p className="text-ink text-sm font-medium">{answer.question}</p>
      </div>

      <div className="space-y-5 p-5">
        {/* Reasoning. */}
        <motion.section custom={0} initial="hidden" animate="visible" variants={sectionVariants}>
          <SectionLabel icon={<Brain className="size-3.5" />} text="Reasoning" />
          <ol className="mt-2 space-y-1.5">
            {answer.reasoning.map((step, index) => (
              <li key={step} className="text-ink-secondary flex gap-2.5 text-[13px] leading-relaxed">
                <span className="text-faint font-mono text-[11px] leading-5 tabular-nums">
                  {String(index + 1).padStart(2, '0')}
                </span>
                {step}
              </li>
            ))}
          </ol>
        </motion.section>

        {/* Risk. */}
        <motion.section custom={1} initial="hidden" animate="visible" variants={sectionVariants}>
          <SectionLabel icon={<ShieldAlert className="size-3.5" />} text="Risk" />
          <div
            className={cn(
              'mt-2 flex items-start gap-3 rounded-xl border p-3.5',
              SEVERITY[answer.risk.level].bg,
            )}
          >
            <RiskBadge severity={answer.risk.level} />
            <p className="text-ink-secondary text-[13px] leading-relaxed">
              {answer.risk.statement}
            </p>
          </div>
        </motion.section>

        {/* Evidence. */}
        <motion.section custom={2} initial="hidden" animate="visible" variants={sectionVariants}>
          <SectionLabel icon={<ClipboardList className="size-3.5" />} text="Evidence" />
          <div className="border-line mt-2 overflow-hidden rounded-xl border">
            {answer.evidence.map((item, index) => (
              <div
                key={item.label}
                className={cn(
                  'flex items-center justify-between gap-4 px-3.5 py-2.5',
                  index % 2 === 1 && 'bg-raised/50',
                )}
              >
                <span className="text-ink text-[13px] font-medium">{item.label}</span>
                <span className="flex items-center gap-2.5">
                  <span className="text-muted text-[12.5px]">{item.value}</span>
                  {item.severity ? <RiskBadge severity={item.severity} size="sm" /> : null}
                </span>
              </div>
            ))}
          </div>
        </motion.section>

        {/* Recommendation + actions. */}
        <motion.section custom={3} initial="hidden" animate="visible" variants={sectionVariants}>
          <SectionLabel icon={<Lightbulb className="size-3.5" />} text="Recommendation" />
          <p className="text-ink-secondary mt-2 text-[13px] leading-relaxed">
            {answer.recommendation}
          </p>
          <div className="mt-3.5 flex flex-wrap gap-2">
            {answer.actions.map((action, index) => (
              <button
                key={action}
                type="button"
                onClick={() => onAction?.(action)}
                className={cn(
                  'rounded-lg px-3.5 py-2 text-[12.5px] font-medium transition-all',
                  index === 0
                    ? 'bg-brand hover:bg-brand-strong text-white shadow-glow'
                    : 'border-line bg-raised text-ink-secondary hover:border-brand/40 hover:text-ink border',
                )}
              >
                {action}
              </button>
            ))}
          </div>
        </motion.section>
      </div>

      {footer}
    </div>
  )
}

function SectionLabel({ icon, text }: { icon: React.ReactNode; text: string }) {
  return (
    <p className="text-faint flex items-center gap-1.5 text-[11px] font-semibold tracking-widest uppercase">
      {icon}
      {text}
    </p>
  )
}
