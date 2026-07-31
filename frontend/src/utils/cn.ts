type ClassValue = string | false | null | undefined

/** Joins conditional Tailwind class names, dropping falsy entries. */
export function cn(...classes: ClassValue[]): string {
  return classes.filter(Boolean).join(' ')
}
