import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './theme-tokens.css'
import './index.css'
import './App.css'
import './styles/primitives.css'
import './styles/today.css'
import './styles/approval.css'
import './styles/projects.css'
import './styles/ask.css'
import './styles/settings.css'
import './styles/reader.css'
import './styles/wizard.css'
import './styles/markdown.css'
import './styles/controls.css'
import App from './App.tsx'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
