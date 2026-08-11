import { ClerkProvider } from '@clerk/clerk-react'
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.tsx'

const PUBLISHABLE_KEY = import.meta.env.VITE_CLERK_PUBLISHABLE_KEY as string | undefined

const root = createRoot(document.getElementById('root')!)

if (!PUBLISHABLE_KEY) {
  root.render(
    <StrictMode>
      <main style={{ fontFamily: 'sans-serif', padding: '2rem' }}>
        <h1>Configuração pendente</h1>
        <p>
          Defina <code>VITE_CLERK_PUBLISHABLE_KEY</code> em <code>frontend/.env</code> (crie um
          app em <a href="https://dashboard.clerk.com">dashboard.clerk.com</a>) para carregar a
          aplicação.
        </p>
      </main>
    </StrictMode>,
  )
} else {
  root.render(
    <StrictMode>
      <ClerkProvider publishableKey={PUBLISHABLE_KEY} afterSignOutUrl="/">
        <App />
      </ClerkProvider>
    </StrictMode>,
  )
}
