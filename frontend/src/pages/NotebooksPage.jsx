import { useState, useEffect } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { useTheme } from '../ThemeContext'
import { Scale, Plus, MoreVertical, Trash2, LogOut, Moon, Sun, User, FileText, MessageSquare, Gavel, Shield, BookOpen } from 'lucide-react'

const iconMap = {
  shopping: MessageSquare,
  file: FileText,
  home: BookOpen,
  shield: Shield,
  gavel: Gavel,
}

const caseTypeToIcon = {
  'consumer': 'shopping',
  'rti': 'file',
  'rental': 'home',
  'workplace': 'shield',
  'property': 'gavel',
}

const caseTypeToColor = {
  'consumer': '#ef4444',
  'rti': '#3b82f6',
  'rental': '#8b5cf6',
  'workplace': '#10b981',
  'property': '#f59e0b',
}

const NotebooksPage = () => {
  const { theme, toggleTheme } = useTheme()
  const navigate = useNavigate()
  const isDark = theme === 'dark'
  const [notebooks, setNotebooks] = useState([])
  const [menuOpen, setMenuOpen] = useState(null)
  const [loading, setLoading] = useState(true)

  // Fetch cases on mount
  useEffect(() => {
    const fetchCases = async () => {
      try {
        const token = localStorage.getItem('token')
        const res = await fetch('/api/cases', {
          headers: {
            'Authorization': `Bearer ${token}`,
          },
        })

        if (!res.ok) {
          throw new Error('Failed to fetch cases')
        }

        const data = await res.json()
        
        // Transform cases to notebook format
        const transformed = data.cases.map(c => {
          const icon = caseTypeToIcon[c.caseType] || 'shopping'
          const color = caseTypeToColor[c.caseType] || '#ef4444'
          const date = new Date(c.lastMessageAt).toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: 'numeric' })
          
          return {
            id: c._id,
            title: c.title,
            icon,
            color,
            date,
            sources: c.documents.length,
          }
        })

        setNotebooks(transformed)
      } catch (err) {
        console.error('Failed to fetch cases:', err)
      } finally {
        setLoading(false)
      }
    }

    fetchCases()
  }, [])

  const handleSignOut = () => {
    localStorage.removeItem('token')
    localStorage.removeItem('user')
    navigate('/login')
  }

  const handleDelete = async (id, e) => {
    e.stopPropagation()
    try {
      const token = localStorage.getItem('token')
      const res = await fetch(`/api/cases/${id}`, {
        method: 'DELETE',
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      })

      if (res.ok) {
        setNotebooks(notebooks.filter(n => n.id !== id))
      }
    } catch (err) {
      console.error('Failed to delete case:', err)
    }
    setMenuOpen(null)
  }

  const handleNotebookClick = (id) => {
    navigate(`/dashboard/${id}`)
  }

  const handleCreateNew = async () => {
    try {
      const token = localStorage.getItem('token')
      const res = await fetch('/api/cases/new', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
      })

      if (!res.ok) {
        throw new Error('Failed to create case')
      }

      const data = await res.json()
      navigate(`/dashboard/${data.case._id}`)
    } catch (err) {
      console.error('Failed to create case:', err)
    }
  }

  return (
    <div className="min-h-screen" style={{ background: isDark ? '#0a0a0a' : '#fafafa', color: 'var(--text-primary)' }}>
      {/* Top bar */}
      <div className="flex items-center justify-between px-6 py-4" style={{ borderBottom: `1px solid ${isDark ? 'rgba(255,255,255,0.06)' : 'rgba(0,0,0,0.06)'}` }}>
        <Link to="/" className="flex items-center gap-2.5">
          <span className="inline-flex h-9 w-9 items-center justify-center rounded-xl text-white shadow" style={{ background: '#0a0a0a' }}>
            <Scale size={16} />
          </span>
          <span className="font-['Sora'] text-lg font-bold" style={{ color: 'var(--text-primary)' }}>NyayaMitr</span>
        </Link>

        <div className="flex items-center gap-3">
          <button onClick={toggleTheme} className="w-9 h-9 rounded-lg flex items-center justify-center hover:bg-white/5" style={{ color: 'var(--text-muted)' }}>
            {isDark ? <Sun size={16} /> : <Moon size={16} />}
          </button>
          <button onClick={handleSignOut} className="w-9 h-9 rounded-lg flex items-center justify-center hover:bg-white/5" style={{ color: 'var(--text-muted)' }}>
            <LogOut size={16} />
          </button>
          <div className="w-9 h-9 rounded-full flex items-center justify-center" style={{ background: isDark ? 'rgba(255,255,255,0.06)' : 'rgba(0,0,0,0.04)' }}>
            <User size={14} style={{ color: 'var(--text-muted)' }} />
          </div>
        </div>
      </div>

      {/* Main content */}
      <div className="max-w-6xl mx-auto px-6 py-8">
        <div className="flex items-center justify-between mb-6">
          <h1 className="text-2xl font-bold" style={{ color: 'var(--text-primary)' }}>Recent cases</h1>
          <button className="text-sm font-semibold flex items-center gap-1" style={{ color: '#c9a84c' }}>
            See all <span>→</span>
          </button>
        </div>

        {/* Grid */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
          {/* Create new card */}
          <button
            onClick={handleCreateNew}
            className="group relative rounded-2xl p-6 flex flex-col items-center justify-center gap-3 transition-all hover:scale-[1.02] hover:shadow-lg"
            style={{
              background: isDark ? 'rgba(255,255,255,0.03)' : 'rgba(255,255,255,0.8)',
              border: `1px solid ${isDark ? 'rgba(255,255,255,0.08)' : 'rgba(0,0,0,0.06)'}`,
              minHeight: '180px',
            }}
          >
            <div className="w-14 h-14 rounded-full flex items-center justify-center transition-all group-hover:scale-110" style={{ background: isDark ? 'rgba(255,255,255,0.05)' : 'rgba(0,0,0,0.04)' }}>
              <Plus size={24} style={{ color: 'var(--text-muted)' }} />
            </div>
            <span className="text-sm font-semibold" style={{ color: 'var(--text-secondary)' }}>Create new case</span>
          </button>

          {/* Loading state */}
          {loading && (
            <div className="col-span-full flex items-center justify-center py-12">
              <div className="flex items-center gap-2">
                <div className="w-2 h-2 rounded-full bg-[#c9a84c] animate-bounce" style={{ animationDelay: '0ms' }} />
                <div className="w-2 h-2 rounded-full bg-[#c9a84c] animate-bounce" style={{ animationDelay: '150ms' }} />
                <div className="w-2 h-2 rounded-full bg-[#c9a84c] animate-bounce" style={{ animationDelay: '300ms' }} />
              </div>
            </div>
          )}

          {/* Empty state */}
          {!loading && notebooks.length === 0 && (
            <div className="col-span-full flex flex-col items-center justify-center py-12">
              <MessageSquare size={32} style={{ color: 'var(--text-muted)', opacity: 0.4 }} />
              <p className="text-sm mt-3" style={{ color: 'var(--text-muted)' }}>No cases yet. Create your first case!</p>
            </div>
          )}

          {/* Notebook cards */}
          {!loading && notebooks.map((nb) => {
            const IconComponent = iconMap[nb.icon] || MessageSquare
            return (
              <div
                key={nb.id}
                onClick={() => handleNotebookClick(nb.id)}
                className="group relative rounded-2xl p-6 cursor-pointer transition-all hover:scale-[1.02] hover:shadow-lg"
                style={{
                  background: isDark ? 'rgba(255,255,255,0.03)' : 'rgba(255,255,255,0.8)',
                  border: `1px solid ${isDark ? 'rgba(255,255,255,0.08)' : 'rgba(0,0,0,0.06)'}`,
                  minHeight: '180px',
                }}
              >
                {/* Menu button */}
                <button
                  onClick={(e) => { e.stopPropagation(); setMenuOpen(menuOpen === nb.id ? null : nb.id) }}
                  className="absolute top-3 right-3 w-7 h-7 rounded-lg flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity hover:bg-white/5"
                  style={{ color: 'var(--text-muted)' }}
                >
                  <MoreVertical size={14} />
                </button>

                {/* Delete menu */}
                {menuOpen === nb.id && (
                  <div className="absolute top-11 right-3 rounded-lg shadow-xl z-10 overflow-hidden" style={{ background: isDark ? '#1a1a1a' : '#fff', border: `1px solid ${isDark ? 'rgba(255,255,255,0.08)' : 'rgba(0,0,0,0.06)'}` }}>
                    <button
                      onClick={(e) => handleDelete(nb.id, e)}
                      className="flex items-center gap-2 px-3 py-2 text-xs font-semibold hover:bg-red-500/10 w-full text-left"
                      style={{ color: '#ef4444' }}
                    >
                      <Trash2 size={12} />
                      Delete
                    </button>
                  </div>
                )}

                {/* Icon */}
                <div className="w-12 h-12 rounded-xl flex items-center justify-center mb-4" style={{ background: `${nb.color}15` }}>
                  <IconComponent size={20} style={{ color: nb.color }} />
                </div>

                {/* Title */}
                <h3 className="text-sm font-semibold mb-2 line-clamp-2" style={{ color: 'var(--text-primary)' }}>
                  {nb.title}
                </h3>

                {/* Meta */}
                <div className="flex items-center gap-2 text-xs" style={{ color: 'var(--text-muted)' }}>
                  <span>{nb.date}</span>
                  <span>•</span>
                  <span>{nb.sources} source{nb.sources > 1 ? 's' : ''}</span>
                </div>
              </div>
            )
          })}
        </div>
      </div>
    </div>
  )
}

export default NotebooksPage
