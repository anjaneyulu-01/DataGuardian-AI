import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter } from 'react-router'

import App from './App.tsx'
import { DemoModeProvider } from './app/DemoModeProvider'
import { ErrorBoundary } from './app/ErrorBoundary'
import { QueryProvider } from './app/QueryProvider'
import './index.css'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    {/* Outermost boundary: catches anything the per-page boundaries miss. */}
    <ErrorBoundary>
      {/* QueryProvider wraps DemoModeProvider because toggling Demo Mode
          invalidates the query cache, so it needs the client in scope. */}
      <QueryProvider>
        <DemoModeProvider>
          <BrowserRouter>
            <App />
          </BrowserRouter>
        </DemoModeProvider>
      </QueryProvider>
    </ErrorBoundary>
  </StrictMode>,
)
