import {
  ArrowRight, Scale, FileText, Shield, Users, MessageSquare,
  Sparkles, Zap, Globe, BookOpen, Search, Mic, Phone,
  AlertTriangle, FileCheck, ChevronRight, Star, TrendingUp
} from 'lucide-react'
import { Link } from 'react-router-dom'
import { useTheme } from '../ThemeContext'
import MagicBentoCard from '../componts/MagicBentoCard'
import DotGrid from '../componts/DotGrid'
import { useState, useEffect } from 'react'

const rotatingWords = ['FIRs', 'RTIs', 'Complaints', 'Contracts', 'Legal Notices']

const LandingPage = () => {
  const { theme } = useTheme()
  const isDark = theme === 'dark'
  const [wordIdx, setWordIdx] = useState(0)
  const [fade, setFade] = useState(true)

  useEffect(() => {
    const interval = setInterval(() => {
      setFade(false)
      setTimeout(() => { setWordIdx((i) => (i + 1) % rotatingWords.length); setFade(true) }, 300)
    }, 2500)
    return () => clearInterval(interval)
  }, [])

  return (
    <div className="space-y-24 pb-20">
      {/* ═══════════ HERO ═══════════ */}
      <section className="relative min-h-[92vh] flex items-center justify-center overflow-hidden -mx-4 sm:-mx-6 lg:-mx-10 -mt-[5rem] pt-[5rem]">
        <div className="absolute inset-0 z-0">
          <DotGrid dotSize={2} gap={20} baseColor={isDark ? '#333333' : '#cccccc'} activeColor={isDark ? '#c9a84c' : '#0a0a0a'}
            proximity={150} speedTrigger={80} shockRadius={200} shockStrength={3} className="w-full h-full" />
        </div>
        {/* Ambient glows */}
        <div className="absolute top-1/4 left-1/4 w-[600px] h-[600px] rounded-full blur-[180px] pointer-events-none" style={{ background: '#c9a84c', opacity: isDark ? 0.06 : 0.04 }} />
        <div className="absolute bottom-1/4 right-1/4 w-[400px] h-[400px] rounded-full blur-[140px] pointer-events-none" style={{ background: isDark ? '#fff' : '#000', opacity: 0.03 }} />

        <div className="relative z-10 text-center max-w-5xl mx-auto px-4">
          <div className="animate-in delay-1">
            <span className="pill text-xs py-2.5 px-5" style={{ boxShadow: 'var(--shadow-md)', backdropFilter: 'blur(8px)' }}>
              <Scale size={13} /> AI-Powered Legal Assistance Platform
            </span>
          </div>

          <h1 className="animate-in delay-2 mt-8 text-5xl sm:text-6xl lg:text-7xl font-extrabold leading-[1.05] tracking-tight">
            Navigate Indian law<br />
            <span className="shimmer-text">without a law degree.</span>
          </h1>

          <p className="animate-in delay-3 mt-7 text-lg sm:text-xl max-w-2xl mx-auto leading-relaxed" style={{ color: 'var(--text-secondary)' }}>
            File{' '}
            <span className="inline-block min-w-[120px] text-left transition-all duration-300 font-bold" style={{ color: '#c9a84c', opacity: fade ? 1 : 0, transform: fade ? 'translateY(0)' : 'translateY(8px)' }}>
              {rotatingWords[wordIdx]}
            </span>
            , understand contracts, and get step-by-step legal guidance — all in plain language, powered by AI.
          </p>

          <div className="animate-in delay-4 mt-10 flex flex-wrap items-center justify-center gap-4">
            <Link to="/login" className="btn-accent text-base px-8 py-4 group">
              Get Started <ArrowRight size={16} className="group-hover:translate-x-1 transition-transform" />
            </Link>
            <a href="#features" className="btn-ghost text-base px-8 py-4">Explore Features</a>
          </div>

          {/* Trust stats */}
          <div className="animate-in delay-5 mt-14 flex items-center justify-center gap-6 sm:gap-10 flex-wrap">
            {[
              { value: '10K+', label: 'Cases Analyzed' },
              { value: '12+', label: 'Languages' },
              { value: '95%', label: 'Accuracy' },
              { value: '50+', label: 'Legal Areas' },
            ].map((s) => (
              <div key={s.label} className="text-center px-3">
                <p className="text-2xl sm:text-3xl font-black tracking-tight" style={{ color: 'var(--text-primary)' }}>{s.value}</p>
                <p className="text-[11px] font-bold uppercase tracking-wider mt-1" style={{ color: 'var(--text-muted)' }}>{s.label}</p>
              </div>
            ))}
          </div>

          {/* Floating badges */}
          <div className="animate-in delay-5 mt-8 flex items-center justify-center gap-6 sm:gap-8 flex-wrap">
            {[
              { icon: Shield, label: 'Multi-lingual' },
              { icon: Zap, label: 'Instant AI Analysis' },
              { icon: Globe, label: 'Pan-India Coverage' },
            ].map((b) => (
              <div key={b.label} className="flex items-center gap-2 text-xs font-bold" style={{ color: 'var(--text-muted)' }}>
                <b.icon size={14} style={{ color: 'var(--text-primary)' }} /> {b.label}
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ═══════════ FEATURES ═══════════ */}
      <section id="features" className="mx-auto max-w-6xl px-4">
        <div className="text-center mb-14">
          <p className="section-label mb-3">What NyayaMitr Does</p>
          <h2 className="text-3xl sm:text-4xl lg:text-5xl font-extrabold" style={{ color: 'var(--text-primary)' }}>
            Legal empowerment.<br className="hidden sm:block" /> One platform.
          </h2>
        </div>
        {/* Row 1 */}
        <div className="grid gap-4 lg:grid-cols-[1.3fr_0.7fr] mb-4">
          <MagicBentoCard className="p-8 sm:p-10 flex flex-col justify-between min-h-[340px]">
            <div>
              <div className="inline-flex rounded-2xl p-3.5 mb-5" style={{ background: '#111' }}>
                <MessageSquare size={26} style={{ color: '#fff' }} />
              </div>
              <h3 className="text-2xl sm:text-[1.75rem] font-extrabold mb-3" style={{ color: 'var(--text-primary)' }}>AI Legal Consultation</h3>
              <p className="text-sm leading-relaxed max-w-md" style={{ color: 'var(--text-secondary)' }}>
                Describe your situation in plain language. Our AI understands context, identifies applicable laws, and walks you through your options — step by step.
              </p>
            </div>
            <div className="mt-7 flex items-center gap-2.5 flex-wrap">
              {['Describe', 'Analyze', 'Advise', 'Draft'].map((step, i) => (
                <div key={step} className="flex items-center gap-2">
                  <span className="rounded-lg px-3.5 py-2 text-xs font-bold" style={{
                    background: i === 3 ? '#0a0a0a' : 'var(--bg-tertiary)', color: i === 3 ? '#fff' : 'var(--text-secondary)',
                  }}>{step}</span>
                  {i < 3 && <ArrowRight size={12} style={{ color: 'var(--text-muted)' }} />}
                </div>
              ))}
            </div>
          </MagicBentoCard>
          <div className="p-8 flex flex-col justify-between min-h-[340px] rounded-3xl transition-all hover:translate-y-[-4px]" style={{
            background: '#111', color: '#f0f0f0', boxShadow: '0 8px 32px rgba(0,0,0,0.25)', border: '1px solid rgba(255,255,255,0.05)'
          }}>
            <div>
              <FileCheck size={36} className="mb-5 opacity-80" />
              <h3 className="text-2xl font-extrabold mb-3">Auto-Drafting</h3>
              <p className="text-sm leading-relaxed opacity-80">AI generates ready-to-print PDFs for RTI applications, consumer complaints, legal notices, and more.</p>
            </div>
            <div className="mt-7 flex flex-wrap gap-2">
              {['RTI', 'Legal Notice', 'Consumer Complaint', 'FIR Draft', 'Escalation'].map((t) => (
                <span key={t} className="rounded-full px-3 py-1.5 text-xs font-bold bg-white/10 backdrop-blur-sm hover:bg-white/20 transition-all">{t}</span>
              ))}
            </div>
          </div>
        </div>

        {/* Row 2 */}
        <div className="grid gap-4 sm:grid-cols-3 mb-4">
          <MagicBentoCard className="p-6">
            <div className="inline-flex rounded-xl p-2.5 mb-3" style={{ background: '#111' }}>
              <Search size={20} style={{ color: '#fff' }} />
            </div>
            <h3 className="text-base font-extrabold mb-2" style={{ color: 'var(--text-primary)' }}>Contract Analyzer</h3>
            <p className="text-sm" style={{ color: 'var(--text-secondary)' }}>Upload rental or employment contracts. AI highlights red flags in plain language.</p>
            <div className="mt-4 space-y-2">
              {[{ flag: 'Lock-in — 24 months', sev: 'w' }, { flag: 'Deposit exceeds 2 months', sev: 'd' }].map((item) => (
                <div key={item.flag} className="rounded-lg px-3 py-2 text-xs flex items-center gap-2" style={{ background: 'var(--bg-secondary)', border: '1px solid var(--border)' }}>
                  <AlertTriangle size={11} style={{ color: item.sev === 'd' ? '#ef4444' : '#f59e0b' }} />
                  <span className="font-semibold" style={{ color: 'var(--text-primary)' }}>{item.flag}</span>
                </div>
              ))}
            </div>
          </MagicBentoCard>
          <MagicBentoCard className="p-6">
            <div className="inline-flex rounded-xl p-2.5 mb-3" style={{ background: '#111' }}>
              <AlertTriangle size={20} style={{ color: '#fff' }} />
            </div>
            <h3 className="text-base font-extrabold mb-2" style={{ color: 'var(--text-primary)' }}>Complaint Strength</h3>
            <p className="text-sm" style={{ color: 'var(--text-secondary)' }}>AI reviews your case strength and tells you what evidence you still need.</p>
            <div className="mt-4 grid grid-cols-2 gap-2">
              {[{ l: 'Strength', v: '85%', c: '#22c55e' }, { l: 'Evidence', v: '4/6', c: 'var(--text-primary)' }, { l: 'Forum', v: 'District', c: 'var(--text-primary)' }, { l: 'Timeline', v: '3-5 mo', c: '#c9a84c' }].map((m) => (
                <div key={m.l} className="rounded-lg px-2.5 py-2 text-center" style={{ background: 'var(--bg-secondary)' }}>
                  <p className="text-xs font-bold" style={{ color: m.c }}>{m.v}</p>
                  <p className="text-[10px] font-medium" style={{ color: 'var(--text-muted)' }}>{m.l}</p>
                </div>
              ))}
            </div>
          </MagicBentoCard>
          <MagicBentoCard className="p-6">
            <div className="inline-flex rounded-xl p-2.5 mb-3" style={{ background: '#111' }}>
              <BookOpen size={20} style={{ color: '#fff' }} />
            </div>
            <h3 className="text-base font-extrabold mb-2" style={{ color: 'var(--text-primary)' }}>Legal Research</h3>
            <p className="text-sm" style={{ color: 'var(--text-secondary)' }}>Finds relevant IPC, CrPC, consumer law sections for your situation.</p>
            <div className="mt-4 space-y-2">
              {[{ s: 'Sec 154 CrPC', d: 'FIR Registration' }, { s: 'Sec 2(6) CPA', d: 'Defect' }, { s: 'Article 21', d: 'Right to Life' }].map((x) => (
                <div key={x.s} className="flex items-center gap-2 text-xs">
                  <span className="rounded-md px-2 py-1 font-mono" style={{ background: 'var(--bg-secondary)', color: 'var(--text-muted)' }}>{x.s}</span>
                  <span className="font-medium" style={{ color: 'var(--text-secondary)' }}>{x.d}</span>
                </div>
              ))}
            </div>
          </MagicBentoCard>
        </div>

        {/* Row 3 */}
        <div className="grid gap-4 lg:grid-cols-[0.7fr_1.3fr]">
          <MagicBentoCard className="p-8 flex flex-col justify-between">
            <div>
              <div className="inline-flex rounded-2xl p-3 mb-4" style={{ background: '#111' }}>
                <Mic size={24} style={{ color: '#fff' }} />
              </div>
              <h3 className="text-xl font-extrabold mb-2" style={{ color: 'var(--text-primary)' }}>Voice Agent</h3>
              <p className="text-sm" style={{ color: 'var(--text-secondary)' }}>Speak in your language — Hindi, Marathi, Tamil, or more. The AI listens and responds.</p>
            </div>
            <div className="mt-5 flex flex-wrap gap-2">
              {['हिंदी', 'मराठी', 'தமிழ்', 'తెలుగు', 'English'].map((l) => (
                <span key={l} className="rounded-full px-3 py-1.5 text-xs font-bold" style={{ background: 'var(--bg-secondary)', border: '1px solid var(--border)', color: 'var(--text-secondary)' }}>{l}</span>
              ))}
            </div>
          </MagicBentoCard>
          <div className="p-8 sm:p-10 rounded-3xl transition-all hover:translate-y-[-4px]" style={{
            background: '#111', color: '#f5f5f5', boxShadow: '0 8px 32px rgba(0,0,0,0.3)', border: '1px solid rgba(255,255,255,0.06)',
          }}>
            <div className="flex items-center gap-3 mb-6">
              <div className="inline-flex rounded-2xl p-3" style={{ background: 'rgba(255,255,255,0.08)' }}>
                <Globe size={24} style={{ color: '#c9a84c' }} />
              </div>
              <div>
                <h3 className="text-xl font-extrabold text-white">Available Everywhere</h3>
                <p className="text-xs text-gray-400">Access justice from any device</p>
              </div>
            </div>
            <div className="grid grid-cols-2 gap-3">
              {[
                { icon: Globe, label: 'Web App', desc: 'Full browser app', color: '#fff' },
                { icon: Phone, label: 'Mobile', desc: 'Android & iOS', color: '#c9a84c' },
                { icon: MessageSquare, label: 'WhatsApp', desc: 'Chat with bot', color: '#25D366' },
                { icon: Mic, label: 'Voice Call', desc: 'Call for guidance', color: '#f59e0b' },
              ].map((e) => (
                <div key={e.label} className="rounded-xl p-4 border border-white/10 bg-white/5 hover:bg-white/10 hover:scale-[1.02] transition-all">
                  <e.icon size={20} style={{ color: e.color }} className="mb-2" />
                  <p className="text-sm font-bold text-white">{e.label}</p>
                  <p className="text-xs text-gray-400 mt-0.5">{e.desc}</p>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* ═══════════ WHO WE SERVE ═══════════ */}
      <section className="mx-auto max-w-6xl px-4">
        <div className="text-center mb-14">
          <p className="section-label mb-3">Who We Serve</p>
          <h2 className="text-3xl sm:text-4xl lg:text-5xl font-extrabold" style={{ color: 'var(--text-primary)' }}>Justice for everyone</h2>
        </div>
        <div className="grid gap-5 sm:grid-cols-2 lg:grid-cols-4">
          {[
            { n: '01', icon: Users, title: 'Urban Migrants', desc: 'Tenant rights, worker protections, consumer disputes.' },
            { n: '02', icon: Scale, title: 'Rural Citizens', desc: 'Land disputes, labour issues, government schemes.' },
            { n: '03', icon: Shield, title: 'Women & Families', desc: 'Domestic violence, workplace harassment, maintenance.' },
            { n: '04', icon: BookOpen, title: 'Small Businesses', desc: 'Consumer courts, contracts, regulatory compliance.' },
          ].map((s) => (
            <MagicBentoCard key={s.n} className="p-6 group">
              <span className="absolute -top-3 -right-2 text-[5rem] font-black opacity-[0.03] select-none pointer-events-none">{s.n}</span>
              <div className="relative z-10">
                <div className="inline-flex rounded-xl p-2.5 mb-4 group-hover:scale-110 transition-transform" style={{ background: '#111' }}>
                  <s.icon size={22} style={{ color: '#fff' }} />
                </div>
                <h3 className="text-lg font-extrabold mb-2" style={{ color: 'var(--text-primary)' }}>{s.title}</h3>
                <p className="text-sm leading-relaxed" style={{ color: 'var(--text-secondary)' }}>{s.desc}</p>
              </div>
            </MagicBentoCard>
          ))}
        </div>
      </section>

      {/* ═══════════ HOW IT WORKS ═══════════ */}
      <section className="mx-auto max-w-6xl px-4">
        <div className="text-center mb-14">
          <p className="section-label mb-3">How It Works</p>
          <h2 className="text-3xl sm:text-4xl lg:text-5xl font-extrabold" style={{ color: 'var(--text-primary)' }}>From confusion to clarity</h2>
        </div>
        <div className="grid gap-5 sm:grid-cols-3">
          {[
            { n: '01', icon: MessageSquare, title: 'Describe', desc: 'Tell us what happened — in your own words, in your own language.' },
            { n: '02', icon: Sparkles, title: 'AI Analyzes', desc: 'Our AI identifies laws, assesses strength, and builds an action plan.' },
            { n: '03', icon: FileText, title: 'Act', desc: 'Get ready-to-file documents and take action with confidence.' },
          ].map((s) => (
            <MagicBentoCard key={s.n} className="p-8 group text-center">
              <div className="relative z-10">
                <span className="inline-flex items-center justify-center w-12 h-12 rounded-2xl mb-5 text-lg font-black group-hover:scale-110 transition-transform" style={{ background: '#111', color: '#fff' }}>{s.n}</span>
                <div className="inline-flex rounded-xl p-2.5 mb-4 mx-auto"><s.icon size={28} style={{ color: 'var(--text-primary)' }} /></div>
                <h3 className="text-lg font-extrabold mb-2" style={{ color: 'var(--text-primary)' }}>{s.title}</h3>
                <p className="text-sm leading-relaxed" style={{ color: 'var(--text-secondary)' }}>{s.desc}</p>
              </div>
            </MagicBentoCard>
          ))}
        </div>
      </section>

      {/* ═══════════ CTA ═══════════ */}
      <section className="mx-auto max-w-6xl px-4">
        <div className="p-10 sm:p-16 text-center relative overflow-hidden rounded-3xl" style={{
          background: '#111', color: '#f0f0f0', boxShadow: '0 12px 48px rgba(0,0,0,0.3)', border: '1px solid rgba(255,255,255,0.05)'
        }}>
          <div className="absolute top-0 right-0 w-[350px] h-[350px] rounded-full blur-[100px] bg-white/[0.03] -translate-y-1/2 translate-x-1/3 pointer-events-none" />
          <div className="relative z-10">
            <h2 className="text-3xl sm:text-4xl lg:text-5xl font-extrabold">Don't let paperwork stop you.</h2>
            <p className="mt-5 text-base sm:text-lg opacity-80 max-w-xl mx-auto">Describe your situation. Get step-by-step guidance and ready-to-file documents.</p>
            <Link to="/login" className="mt-9 inline-flex items-center gap-2 rounded-xl bg-white px-8 py-4 text-base font-bold hover:-translate-y-1 hover:shadow-xl transition-all" style={{ color: '#0a0a0a' }}>
              Get Started Free <ArrowRight size={18} />
            </Link>
          </div>
        </div>
      </section>
    </div>
  )
}

export default LandingPage
