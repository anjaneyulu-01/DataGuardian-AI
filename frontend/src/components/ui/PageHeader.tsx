import { motion } from 'framer-motion'
import type { ReactNode } from 'react'

interface PageHeaderProps {
  title: string
  description?: string
  /** Right-aligned slot for page-level actions. */
  action?: ReactNode
}

/** Title block at the top of every routed page. */
export function PageHeader({ title, description, action }: PageHeaderProps) {
  return (
    <motion.header
      initial={{ opacity: 0, y: 6 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3, ease: 'easeOut' }}
      className="mb-6 flex flex-wrap items-end justify-between gap-4"
    >
      <div>
        <h1 className="text-ink text-xl font-semibold tracking-tight">{title}</h1>
        {description ? (
          <p className="text-muted mt-1 max-w-2xl text-sm">{description}</p>
        ) : null}
      </div>
      {action ? <div className="shrink-0">{action}</div> : null}
    </motion.header>
  )
}
