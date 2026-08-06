// Only OverviewPage is exported here, and only because App.tsx imports it
// eagerly: it is the first paint, so lazy-loading it would add a round-trip
// to the very first thing a user sees.
//
// Every other page MUST stay out of this barrel. App.tsx lazy-loads them, and
// a static re-export here silently defeats that — Rolldown reports
// INEFFECTIVE_DYNAMIC_IMPORT and folds the page back into the main chunk.
export { OverviewPage } from './OverviewPage'
