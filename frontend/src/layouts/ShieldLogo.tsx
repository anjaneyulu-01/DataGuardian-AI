/** Brand mark: a shield over a data node, drawn inline so it themes freely. */
export function ShieldLogo({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 32 32" fill="none" className={className} aria-hidden>
      <defs>
        <linearGradient id="dg-shield" x1="6" y1="4" x2="26" y2="28" gradientUnits="userSpaceOnUse">
          <stop stopColor="var(--t-brand)" />
          <stop offset="1" stopColor="var(--t-cyan)" />
        </linearGradient>
      </defs>
      <path
        d="M16 3.5 26 7.4v7.1c0 6.6-4.3 11.6-10 14-5.7-2.4-10-7.4-10-14V7.4L16 3.5Z"
        fill="url(#dg-shield)"
        fillOpacity="0.16"
        stroke="url(#dg-shield)"
        strokeWidth="1.6"
        strokeLinejoin="round"
      />
      <circle cx="16" cy="14.5" r="2.4" fill="var(--t-cyan)" />
      <path
        d="M16 17v4.2M12.2 12.2l1.9 1.2M19.8 12.2l-1.9 1.2"
        stroke="var(--t-cyan)"
        strokeWidth="1.4"
        strokeLinecap="round"
      />
    </svg>
  )
}
