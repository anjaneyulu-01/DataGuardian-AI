import { Link } from 'react-router'

/** Catch-all route for unknown paths. */
export function NotFoundPage() {
  return (
    <div className="space-y-3">
      <h1 className="text-ink text-2xl font-semibold">Page not found</h1>
      <p className="text-muted text-sm">That route does not exist.</p>
      <Link to="/" className="text-brand text-sm underline underline-offset-4">
        Back to dashboard
      </Link>
    </div>
  )
}
