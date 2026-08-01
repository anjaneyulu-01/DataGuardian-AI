import { motion, type HTMLMotionProps } from 'framer-motion'
import type { ReactNode } from 'react'

import { cn } from '@/utils'

interface CardProps extends HTMLMotionProps<'div'> {
  children: ReactNode
  /** Lifts on hover — for cards that navigate or act. */
  interactive?: boolean
  className?: string
}

/**
 * Base surface every panel is built on. Handles the entrance animation and
 * (optionally) the hover lift, so pages never repeat motion boilerplate.
 */
export function Card({ children, interactive, className, ...rest }: CardProps) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.35, ease: 'easeOut' }}
      whileHover={
        interactive
          ? { y: -3, transition: { duration: 0.18, ease: 'easeOut' } }
          : undefined
      }
      className={cn(
        'card',
        interactive && 'cursor-pointer transition-shadow hover:shadow-pop',
        className,
      )}
      {...rest}
    >
      {children}
    </motion.div>
  )
}
