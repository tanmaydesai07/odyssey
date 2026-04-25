import { Moon, Sun, Scale } from 'lucide-react'
import { NavLink, useLocation } from 'react-router-dom'
import { useTheme } from '../ThemeContext'

const TopNav = () => {
  const { theme, toggleTheme } = useTheme()
  const location = useLocation()

  // Hide header on login and dashboard pages
  if (location.pathname === '/login' || location.pathname === '/dashboard') return null

  return (
    <header className="fixed inset-x-0 top-0 z-50 px-4 pt-3 sm:px-6 lg:px-10">
      <nav
        className="mx-auto flex max-w-6xl items-center justify-between rounded-2xl px-5 py-3 sm:px-6 transition-all"
        style={{
          background: theme === 'dark' ? 'rgba(10,10,10,0.85)' : 'rgba(255,255,255,0.85)',
          backdropFilter: 'blur(16px) saturate(180%)',
          border: `1px solid ${theme === 'dark' ? 'rgba(255,255,255,0.08)' : 'rgba(0,0,0,0.08)'}`,
          boxShadow: theme === 'dark' ? '0 4px 24px rgba(0,0,0,0.5)' : '0 4px 24px rgba(0,0,0,0.06)',
        }}
      >
        <NavLink to="/" className="flex items-center gap-2.5">
          <span className="inline-flex h-9 w-9 items-center justify-center rounded-xl text-white shadow-md" style={{ background: '#0a0a0a' }}>
            <Scale size={18} />
          </span>
          <div>
            <p className="font-['Sora'] text-sm font-bold" style={{ color: 'var(--text-primary)' }}>NyayaMitr</p>
            <p className="text-[10px] font-medium" style={{ color: 'var(--text-muted)' }}>AI Legal Assistance</p>
          </div>
        </NavLink>

        <div className="flex items-center gap-3">
          <button type="button" onClick={toggleTheme} aria-label="Toggle theme"
            className="inline-flex items-center justify-center rounded-xl p-2.5 transition-all hover:scale-105"
            style={{ color: 'var(--text-secondary)', background: theme === 'dark' ? 'rgba(255,255,255,0.06)' : 'rgba(0,0,0,0.04)' }}
          >{theme === 'dark' ? <Sun size={16} /> : <Moon size={16} />}</button>
        </div>
      </nav>
    </header>
  )
}

export default TopNav
