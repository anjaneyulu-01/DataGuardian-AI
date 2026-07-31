interface PageHeaderProps {
  title: string
  description?: string
}

/** Consistent title block for every routed page. */
export function PageHeader({ title, description }: PageHeaderProps) {
  return (
    <header className="border-line border-b pb-4">
      <h1 className="text-ink text-2xl font-semibold tracking-tight">{title}</h1>
      {description ? <p className="text-muted mt-1 text-sm">{description}</p> : null}
    </header>
  )
}
