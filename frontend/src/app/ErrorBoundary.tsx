import { AlertTriangle, RotateCw } from 'lucide-react'
import { Component, type ErrorInfo, type ReactNode } from 'react'

interface Props {
  children: ReactNode
  /** Shown instead of the default panel. */
  fallback?: ReactNode
}

interface State {
  error: Error | null
}

/**
 * Catches render-time crashes so one broken panel cannot blank the workspace.
 *
 * Deliberately a class component: React has no hook equivalent for
 * `componentDidCatch`. Data-fetching failures do NOT reach here — services
 * fall back to demo data and React Query surfaces errors as state — so
 * anything caught here is a genuine rendering bug worth showing loudly.
 */
export class ErrorBoundary extends Component<Props, State> {
  state: State = { error: null }

  static getDerivedStateFromError(error: Error): State {
    return { error }
  }

  componentDidCatch(error: Error, info: ErrorInfo): void {
    console.error('Render error caught by boundary:', error, info.componentStack)
  }

  private reset = (): void => {
    this.setState({ error: null })
  }

  render(): ReactNode {
    const { error } = this.state
    if (!error) return this.props.children
    if (this.props.fallback) return this.props.fallback

    return (
      <div
        role="alert"
        className="card mx-auto mt-10 max-w-lg p-6 text-center"
      >
        <span className="border-critical/25 bg-critical/10 text-critical mx-auto grid size-11 place-items-center rounded-xl border">
          <AlertTriangle className="size-5" />
        </span>
        <h2 className="text-ink mt-4 text-sm font-semibold">
          This panel failed to render
        </h2>
        <p className="text-muted mt-1.5 text-[13px] leading-relaxed">
          The rest of the workspace is unaffected. The error has been logged to
          the browser console.
        </p>
        <pre className="border-line bg-raised text-faint mt-3 overflow-x-auto rounded-lg border p-2.5 text-left text-[11px]">
          {error.message}
        </pre>
        <button
          type="button"
          onClick={this.reset}
          className="bg-brand hover:bg-brand-strong shadow-glow mt-4 inline-flex items-center gap-1.5 rounded-lg px-4 py-2 text-[13px] font-medium text-white transition-colors"
        >
          <RotateCw className="size-3.5" /> Try again
        </button>
      </div>
    )
  }
}
