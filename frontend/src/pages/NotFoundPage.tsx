import { Compass } from 'lucide-react'
import { Link } from 'react-router'

import { EmptyState } from '@/components/ui'

/** Catch-all route. */
export function NotFoundPage() {
  return (
    <div className="grid min-h-[60vh] place-items-center">
      <EmptyState
        icon={Compass}
        title="Page not found"
        description="That route does not exist in this workspace."
        action={
          <Link
            to="/"
            className="bg-brand hover:bg-brand-strong shadow-glow rounded-lg px-4 py-2 text-[13px] font-medium text-white transition-colors"
          >
            Back to Overview
          </Link>
        }
      />
    </div>
  )
}
