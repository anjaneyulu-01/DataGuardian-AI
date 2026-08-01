import { useEffect, useRef, useState } from 'react'

/**
 * Animate a number from 0 to `target` with ease-out cubic.
 *
 * Drives the metric cards and the health score so values feel measured rather
 * than pasted. Respects `prefers-reduced-motion` by jumping straight to the
 * target.
 */
export function useCountUp(target: number, durationMs = 900): number {
  const [value, setValue] = useState(0)
  const frame = useRef<number>(0)

  useEffect(() => {
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
      setValue(target)
      return
    }

    const start = performance.now()

    const tick = (now: number) => {
      const progress = Math.min(1, (now - start) / durationMs)
      const eased = 1 - Math.pow(1 - progress, 3)
      setValue(target * eased)
      if (progress < 1) frame.current = requestAnimationFrame(tick)
    }

    frame.current = requestAnimationFrame(tick)
    return () => cancelAnimationFrame(frame.current)
  }, [target, durationMs])

  return value
}
