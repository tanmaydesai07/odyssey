import { useState, useRef, useCallback, useEffect } from 'react'
import { useTheme } from '../ThemeContext'
import { useLegal } from '../componts/LegalDataContext'
import VoiceRipple from '../componts/VoiceRipple'
import { Scale, MessageSquare, FileText, Search, FolderOpen, Mic, MicOff, Plus, ArrowUp, Sparkles, User, Menu, X, LogOut, Moon, Sun, Trash2, TrendingUp, Shield, Gavel, BookOpen, PanelRightOpen, SquarePen, Upload, Image, File, Clock } from 'lucide-react'
import { Link, useNavigate } from 'react-router-dom'

const tools = [
  { id: 'consult', icon: MessageSquare, label: 'AI Consult', desc: 'Legal guidance' },
  { id: 'draft', icon: FileText, label: 'Auto-Draft', desc: 'Generate PDFs' },
  { id: 'research', icon: Search, label: 'Legal Research', desc: 'Find laws' },
  { id: 'contract', icon: BookOpen, label: 'Contract Review', desc: 'Spot red flags' },
  { id: 'strength', icon: TrendingUp, label: 'Case Strength', desc: 'Analyze case' },
  { id: 'evidence', icon: FolderOpen, label: 'Evidence Hub', desc: 'Organize proof' },
  { id: 'rights', icon: Shield, label: 'Know Rights', desc: 'Rights & duties' },
  { id: 'escalation', icon: Gavel, label: 'Escalation', desc: 'Next steps' },
  { id: 'voice', icon: Mic, label: 'Voice Agent', desc: 'Speak naturally' },
]

const pills = ['How do I file an FIR?', 'Review my rental agreement', 'File a consumer complaint', 'My rights at workplace']

const DashboardPage = () => {
  const { theme, toggleTheme } = useTheme()
  const { chatMessages, isTyping, sendMessage } = useLegal()
  const isDark = theme === 'dark'
  const b = isDark ? 'rgba(255,255,255,0.06)' : 'rgba(0,0,0,0.06)'
  const bg = isDark ? '#0e0e0e' : '#fafafa'
  const navigate = useNavigate()

  const handleSignOut = () => {
    localStorage.removeItem('token')
    localStorage.removeItem('user')
    navigate('/login')
  }

  const [mob, setMob] = useState(false)
  const [rp, setRp] = useState(true)
  const [input, setInput] = useState('')
  const [vm, setVm] = useState(false)
  const [listening, setListening] = useState(false)
  const [vt, setVt] = useState('')
  const [chats, setChats] = useState([
    { id: 1, title: 'Consumer refund dispute', time: 'Today' },
    { id: 2, title: 'RTI for land records', time: 'Yesterday' },
    { id: 3, title: 'Rental agreement review', time: '2 days ago' },
  ])
  const [aid, setAid] = useState(null)
  const [evidenceModal, setEvidenceModal] = useState(false)
  const [evidenceFiles, setEvidenceFiles] = useState([
    { id: 1, name: 'Rental_Agreement_2024.pdf', type: 'pdf', size: '2.4 MB', date: '20 Apr 2025' },
    { id: 2, name: 'Defective_Product_Photo.jpg', type: 'image', size: '1.1 MB', date: '18 Apr 2025' },
    { id: 3, name: 'Email_Correspondence.pdf', type: 'pdf', size: '340 KB', date: '15 Apr 2025' },
  ])
  const endRef = useRef(null)
  const taRef = useRef(null)
  const fileInputRef = useRef(null)
  const has = chatMessages.length > 0

  useEffect(() => { endRef.current?.scrollIntoView({ behavior: 'smooth' }) }, [chatMessages, isTyping])
  useEffect(() => { if (taRef.current) { taRef.current.style.height = 'auto'; taRef.current.style.height = Math.min(taRef.current.scrollHeight, 140) + 'px' } }, [input])

  const send = useCallback(async () => { const m = input.trim(); if (!m || isTyping) return; setInput(''); if (!aid) setAid(Date.now()); await sendMessage(m) }, [input, isTyping, sendMessage, aid])
  const prompt = useCallback(async (q) => { if (isTyping) return; setAid(Date.now()); await sendMessage(q) }, [isTyping, sendMessage])
  const kd = useCallback((e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send() } }, [send])

  const toolClick = (t) => {
    if (t.id === 'voice') { setVm(true); return }
    if (t.id === 'evidence') { setEvidenceModal(true); return }
    const p = { consult: 'I need legal consultation.', draft: 'Help me draft a legal document.', research: 'Find relevant laws for my case.', contract: 'Review a contract for red flags.', strength: 'Analyze my case strength.', rights: 'What are my legal rights?', escalation: 'My complaint was rejected, what next?' }
    prompt(p[t.id] || `Help with: ${t.label}`)
  }

  const handleFileUpload = (e) => {
    const files = Array.from(e.target.files)
    const newFiles = files.map((f, i) => ({
      id: Date.now() + i, name: f.name, type: f.type.startsWith('image') ? 'image' : 'pdf',
      size: f.size > 1048576 ? (f.size / 1048576).toFixed(1) + ' MB' : (f.size / 1024).toFixed(0) + ' KB',
      date: new Date().toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: 'numeric' })
    }))
    setEvidenceFiles(prev => [...newFiles, ...prev])
  }

  const deleteEvidence = (id) => setEvidenceFiles(prev => prev.filter(f => f.id !== id))

  const deleteChat = (id, e) => { e.stopPropagation(); setChats(c => c.filter(x => x.id !== id)); if (aid === id) setAid(null) }
  const newChat = () => { setAid(null); window.location.reload() }

  const togListen = useCallback(async () => {
    if (listening) { setListening(false); if (vt) { await sendMessage(vt); setVt('') } }
    else { setListening(true); setVt(''); const ch = ['I bought a defective phone...', 'My landlord is evicting me...'][Math.floor(Math.random() * 2)]; let i = 0; const iv = setInterval(() => { if (i < ch.length) { setVt(ch.slice(0, i + 1)); i++ } else clearInterval(iv) }, 40) }
  }, [listening, vt, sendMessage])

  const inputBar = (
    <div className="flex-shrink-0 px-4 py-3" style={{ borderTop: `1px solid ${b}` }}>
      <div className="mx-auto max-w-2xl">
        <div className="rounded-2xl p-1.5 flex items-end gap-1 shadow-lg" style={{ background: isDark ? 'rgba(18,18,18,0.9)' : 'rgba(255,255,255,0.95)', backdropFilter: 'blur(20px)', border: `1px solid ${b}` }}>
          <button onClick={() => setVm(true)} className="flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center hover:bg-white/5" style={{ color: 'var(--text-muted)' }}><Mic size={15} /></button>
          <textarea ref={taRef} value={input} onChange={e => setInput(e.target.value)} onKeyDown={kd} placeholder="Ask anything about Indian law..." rows={1} className="flex-1 text-[13px] leading-relaxed py-2 px-1.5 outline-none resize-none bg-transparent" style={{ color: 'var(--text-primary)', maxHeight: '130px' }} />
          <button onClick={send} disabled={!input.trim() || isTyping} className="flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center transition-all"
            style={{ background: input.trim() && !isTyping ? '#c9a84c' : (isDark ? 'rgba(255,255,255,0.04)' : 'rgba(0,0,0,0.03)'), color: input.trim() && !isTyping ? '#fff' : 'var(--text-muted)', boxShadow: input.trim() && !isTyping ? '0 3px 12px rgba(201,168,76,0.4)' : 'none' }}>
            <ArrowUp size={15} />
          </button>
        </div>
        <p className="text-[9px] mt-1 text-center" style={{ color: 'var(--text-muted)' }}>AI can make mistakes. Verify legal info.</p>
      </div>
    </div>
  )

  const sidebar = (
    <div className="flex flex-col h-full">
      {/* Logo only */}
      <div className="flex-shrink-0 flex items-center px-4 py-4" style={{ borderBottom: `1px solid ${b}` }}>
        <Link to="/" className="flex items-center gap-2">
          <span className="inline-flex h-8 w-8 items-center justify-center rounded-xl text-white shadow" style={{ background: '#0a0a0a' }}><Scale size={14} /></span>
          <span className="font-['Sora'] text-sm font-bold" style={{ color: 'var(--text-primary)' }}>NyayaMitr</span>
        </Link>
      </div>

      {/* New chat button */}
      <div className="flex-shrink-0 px-3 pt-3 pb-1">
        <button onClick={newChat} className="w-full flex items-center gap-2.5 px-3.5 py-2.5 rounded-xl text-left transition-all hover:scale-[1.02] hover:shadow-md"
          style={{ background: isDark ? 'rgba(255,255,255,0.05)' : 'rgba(0,0,0,0.04)', border: `1px solid ${b}`, color: 'var(--text-primary)' }}>
          <SquarePen size={14} />
          <span className="text-[12px] font-semibold">New Chat</span>
        </button>
      </div>

      {/* Chat list */}
      <nav className="flex-1 overflow-y-auto px-3 py-2">
        <p className="text-[9px] font-bold uppercase tracking-widest px-2 mb-2 mt-1" style={{ color: 'var(--text-muted)' }}>Recent</p>
        {chats.map(c => (
          <div key={c.id}
            role="button"
            tabIndex={0}
            onClick={() => { setAid(c.id); setMob(false) }}
            onKeyDown={(e) => e.key === 'Enter' && (setAid(c.id), setMob(false))}
            className="w-full flex items-center gap-2 px-3 py-2.5 rounded-xl text-left transition-all group hover:bg-white/5 mb-0.5 cursor-pointer"
            style={{ background: aid === c.id ? (isDark ? 'rgba(255,255,255,0.07)' : 'rgba(0,0,0,0.04)') : 'transparent' }}>
            <MessageSquare size={12} style={{ color: 'var(--text-muted)', flexShrink: 0 }} />
            <div className="min-w-0 flex-1">
              <p className="text-[11px] font-semibold truncate" style={{ color: 'var(--text-primary)' }}>{c.title}</p>
              <p className="text-[9px]" style={{ color: 'var(--text-muted)' }}>{c.time}</p>
            </div>
            <button onClick={(e) => deleteChat(c.id, e)} className="opacity-0 group-hover:opacity-100 transition-opacity p-1 rounded-md hover:bg-red-500/10" style={{ color: 'var(--text-muted)' }} title="Delete"><Trash2 size={11} /></button>
          </div>
        ))}
        {chats.length === 0 && <p className="text-[10px] px-2 mt-2" style={{ color: 'var(--text-muted)' }}>No chats yet</p>}
      </nav>

      {/* Bottom */}
      <div className="flex-shrink-0 px-3 py-3 space-y-0.5" style={{ borderTop: `1px solid ${b}` }}>
        <button onClick={toggleTheme} className="w-full flex items-center gap-2.5 px-3 py-2 rounded-xl text-left hover:bg-white/5" style={{ color: 'var(--text-muted)' }}>
          {isDark ? <Sun size={13} /> : <Moon size={13} />}<span className="text-[11px] font-semibold">{isDark ? 'Light' : 'Dark'} Mode</span>
        </button>
        <button onClick={handleSignOut} className="w-full flex items-center gap-2.5 px-3 py-2 rounded-xl text-left hover:bg-white/5" style={{ color: 'var(--text-muted)' }}>
          <LogOut size={13} /><span className="text-[11px] font-semibold">Sign Out</span>
        </button>
      </div>
    </div>
  )

  return (
    <div className="flex h-screen overflow-hidden" style={{ background: 'var(--bg-primary)' }}>
      {/* Evidence Hub Modal */}
      {evidenceModal && (
        <div className="fixed inset-0 z-[60] flex items-center justify-center">
          <div className="absolute inset-0 bg-black/50 backdrop-blur-sm" onClick={() => setEvidenceModal(false)} />
          <div className="relative w-full max-w-lg mx-4 rounded-2xl shadow-2xl flex flex-col" style={{ background: isDark ? '#141414' : '#fff', border: `1px solid ${b}`, maxHeight: '80vh' }}>
            <div className="flex-shrink-0 flex items-center justify-between px-5 py-4" style={{ borderBottom: `1px solid ${b}` }}>
              <div className="flex items-center gap-2.5">
                <div className="w-9 h-9 rounded-xl flex items-center justify-center" style={{ background: isDark ? 'rgba(201,168,76,0.12)' : 'rgba(201,168,76,0.08)' }}>
                  <FolderOpen size={16} style={{ color: '#c9a84c' }} />
                </div>
                <div>
                  <h3 className="text-sm font-bold" style={{ color: 'var(--text-primary)' }}>Evidence Hub</h3>
                  <p className="text-[10px]" style={{ color: 'var(--text-muted)' }}>{evidenceFiles.length} files uploaded</p>
                </div>
              </div>
              <button onClick={() => setEvidenceModal(false)} className="w-7 h-7 rounded-lg flex items-center justify-center hover:bg-white/5" style={{ color: 'var(--text-muted)' }}><X size={14} /></button>
            </div>
            <div className="flex-1 overflow-y-auto px-5 py-3" style={{ minHeight: '200px' }}>
              {evidenceFiles.length === 0 ? (
                <div className="flex flex-col items-center justify-center py-12">
                  <FolderOpen size={32} style={{ color: 'var(--text-muted)', opacity: 0.4 }} />
                  <p className="text-xs mt-3" style={{ color: 'var(--text-muted)' }}>No evidence uploaded yet</p>
                </div>
              ) : (
                <div className="space-y-2">
                  {evidenceFiles.map(f => (
                    <div key={f.id} className="flex items-center gap-3 rounded-xl px-3.5 py-3 group transition-all hover:shadow-sm" style={{ background: isDark ? 'rgba(255,255,255,0.03)' : 'rgba(0,0,0,0.02)', border: `1px solid ${b}` }}>
                      <div className="w-9 h-9 rounded-lg flex items-center justify-center flex-shrink-0" style={{ background: f.type === 'image' ? 'rgba(59,130,246,0.1)' : 'rgba(239,68,68,0.1)' }}>
                        {f.type === 'image' ? <Image size={16} style={{ color: '#3b82f6' }} /> : <File size={16} style={{ color: '#ef4444' }} />}
                      </div>
                      <div className="min-w-0 flex-1">
                        <p className="text-[12px] font-semibold truncate" style={{ color: 'var(--text-primary)' }}>{f.name}</p>
                        <div className="flex items-center gap-2 mt-0.5">
                          <span className="text-[10px]" style={{ color: 'var(--text-muted)' }}>{f.size}</span>
                          <span className="text-[10px] flex items-center gap-0.5" style={{ color: 'var(--text-muted)' }}><Clock size={8} />{f.date}</span>
                        </div>
                      </div>
                      <button onClick={() => deleteEvidence(f.id)} className="opacity-0 group-hover:opacity-100 transition-opacity p-1.5 rounded-lg hover:bg-red-500/10" style={{ color: 'var(--text-muted)' }}><Trash2 size={12} /></button>
                    </div>
                  ))}
                </div>
              )}
            </div>
            <div className="flex-shrink-0 px-5 py-4" style={{ borderTop: `1px solid ${b}` }}>
              <input ref={fileInputRef} type="file" multiple accept=".pdf,.jpg,.jpeg,.png,.doc,.docx" className="hidden" onChange={handleFileUpload} />
              <button onClick={() => fileInputRef.current?.click()} className="w-full flex items-center justify-center gap-2 rounded-xl py-3 transition-all hover:scale-[1.01] hover:shadow-md"
                style={{ background: isDark ? 'rgba(201,168,76,0.1)' : 'rgba(201,168,76,0.08)', border: '1px dashed rgba(201,168,76,0.3)', color: '#c9a84c' }}>
                <Upload size={16} />
                <span className="text-[12px] font-bold">Upload Evidence</span>
              </button>
              <p className="text-[9px] mt-1.5 text-center" style={{ color: 'var(--text-muted)' }}>PDF, JPG, PNG, DOC · Max 10 MB</p>
            </div>
          </div>
        </div>
      )}

      {mob && <div className="fixed inset-0 z-50 lg:hidden">
        <div className="absolute inset-0 bg-black/50 backdrop-blur-sm" onClick={() => setMob(false)} />
        <div className="absolute left-0 top-0 bottom-0 w-56 shadow-2xl" style={{ background: bg, borderRight: `1px solid ${b}` }}>
          <div className="absolute top-3 right-3"><button onClick={() => setMob(false)} style={{ color: 'var(--text-muted)' }}><X size={14} /></button></div>
          {sidebar}
        </div>
      </div>}

      <aside className="hidden lg:flex flex-col flex-shrink-0 w-56 h-screen" style={{ background: bg, borderRight: `1px solid ${b}` }}>{sidebar}</aside>

      <main className="flex-1 flex flex-col min-w-0 h-screen">
        <div className="flex-shrink-0 flex items-center px-4 py-2.5" style={{ borderBottom: `1px solid ${b}` }}>
          <button onClick={() => setMob(true)} className="lg:hidden mr-2 w-7 h-7 rounded-lg flex items-center justify-center" style={{ background: isDark ? 'rgba(255,255,255,0.05)' : 'rgba(0,0,0,0.03)', color: 'var(--text-secondary)' }}><Menu size={14} /></button>
          <h2 className="text-xs font-bold" style={{ color: 'var(--text-primary)' }}>{has ? 'Chat' : 'New Chat'}</h2>
          <div className="ml-auto flex items-center gap-2">
            {!rp && <button onClick={() => setRp(true)} className="w-7 h-7 rounded-lg flex items-center justify-center" style={{ background: isDark ? 'rgba(255,255,255,0.05)' : 'rgba(0,0,0,0.03)', color: 'var(--text-secondary)' }}><PanelRightOpen size={14} /></button>}
            <div className="w-7 h-7 rounded-full flex items-center justify-center" style={{ background: isDark ? 'rgba(255,255,255,0.06)' : 'rgba(0,0,0,0.04)' }}><User size={12} style={{ color: 'var(--text-muted)' }} /></div>
          </div>
        </div>

        <div className="flex-1 overflow-y-auto">
          {vm ? (
            <div className="h-full flex flex-col items-center justify-center px-4">
              <div style={{ width: '320px', height: '320px' }} className="relative mb-6">
                <VoiceRipple
                  color={isDark ? '#c9a84c' : '#8b7332'}
                  speed={listening ? 0.4 : 0.15}
                  amplitude={listening ? 2.0 : 0.8}
                  frequency={listening ? 14.0 : 8.0}
                  rippleRate={listening ? 3.0 : 1.5}
                  lineWidth={listening ? 6.0 : 12.0}
                  opacity={listening ? 1.0 : 0.5}
                  followMouse={true}
                  mouseInfluence={0.12}
                />
              </div>
              <div className="h-10 flex items-center justify-center mb-4">
                {vt ? <p className="text-sm text-center font-medium" style={{ color: 'var(--text-primary)' }}>"{vt}"</p> : <p className="text-xs font-bold" style={{ color: 'var(--text-secondary)' }}>{listening ? 'Listening...' : 'Tap mic to speak'}</p>}
              </div>
              <button onClick={togListen} className="w-16 h-16 rounded-full flex items-center justify-center transition-all hover:scale-105"
                style={{ background: listening ? '#ef4444' : (isDark ? '#111' : '#fff'), color: listening ? '#fff' : (isDark ? '#fff' : '#111'), boxShadow: listening ? '0 0 40px rgba(239,68,68,0.5)' : '0 8px 28px rgba(0,0,0,0.15)', border: listening ? 'none' : `1px solid ${b}` }}>
                {listening ? <MicOff size={22} /> : <Mic size={22} />}
              </button>
              <p className="mt-3 text-[10px]" style={{ color: 'var(--text-muted)' }}>हिंदी · தமிழ் · తెలుగు · English</p>
              <button onClick={() => setVm(false)} className="mt-5 px-4 py-2 rounded-full text-[11px] font-bold flex items-center gap-2 transition-all hover:shadow-md" style={{ color: 'var(--text-secondary)', border: `1px solid ${b}` }}><MessageSquare size={12} /> Text mode</button>
            </div>
          ) : !has ? (
            <div className="h-full flex flex-col items-center justify-center px-6">
              <div className="relative mb-5">
                <div className="absolute inset-0 blur-3xl opacity-15" style={{ background: '#c9a84c' }} />
                <div className="relative w-16 h-16 rounded-2xl flex items-center justify-center" style={{ background: isDark ? '#151515' : '#fff', border: `1px solid ${b}`, boxShadow: '0 8px 30px rgba(0,0,0,0.08)' }}>
                  <Scale size={28} style={{ color: '#c9a84c' }} />
                </div>
              </div>
              <h1 className="text-3xl font-extrabold mb-1.5 tracking-tight" style={{ color: 'var(--text-primary)' }}>NyayaMitr AI</h1>
              <p className="text-[13px] mb-8" style={{ color: 'var(--text-muted)' }}>Your AI legal assistant</p>
              <div className="flex flex-wrap justify-center gap-2 max-w-md">
                {pills.map(s => (
                  <button key={s} onClick={() => prompt(s)} className="rounded-full px-4 py-2 text-[12px] font-medium transition-all hover:scale-105 hover:shadow-md"
                    style={{ background: isDark ? 'rgba(255,255,255,0.04)' : 'rgba(0,0,0,0.03)', border: `1px solid ${b}`, color: 'var(--text-secondary)' }}>{s}</button>
                ))}
              </div>
            </div>
          ) : (
            <div className="px-4 py-4">
              <div className="space-y-5 max-w-2xl mx-auto">
                {chatMessages.map((msg, i) => (
                  <div key={i} className={`flex w-full ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                    {msg.role === 'ai' && <div className="flex-shrink-0 w-7 h-7 rounded-full flex items-center justify-center mr-2.5 mt-1" style={{ background: isDark ? '#151515' : '#fff', border: `1px solid ${b}` }}><Scale size={12} style={{ color: isDark ? '#fff' : '#111' }} /></div>}
                    <div className={`max-w-[80%] flex flex-col ${msg.role === 'user' ? 'items-end' : 'items-start'}`}>
                      {msg.role === 'ai' && msg.category && (
                        <div className="flex items-center gap-1.5 mb-1 ml-0.5">
                          <span className="text-[9px] font-bold px-1.5 py-0.5 rounded-full uppercase tracking-wider" style={{ background: 'var(--color-gold-soft)', color: '#c9a84c' }}>{msg.category}</span>
                          {msg.confidence && <span className="text-[9px] font-bold flex items-center gap-0.5" style={{ color: '#22c55e' }}><Sparkles size={8} />{msg.confidence}%</span>}
                        </div>
                      )}
                      <div className={`px-4 py-3 text-[13px] leading-relaxed ${msg.role === 'user' ? 'rounded-2xl rounded-tr-sm' : 'rounded-2xl rounded-tl-sm'}`}
                        style={msg.role === 'user' ? { background: isDark ? '#1a1a1a' : '#111', color: '#fff' } : { background: isDark ? 'rgba(255,255,255,0.03)' : 'rgba(0,0,0,0.02)', border: `1px solid ${b}`, color: 'var(--text-primary)' }}>
                        {msg.content.split('\n').map((line, j) => { const parts = line.split(/(\*\*.*?\*\*)/g); return (<div key={j} style={{ marginBottom: line === '' ? '0.5rem' : '0.15rem' }}>{parts.map((p, k) => p.startsWith('**') && p.endsWith('**') ? <strong key={k}>{p.slice(2, -2)}</strong> : <span key={k}>{p}</span>)}</div>) })}
                      </div>
                      {msg.role === 'ai' && msg.relatedSections && <div className="mt-1.5 flex flex-wrap gap-1 ml-0.5">{msg.relatedSections.map(s => <span key={s} className="rounded px-1.5 py-0.5 text-[9px] font-mono font-semibold" style={{ background: isDark ? '#151515' : '#f5f5f5', color: 'var(--text-muted)', border: `1px solid ${b}` }}>{s}</span>)}</div>}
                    </div>
                    {msg.role === 'user' && <div className="flex-shrink-0 w-7 h-7 rounded-full flex items-center justify-center ml-2.5 mt-1" style={{ background: isDark ? '#1a1a1a' : '#eee' }}><User size={12} style={{ color: 'var(--text-muted)' }} /></div>}
                  </div>
                ))}
                {isTyping && <div className="flex justify-start"><div className="flex-shrink-0 w-7 h-7 rounded-full flex items-center justify-center mr-2.5 mt-1" style={{ background: isDark ? '#151515' : '#fff', border: `1px solid ${b}` }}><Scale size={12} style={{ color: isDark ? '#fff' : '#111' }} /></div><div className="rounded-2xl rounded-tl-sm px-4 py-3" style={{ background: isDark ? 'rgba(255,255,255,0.03)' : 'rgba(0,0,0,0.02)', border: `1px solid ${b}` }}><div className="flex gap-1">{[0, 150, 300].map(d => <span key={d} className="w-1.5 h-1.5 rounded-full bg-[#c9a84c] animate-bounce" style={{ animationDelay: `${d}ms` }} />)}</div></div></div>}
                <div ref={endRef} className="h-2" />
              </div>
            </div>
          )}
        </div>
        {!vm && inputBar}
      </main>

      {rp && (
        <aside className="hidden md:flex flex-col flex-shrink-0 w-64 h-screen" style={{ background: bg, borderLeft: `1px solid ${b}` }}>
          <div className="flex-shrink-0 px-4 py-3 flex items-center justify-between" style={{ borderBottom: `1px solid ${b}` }}>
            <h3 className="text-[11px] font-bold uppercase tracking-wider" style={{ color: 'var(--text-muted)' }}>AI Tools</h3>
            <button onClick={() => setRp(false)} className="w-6 h-6 rounded-lg flex items-center justify-center hover:bg-white/5" style={{ color: 'var(--text-muted)' }}><X size={12} /></button>
          </div>
          <div className="flex-1 overflow-y-auto px-3 py-3">
            <div className="grid grid-cols-2 gap-2">
              {tools.map(t => (
                <button key={t.id} onClick={() => toolClick(t)} className="group flex flex-col items-center rounded-2xl p-3.5 text-center transition-all hover:scale-[1.03] hover:shadow-md" style={{ background: isDark ? 'rgba(255,255,255,0.03)' : 'rgba(0,0,0,0.02)', border: `1px solid ${b}` }}>
                  <t.icon size={18} className="mb-2 transition-colors group-hover:text-[#c9a84c]" style={{ color: 'var(--text-secondary)' }} />
                  <span className="text-[11px] font-bold leading-tight" style={{ color: 'var(--text-primary)' }}>{t.label}</span>
                  <span className="text-[9px] mt-0.5" style={{ color: 'var(--text-muted)' }}>{t.desc}</span>
                </button>
              ))}
            </div>
          </div>
          <div className="flex-shrink-0 px-3 py-3" style={{ borderTop: `1px solid ${b}` }}>
            <div className="rounded-xl p-3" style={{ background: isDark ? 'rgba(201,168,76,0.06)' : 'rgba(201,168,76,0.05)', border: '1px solid rgba(201,168,76,0.12)' }}>
              <p className="text-[10px] font-bold mb-0.5" style={{ color: '#c9a84c' }}>✨ How to use</p>
              <p className="text-[9px] leading-relaxed" style={{ color: 'var(--text-muted)' }}>Pick a tool or type your question directly.</p>
            </div>
          </div>
        </aside>
      )}
    </div>
  )
}

export default DashboardPage
