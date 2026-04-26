import { useState, useEffect } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { Scale, Mail, Lock, User, ArrowRight, Eye, EyeOff } from 'lucide-react'
import { useTheme } from '../ThemeContext'

const LoginPage = () => {
  const [tab, setTab] = useState('login')
  const [showPw, setShowPw] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  // Form fields
  const [name, setName] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')

  const { theme } = useTheme()
  const navigate = useNavigate()
  const isDark = theme === 'dark'

  // Redirect if already logged in
  useEffect(() => {
    const token = localStorage.getItem('token')
    if (token) {
      navigate('/notebooks', { replace: true })
    }
  }, [navigate])

  const resetForm = () => {
    setName('')
    setEmail('')
    setPassword('')
    setConfirmPassword('')
    setError('')
  }

  const handleTabSwitch = (t) => {
    setTab(t)
    resetForm()
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')

    // Client-side validation
    if (tab === 'register') {
      if (!name.trim()) return setError('Full name is required')
      if (password !== confirmPassword) return setError('Passwords do not match')
      if (password.length < 6) return setError('Password must be at least 6 characters')
    }

    const endpoint = tab === 'login' ? '/api/auth/login' : '/api/auth/signup'
    const body =
      tab === 'login'
        ? { email, password }
        : { name, email, password, confirmPassword }

    try {
      setLoading(true)
      const res = await fetch(endpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      })

      const data = await res.json()

      if (!res.ok) {
        setError(data.message || 'Something went wrong')
        return
      }

      // Persist token and user info
      localStorage.setItem('token', data.token)
      localStorage.setItem('user', JSON.stringify(data.user))

      navigate('/notebooks')
    } catch {
      setError('Unable to reach the server. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  const inputStyle = {
    background: isDark ? 'rgba(255,255,255,0.05)' : 'rgba(0,0,0,0.03)',
    border: `1px solid ${isDark ? 'rgba(255,255,255,0.08)' : 'rgba(0,0,0,0.06)'}`,
    color: 'var(--text-primary)',
  }

  return (
    <div className="min-h-[calc(100vh-5rem)] flex items-center justify-center px-4 relative overflow-hidden">
      {/* Background glows */}
      <div className="absolute top-1/4 left-1/3 w-[500px] h-[500px] rounded-full blur-[160px] opacity-[0.06] pointer-events-none" style={{ background: '#c9a84c' }} />
      <div className="absolute bottom-1/4 right-1/4 w-[400px] h-[400px] rounded-full blur-[120px] opacity-[0.04] pointer-events-none" style={{ background: isDark ? '#fff' : '#000' }} />

      <div className="w-full max-w-md animate-in delay-1">
        {/* Logo */}
        <div className="text-center mb-8">
          <Link to="/" className="inline-flex items-center gap-2.5 mb-4">
            <span className="inline-flex h-11 w-11 items-center justify-center rounded-2xl text-white shadow-lg" style={{ background: '#0a0a0a' }}>
              <Scale size={20} />
            </span>
            <span className="font-['Sora'] text-xl font-bold" style={{ color: 'var(--text-primary)' }}>NyayaMitr</span>
          </Link>
          <p className="text-sm mt-1" style={{ color: 'var(--text-muted)' }}>AI-Powered Legal Assistance for Every Indian</p>
        </div>

        {/* Card */}
        <div className="rounded-3xl p-8 shadow-2xl" style={{
          background: isDark ? 'rgba(20,20,20,0.7)' : 'rgba(255,255,255,0.8)',
          backdropFilter: 'blur(24px)',
          border: `1px solid ${isDark ? 'rgba(255,255,255,0.08)' : 'rgba(0,0,0,0.06)'}`,
        }}>
          {/* Tabs */}
          <div className="flex rounded-xl p-1 mb-8" style={{ background: isDark ? 'rgba(255,255,255,0.05)' : 'rgba(0,0,0,0.04)' }}>
            {['login', 'register'].map((t) => (
              <button key={t} onClick={() => handleTabSwitch(t)}
                className="flex-1 py-2.5 text-sm font-bold rounded-lg transition-all capitalize"
                style={{
                  background: tab === t ? (isDark ? '#fff' : '#0a0a0a') : 'transparent',
                  color: tab === t ? (isDark ? '#0a0a0a' : '#fff') : 'var(--text-muted)',
                  boxShadow: tab === t ? '0 2px 10px rgba(0,0,0,0.15)' : 'none',
                }}>{t === 'login' ? 'Sign In' : 'Create Account'}</button>
            ))}
          </div>

          {/* Error message */}
          {error && (
            <div className="mb-4 px-4 py-3 rounded-xl text-sm font-medium" style={{
              background: 'rgba(220,38,38,0.1)',
              border: '1px solid rgba(220,38,38,0.25)',
              color: '#ef4444',
            }}>
              {error}
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            {tab === 'register' && (
              <div className="relative">
                <User size={16} className="absolute left-4 top-1/2 -translate-y-1/2" style={{ color: 'var(--text-muted)' }} />
                <input
                  type="text"
                  placeholder="Full Name"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  required
                  className="w-full pl-11 pr-4 py-3.5 rounded-xl text-sm font-medium outline-none transition-all"
                  style={inputStyle}
                />
              </div>
            )}

            <div className="relative">
              <Mail size={16} className="absolute left-4 top-1/2 -translate-y-1/2" style={{ color: 'var(--text-muted)' }} />
              <input
                type="email"
                placeholder="Email address"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                className="w-full pl-11 pr-4 py-3.5 rounded-xl text-sm font-medium outline-none transition-all"
                style={inputStyle}
              />
            </div>

            <div className="relative">
              <Lock size={16} className="absolute left-4 top-1/2 -translate-y-1/2" style={{ color: 'var(--text-muted)' }} />
              <input
                type={showPw ? 'text' : 'password'}
                placeholder="Password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                className="w-full pl-11 pr-11 py-3.5 rounded-xl text-sm font-medium outline-none transition-all"
                style={inputStyle}
              />
              <button type="button" onClick={() => setShowPw(!showPw)} className="absolute right-4 top-1/2 -translate-y-1/2" style={{ color: 'var(--text-muted)' }}>
                {showPw ? <EyeOff size={16} /> : <Eye size={16} />}
              </button>
            </div>

            {tab === 'register' && (
              <div className="relative">
                <Lock size={16} className="absolute left-4 top-1/2 -translate-y-1/2" style={{ color: 'var(--text-muted)' }} />
                <input
                  type="password"
                  placeholder="Confirm Password"
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  required
                  className="w-full pl-11 pr-4 py-3.5 rounded-xl text-sm font-medium outline-none transition-all"
                  style={inputStyle}
                />
              </div>
            )}

            {tab === 'login' && (
              <div className="flex justify-end">
                <button type="button" className="text-xs font-semibold" style={{ color: '#c9a84c' }}>Forgot password?</button>
              </div>
            )}

            <button
              type="submit"
              disabled={loading}
              className="w-full flex items-center justify-center gap-2 py-3.5 rounded-xl text-sm font-bold transition-all hover:-translate-y-0.5 disabled:opacity-60 disabled:cursor-not-allowed"
              style={{ background: '#0a0a0a', color: '#fff', boxShadow: '0 4px 20px rgba(0,0,0,0.2)' }}
            >
              {loading ? 'Please wait…' : (tab === 'login' ? 'Sign In' : 'Create Account')}
              {!loading && <ArrowRight size={16} />}
            </button>
          </form>

          <div className="mt-6 flex items-center gap-3">
            <div className="flex-1 h-px" style={{ background: 'var(--border)' }} />
            <span className="text-[11px] font-bold uppercase tracking-wider" style={{ color: 'var(--text-muted)' }}>or</span>
            <div className="flex-1 h-px" style={{ background: 'var(--border)' }} />
          </div>

          <button
            className="mt-4 w-full flex items-center justify-center gap-3 py-3 rounded-xl text-sm font-semibold transition-all hover:scale-[1.01]"
            style={{
              background: isDark ? 'rgba(255,255,255,0.05)' : 'rgba(0,0,0,0.03)',
              border: `1px solid ${isDark ? 'rgba(255,255,255,0.08)' : 'rgba(0,0,0,0.06)'}`,
              color: 'var(--text-primary)',
            }}
          >
            <svg width="18" height="18" viewBox="0 0 48 48">
              <path fill="#4285F4" d="M24 9.5c3.54 0 6.71 1.22 9.21 3.6l6.85-6.85C35.9 2.38 30.47 0 24 0 14.62 0 6.51 5.38 2.56 13.22l7.98 6.19C12.43 13.72 17.74 9.5 24 9.5z"/>
              <path fill="#34A853" d="M46.98 24.55c0-1.57-.15-3.09-.38-4.55H24v9.02h12.94c-.58 2.96-2.26 5.48-4.78 7.18l7.73 6c4.51-4.18 7.09-10.36 7.09-17.65z"/>
              <path fill="#FBBC05" d="M10.53 28.59c-.48-1.45-.76-2.99-.76-4.59s.27-3.14.76-4.59l-7.98-6.19C.92 16.46 0 20.12 0 24c0 3.88.92 7.54 2.56 10.78l7.97-6.19z"/>
              <path fill="#EA4335" d="M24 48c6.48 0 11.93-2.13 15.89-5.81l-7.73-6c-2.15 1.45-4.92 2.3-8.16 2.3-6.26 0-11.57-4.22-13.47-9.91l-7.98 6.19C6.51 42.62 14.62 48 24 48z"/>
            </svg>
            Continue with Google
          </button>
        </div>

        <p className="text-center text-xs mt-6" style={{ color: 'var(--text-muted)' }}>
          By continuing, you agree to our Terms of Service and Privacy Policy
        </p>
      </div>
    </div>
  )
}

export default LoginPage
