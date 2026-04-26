import { useState, useRef, useCallback, useEffect } from 'react'
import { useTheme } from '../ThemeContext'
import { useChat } from '../hooks/useChat'
import { useParams, useNavigate, Link } from 'react-router-dom'
import VoiceRipple from '../componts/VoiceRipple'
import { Scale, MessageSquare, FileText, Search, FolderOpen, Mic, MicOff, Plus, ArrowUp, Sparkles, User, Menu, X, LogOut, Moon, Sun, Trash2, TrendingUp, Shield, Gavel, BookOpen, PanelRightOpen, SquarePen, Upload, Image, File, Clock, ChevronDown, ChevronUp, Wrench, Eye, Lightbulb, Activity, Languages, ClipboardCheck, CalendarCheck, FileStack, Download, Paperclip, Loader2 } from 'lucide-react'

const tools = [
  { id: 'consult', icon: MessageSquare, label: 'AI Consult', desc: 'Legal guidance' },
  { id: 'draft', icon: FileText, label: 'Auto-Draft', desc: 'Generate PDFs' },
  { id: 'research', icon: Search, label: 'Legal Research', desc: 'Find laws' },
  { id: 'contract', icon: BookOpen, label: 'Contract Review', desc: 'Spot red flags' },
  { id: 'strength', icon: TrendingUp, label: 'Case Strength', desc: 'Analyze case' },
  { id: 'evidence', icon: FolderOpen, label: 'Evidence Hub', desc: 'Organize proof' },
  { id: 'rights', icon: Shield, label: 'Know Rights', desc: 'Rights & duties' },
  { id: 'escalation', icon: Gavel, label: 'Escalation', desc: 'Next steps' },
  { id: 'hearing', icon: CalendarCheck, label: 'Hearing Prep', desc: 'Court ready' },
  { id: 'summarise', icon: FileStack, label: 'Doc Summary', desc: 'Summarize docs' },
  { id: 'translate', icon: Languages, label: 'Translate', desc: 'Any language' },
  { id: 'checklist', icon: ClipboardCheck, label: 'Checklist', desc: 'What to bring' },
  { id: 'voice', icon: Mic, label: 'Voice Agent', desc: 'Speak naturally' },
]

const pills = ['How do I file an FIR?', 'Review my rental agreement', 'File a consumer complaint', 'My rights at workplace']

const languages = [
  { code: 'en', name: 'English', native: 'English', flag: '🇬🇧' },
  { code: 'hi', name: 'Hindi', native: 'हिन्दी', flag: '🇮🇳' },
  { code: 'mr', name: 'Marathi', native: 'मराठी', flag: '🇮🇳' },
  { code: 'ta', name: 'Tamil', native: 'தமிழ்', flag: '🇮🇳' },
  { code: 'te', name: 'Telugu', native: 'తెలుగు', flag: '🇮🇳' },
  { code: 'kn', name: 'Kannada', native: 'ಕನ್ನಡ', flag: '🇮🇳' },
  { code: 'bn', name: 'Bengali', native: 'বাংলা', flag: '🇮🇳' },
  { code: 'gu', name: 'Gujarati', native: 'ગુજરાતી', flag: '🇮🇳' },
  { code: 'ml', name: 'Malayalam', native: 'മലയാളം', flag: '🇮🇳' },
]

// Inline markdown renderer — handles headers, bold, bullets, horizontal rules
const MarkdownMessage = ({ content, isDark }) => {
  const lines = content.split('\n')
  const elements = []
  let i = 0

  while (i < lines.length) {
    const line = lines[i]

    // H3 ###
    if (line.startsWith('### ')) {
      elements.push(
        <div key={i} className="font-bold text-[13px] mt-3 mb-1" style={{ color: isDark ? '#e5e5e5' : '#111' }}>
          {renderInline(line.slice(4))}
        </div>
      )
    }
    // H2 ##
    else if (line.startsWith('## ')) {
      elements.push(
        <div key={i} className="font-extrabold text-[14px] mt-4 mb-1.5" style={{ color: isDark ? '#fff' : '#000' }}>
          {renderInline(line.slice(3))}
        </div>
      )
    }
    // H1 #
    else if (line.startsWith('# ')) {
      elements.push(
        <div key={i} className="font-extrabold text-[15px] mt-4 mb-2" style={{ color: isDark ? '#fff' : '#000' }}>
          {renderInline(line.slice(2))}
        </div>
      )
    }
    // Horizontal rule ---
    else if (/^---+$/.test(line.trim())) {
      elements.push(
        <hr key={i} className="my-2 border-0 border-t" style={{ borderColor: isDark ? 'rgba(255,255,255,0.08)' : 'rgba(0,0,0,0.08)' }} />
      )
    }
    // Bullet - or *
    else if (/^[\-\*] /.test(line)) {
      elements.push(
        <div key={i} className="flex gap-2 text-[12.5px] my-0.5 ml-1">
          <span className="flex-shrink-0 mt-1 w-1.5 h-1.5 rounded-full bg-[#c9a84c]" />
          <span>{renderInline(line.slice(2))}</span>
        </div>
      )
    }
    // Numbered list 1. 2. etc
    else if (/^\d+\. /.test(line)) {
      const num = line.match(/^(\d+)\. /)[1]
      elements.push(
        <div key={i} className="flex gap-2 text-[12.5px] my-0.5 ml-1">
          <span className="flex-shrink-0 font-bold text-[#c9a84c] text-[11px] mt-0.5 w-4">{num}.</span>
          <span>{renderInline(line.replace(/^\d+\. /, ''))}</span>
        </div>
      )
    }
    // Empty line — spacing
    else if (line.trim() === '') {
      elements.push(<div key={i} className="h-1.5" />)
    }
    // Normal paragraph
    else {
      elements.push(
        <div key={i} className="text-[12.5px] leading-relaxed my-0.5">
          {renderInline(line)}
        </div>
      )
    }
    i++
  }

  return <div className="space-y-0">{elements}</div>
}

// Render inline markdown: **bold**, *italic*, `code`
const renderInline = (text) => {
  const parts = text.split(/(\*\*[^*]+\*\*|\*[^*]+\*|`[^`]+`)/g)
  return parts.map((part, i) => {
    if (part.startsWith('**') && part.endsWith('**'))
      return <strong key={i} className="font-semibold">{part.slice(2, -2)}</strong>
    if (part.startsWith('*') && part.endsWith('*'))
      return <em key={i}>{part.slice(1, -1)}</em>
    if (part.startsWith('`') && part.endsWith('`'))
      return <code key={i} className="px-1 py-0.5 rounded text-[11px] font-mono" style={{ background: 'rgba(201,168,76,0.12)', color: '#c9a84c' }}>{part.slice(1, -1)}</code>
    return <span key={i}>{part}</span>
  })
}

// ── Thinking Panel ────────────────────────────────────────────────────────────
// Strip code blocks, HTML tags, and noise from thought text for display
const cleanThought = (text) => {
  if (!text) return ''
  return text
    .replace(/```py[\s\S]*?```/g, '')  // remove fenced python blocks
    .replace(/```[\s\S]*?```/g, '')    // remove other fenced blocks
    .replace(/`{1,3}py\n?/g, '')       // remove stray ```py
    .replace(/<end_code>/g, '')         // remove <end_code> markers
    .replace(/<\/code>/g, '')           // remove </code> HTML tags
    .replace(/<code>/g, '')             // remove <code> HTML tags
    .replace(/^Code:\s*$/gm, '')        // remove bare "Code:" lines
    .replace(/^Thought:\s*/i, '')       // strip leading "Thought:" label
    .replace(/\n{3,}/g, '\n\n')         // collapse multiple blank lines
    .trim()
}
const TOOL_COLORS = {
  intake_analyzer:    '#3b82f6',
  case_classifier:    '#8b5cf6',
  jurisdiction_resolver: '#10b981',
  legal_retriever:    '#f59e0b',
  workflow_planner:   '#ec4899',
  draft_generator:    '#06b6d4',
  document_exporter:  '#84cc16',
  authority_finder:   '#f97316',
  checklist_generator:'#a855f7',
  web_search:         '#6366f1',
  visit_webpage:      '#6366f1',
  complaint_strength_analyser: '#ef4444',
  evidence_organiser: '#14b8a6',
  translator:         '#f59e0b',
  language_detector:  '#64748b',
  final_answer:       '#22c55e',
  python_interpreter: '#94a3b8',
}

const toolColor = (name) => TOOL_COLORS[name] || '#c9a84c'

const toolLabel = (name) => name
  ? name.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())
  : 'Tool'

const ThinkingPanel = ({ steps, isDark }) => {
  const [open, setOpen] = useState(false)
  if (!steps || steps.length === 0) return null

  const b = isDark ? 'rgba(255,255,255,0.06)' : 'rgba(0,0,0,0.06)'

  // Count tool calls for summary
  const toolCalls = steps.filter(s => s.type === 'tool')
  const thoughtCount = steps.filter(s => s.type === 'thought').length

  return (
    <div className="mt-2 w-full">
      {/* Toggle button */}
      <button
        onClick={() => setOpen(o => !o)}
        className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-[10px] font-semibold transition-all hover:scale-[1.02]"
        style={{
          background: isDark ? 'rgba(255,255,255,0.04)' : 'rgba(0,0,0,0.03)',
          border: `1px solid ${b}`,
          color: 'var(--text-muted)',
        }}
      >
        <Activity size={10} style={{ color: '#c9a84c' }} />
        <span>
          {open ? 'Hide' : 'Show'} thinking
          {toolCalls.length > 0 && (
            <span className="ml-1 px-1.5 py-0.5 rounded-full text-[9px] font-bold"
              style={{ background: 'rgba(201,168,76,0.15)', color: '#c9a84c' }}>
              {toolCalls.length} tool{toolCalls.length !== 1 ? 's' : ''}
            </span>
          )}
        </span>
        {open ? <ChevronUp size={10} /> : <ChevronDown size={10} />}
      </button>

      {/* Expanded panel */}
      {open && (
        <div
          className="mt-2 rounded-xl overflow-hidden"
          style={{ border: `1px solid ${b}`, background: isDark ? 'rgba(10,10,10,0.6)' : 'rgba(248,248,248,0.8)' }}
        >
          {/* Header */}
          <div className="flex items-center gap-2 px-3 py-2" style={{ borderBottom: `1px solid ${b}`, background: isDark ? 'rgba(255,255,255,0.02)' : 'rgba(0,0,0,0.02)' }}>
            <div className="w-1.5 h-1.5 rounded-full bg-[#c9a84c] animate-pulse" />
            <span className="text-[10px] font-bold uppercase tracking-widest" style={{ color: 'var(--text-muted)' }}>
              Agent Trace — {steps.length} steps
            </span>
          </div>

          {/* Steps */}
          <div className="px-3 py-2 space-y-1.5 max-h-80 overflow-y-auto">
            {steps.map((step, i) => {
              if (step.type === 'plan') return (
                <div key={i} className="rounded-lg p-2.5" style={{ background: isDark ? 'rgba(99,102,241,0.08)' : 'rgba(99,102,241,0.05)', border: '1px solid rgba(99,102,241,0.15)' }}>
                  <div className="flex items-center gap-1.5 mb-1">
                    <Lightbulb size={10} style={{ color: '#6366f1' }} />
                    <span className="text-[9px] font-bold uppercase tracking-wider" style={{ color: '#6366f1' }}>Plan</span>
                  </div>
                  <pre className="text-[10px] leading-relaxed whitespace-pre-wrap font-mono" style={{ color: isDark ? '#a5b4fc' : '#4338ca' }}>
                    {cleanThought(step.content)?.slice(0, 400)}{step.content?.length > 400 ? '…' : ''}
                  </pre>
                </div>
              )

              if (step.type === 'thought') return (
                <div key={i} className="rounded-lg p-2.5" style={{ background: isDark ? 'rgba(255,255,255,0.02)' : 'rgba(0,0,0,0.02)', border: `1px solid ${b}` }}>
                  <div className="flex items-center gap-1.5 mb-1">
                    <span className="text-[9px] font-bold px-1.5 py-0.5 rounded" style={{ background: isDark ? 'rgba(255,255,255,0.06)' : 'rgba(0,0,0,0.05)', color: 'var(--text-muted)' }}>
                      Step {step.step}
                    </span>
                    <span className="text-[9px] font-bold uppercase tracking-wider" style={{ color: 'var(--text-muted)' }}>Thought</span>
                  </div>
                  <p className="text-[10px] leading-relaxed" style={{ color: isDark ? '#94a3b8' : '#64748b' }}>
                    {cleanThought(step.content)?.slice(0, 300)}
                    {(cleanThought(step.content)?.length || 0) > 300 ? '…' : ''}
                  </p>
                </div>
              )

              if (step.type === 'tool') return (
                <div key={i} className="flex items-center gap-2 rounded-lg px-2.5 py-2" style={{ background: `${toolColor(step.name)}10`, border: `1px solid ${toolColor(step.name)}25` }}>
                  <div className="w-5 h-5 rounded-md flex items-center justify-center flex-shrink-0" style={{ background: `${toolColor(step.name)}20` }}>
                    <Wrench size={9} style={{ color: toolColor(step.name) }} />
                  </div>
                  <div className="flex-1 min-w-0">
                    <span className="text-[10px] font-bold" style={{ color: toolColor(step.name) }}>
                      {toolLabel(step.name)}
                    </span>
                    <span className="text-[9px] ml-1.5" style={{ color: 'var(--text-muted)' }}>called</span>
                  </div>
                  <div className="w-1.5 h-1.5 rounded-full flex-shrink-0" style={{ background: toolColor(step.name) }} />
                </div>
              )

              if (step.type === 'observation') return (
                <div key={i} className="rounded-lg p-2.5" style={{ background: isDark ? 'rgba(34,197,94,0.05)' : 'rgba(34,197,94,0.04)', border: '1px solid rgba(34,197,94,0.15)' }}>
                  <div className="flex items-center gap-1.5 mb-1">
                    <Eye size={9} style={{ color: '#22c55e' }} />
                    <span className="text-[9px] font-bold uppercase tracking-wider" style={{ color: '#22c55e' }}>Result</span>
                  </div>
                  <pre className="text-[10px] leading-relaxed whitespace-pre-wrap font-mono overflow-x-auto" style={{ color: isDark ? '#86efac' : '#15803d' }}>
                    {step.content?.slice(0, 500)}{step.content?.length > 500 ? '…' : ''}
                  </pre>
                </div>
              )

              return null
            })}
          </div>
        </div>
      )}
    </div>
  )
}

const DashboardPage = () => {
  const { theme, toggleTheme } = useTheme()
  const { caseId: routeCaseId } = useParams()
  const navigate = useNavigate()
  const { messages, isLoading, caseId, createCase, loadCase, sendMessage: sendChatMessage, uploadEvidence, loadEvidence, exportDocument, downloadDocument, downloadEvidence, extractFileText } = useChat()
  const isDark = theme === 'dark'
  const b = isDark ? 'rgba(255,255,255,0.06)' : 'rgba(0,0,0,0.06)'
  const bg = isDark ? '#0e0e0e' : '#fafafa'

  // Initialize case on mount
  useEffect(() => {
    const initCase = async () => {
      if (routeCaseId && routeCaseId !== 'new') {
        try {
          await loadCase(routeCaseId)
        } catch (err) {
          console.error('Failed to load case:', err)
          navigate('/notebooks')
        }
      } else if (routeCaseId === 'new') {
        try {
          const newCaseId = await createCase()
          navigate(`/dashboard/${newCaseId}`, { replace: true })
        } catch (err) {
          console.error('Failed to create case:', err)
        }
      }
    }

    initCase()
  }, [routeCaseId, loadCase, createCase, navigate])

  const [mob, setMob] = useState(false)
  const [rp, setRp] = useState(true)
  const [input, setInput] = useState('')
  const [targetLang, setTargetLang] = useState('English')
  const [vm, setVm] = useState(false)
  const [listening, setListening] = useState(false)
  const [vt, setVt] = useState('')
  const [chats, setChats] = useState([])
  const [aid, setAid] = useState(null)
  const [evidenceModal, setEvidenceModal] = useState(false)
  const [evidenceFiles, setEvidenceFiles] = useState([])
  const [uploadingEvidence, setUploadingEvidence] = useState(false)
  const [sidebarDocs, setSidebarDocs] = useState({ uploads: [], exports: [] })
  const endRef = useRef(null)
  const taRef = useRef(null)
  const fileInputRef = useRef(null)
  const chatFileRef = useRef(null)
  const [attachedFile, setAttachedFile] = useState(null)
  const [extracting, setExtracting] = useState(false)
  const [extractedText, setExtractedText] = useState(null)
  const has = messages.some(m => m.role === 'user' || m.content)

  // Load docs for sidebar whenever case or messages change
  useEffect(() => {
    if (!caseId) return
    const token = localStorage.getItem('token')
    fetch(`/api/cases/${caseId}`, { headers: { 'Authorization': `Bearer ${token}` } })
      .then(r => r.json())
      .then(data => {
        const uploads = data.session?.uploads || []
        const exports = data.session?.documents || data.case?.documents || []
        setSidebarDocs({ uploads, exports })
      })
      .catch(() => {})
  }, [caseId, messages.length])

  useEffect(() => { endRef.current?.scrollIntoView({ behavior: 'smooth' }) }, [messages, isLoading])
  useEffect(() => { if (taRef.current) { taRef.current.style.height = 'auto'; taRef.current.style.height = Math.min(taRef.current.scrollHeight, 140) + 'px' } }, [input])

  // Handle chat file attachment
  const handleChatFileSelect = useCallback(async (e) => {
    const file = e.target.files?.[0]
    if (!file) return
    e.target.value = ''
    setAttachedFile(file)
    setExtracting(true)
    setExtractedText(null)
    try {
      const result = await extractFileText(file)
      setExtractedText(result)
      console.log(`[Chat] Extracted ${result.textLength} chars from ${result.filename} via ${result.method}`)
    } catch (err) {
      console.error('[Chat] Extraction failed:', err)
      setExtractedText({ error: err.message, text: '' })
    } finally {
      setExtracting(false)
    }
  }, [extractFileText])

  const removeAttachment = useCallback(() => {
    setAttachedFile(null)
    setExtractedText(null)
  }, [])

  const send = useCallback(async () => { 
    let m = input.trim()
    if ((!m && !extractedText?.text) || isLoading) return

    // Prepend extracted text if a file is attached
    if (extractedText?.text && !extractedText.error) {
      const fileLabel = attachedFile?.name || 'uploaded file'
      const prefix = `[Uploaded ${extractedText.fileType === 'pdf' ? 'PDF' : 'image'}: ${fileLabel}]\n\n--- Extracted Text ---\n${extractedText.text.slice(0, 15000)}\n--- End of Extracted Text ---\n\n`
      m = prefix + (m || 'Please analyze this document.')
    }

    if (targetLang) {
      m += `\n\n[System Request: Please respond to the above query in ${targetLang} language.]`
    }

    setInput('')
    setAttachedFile(null)
    setExtractedText(null)
    try {
      await sendChatMessage(m)
    } catch (err) {
      console.error('Failed to send message:', err)
    }
  }, [input, isLoading, sendChatMessage, extractedText, attachedFile, targetLang])

  const prompt = useCallback(async (q) => { 
    if (isLoading) return
    let finalQuery = q;
    if (targetLang) {
        finalQuery += `\n\n[System Request: Please respond to the above query in ${targetLang} language.]`
    }
    try {
      await sendChatMessage(finalQuery)
    } catch (err) {
      console.error('Failed to send message:', err)
    }
  }, [isLoading, sendChatMessage, targetLang])
  const kd = useCallback((e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send() } }, [send])

  const handleSignOut = () => {
    localStorage.removeItem('token')
    localStorage.removeItem('user')
    navigate('/login')
  }

  const toolClick = (t) => {
    if (t.id === 'voice') { setVm(true); return }
    if (t.id === 'evidence') { setEvidenceModal(true); return }
    const p = {
      consult: 'I need legal consultation about my situation. Please analyze my case and guide me step by step.',
      draft: 'Draft a legal document for my case and export it as PDF. Ask me what type of document I need (FIR, consumer complaint, RTI, legal notice, or labour complaint).',
      research: 'Find the relevant laws, IPC/CrPC/BNS sections, and legal provisions that apply to my situation. Explain them in plain language.',
      contract: 'I want to review a contract or agreement for red flags. I will paste the text. Highlight risky clauses and summarize my obligations in plain language.',
      strength: 'Analyze the strength of my case before I file a complaint. Tell me my score out of 10, what evidence I have, what is missing, and whether I should proceed.',
      rights: 'Explain my legal rights and responsibilities in my situation. What can I legally do? What protections do I have? What duties must I fulfill?',
      escalation: 'My complaint was rejected or ignored by the authority. Recommend the next authority to escalate to, the legal basis for escalation, and draft an escalation letter.',
      hearing: 'Help me prepare for my upcoming court hearing. Tell me what to bring, what to say, what questions to expect, and how to present myself.',
      summarise: 'I have multiple legal documents (court notices, letters, agreements) to summarize. I will paste them. Give me a plain-language summary of what they all mean together and what action I need to take.',
      translate: 'Translate the following legal text. I will provide the text and tell you which language I want it translated to (Hindi, Marathi, Tamil, Telugu, Bengali, etc.).',
      checklist: 'Generate a checklist of all documents, IDs, fees, and forms I need to prepare for my next legal step. Be specific about copies, attestation, and payment modes.',
    }
    prompt(p[t.id] || `Help with: ${t.label}`)
  }

  const handleFileUpload = async (e) => {
    const files = Array.from(e.target.files)
    if (!files.length) return
    setUploadingEvidence(true)
    try {
      for (const f of files) {
        const result = await uploadEvidence(f)
        setEvidenceFiles(prev => [{
          id: Date.now() + Math.random(),
          name: result.filename || f.name,
          type: f.type.startsWith('image') ? 'image' : 'pdf',
          size: f.size > 1048576 ? (f.size / 1048576).toFixed(1) + ' MB' : (f.size / 1024).toFixed(0) + ' KB',
          date: new Date().toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: 'numeric' }),
        }, ...prev])
      }
    } catch (err) {
      console.error('Evidence upload failed:', err)
    } finally {
      setUploadingEvidence(false)
      e.target.value = ''
    }
  }

  // Load evidence from server when modal opens
  useEffect(() => {
    if (evidenceModal && caseId) {
      loadEvidence().then(uploads => {
        if (uploads.length > 0) {
          setEvidenceFiles(uploads.map((u, i) => ({
            id: u.uploaded_at || i,
            name: u.filename || u.original,
            type: (u.content_type || '').startsWith('image') ? 'image' : 'pdf',
            size: u.size_bytes > 1048576 ? (u.size_bytes / 1048576).toFixed(1) + ' MB' : (u.size_bytes / 1024).toFixed(0) + ' KB',
            date: u.uploaded_at ? new Date(u.uploaded_at).toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: 'numeric' }) : '',
          })))
        }
      }).catch(() => {})
    }
  }, [evidenceModal, caseId, loadEvidence])

  const deleteEvidence = (id) => setEvidenceFiles(prev => prev.filter(f => f.id !== id))

  const deleteChat = (id, e) => { e.stopPropagation(); setChats(c => c.filter(x => x.id !== id)); if (aid === id) setAid(null) }
  const newChat = () => { navigate('/notebooks') }

  const togListen = useCallback(async () => {
    if (listening) { setListening(false); if (vt) { await sendChatMessage(vt); setVt('') } }
    else { setListening(true); setVt(''); const ch = ['I bought a defective phone...', 'My landlord is evicting me...'][Math.floor(Math.random() * 2)]; let i = 0; const iv = setInterval(() => { if (i < ch.length) { setVt(ch.slice(0, i + 1)); i++ } else clearInterval(iv) }, 40) }
  }, [listening, vt, sendChatMessage])

  const canSend = (input.trim() || (extractedText?.text && !extractedText.error)) && !isLoading && !extracting

  const inputBar = (
    <div className="flex-shrink-0 px-4 py-3" style={{ borderTop: `1px solid ${b}` }}>
      <div className="mx-auto max-w-2xl">
        {/* Attached file preview */}
        {attachedFile && (
          <div className="mb-2 flex items-center gap-2 px-3 py-2 rounded-xl" style={{ background: isDark ? 'rgba(201,168,76,0.08)' : 'rgba(201,168,76,0.06)', border: '1px solid rgba(201,168,76,0.2)' }}>
            {extracting ? (
              <Loader2 size={14} className="animate-spin flex-shrink-0" style={{ color: '#c9a84c' }} />
            ) : extractedText?.error ? (
              <X size={14} className="flex-shrink-0" style={{ color: '#ef4444' }} />
            ) : (
              <FileText size={14} className="flex-shrink-0" style={{ color: '#c9a84c' }} />
            )}
            <div className="flex-1 min-w-0">
              <p className="text-[11px] font-semibold truncate" style={{ color: 'var(--text-primary)' }}>{attachedFile.name}</p>
              <p className="text-[9px]" style={{ color: 'var(--text-muted)' }}>
                {extracting ? 'Extracting text...' : extractedText?.error ? extractedText.error : `${extractedText?.textLength || 0} chars extracted · ${extractedText?.method || ''}`}
              </p>
            </div>
            <button onClick={removeAttachment} className="flex-shrink-0 w-5 h-5 rounded-full flex items-center justify-center hover:bg-white/10" style={{ color: 'var(--text-muted)' }}><X size={10} /></button>
          </div>
        )}
        <div className="rounded-2xl p-1.5 flex items-end gap-1 shadow-lg" style={{ background: isDark ? 'rgba(18,18,18,0.9)' : 'rgba(255,255,255,0.95)', backdropFilter: 'blur(20px)', border: `1px solid ${b}` }}>
          <button onClick={() => setVm(true)} className="flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center hover:bg-white/5" style={{ color: 'var(--text-muted)' }}><Mic size={15} /></button>
          <input ref={chatFileRef} type="file" accept=".pdf,.jpg,.jpeg,.png,.bmp,.tiff,.webp,.txt" className="hidden" onChange={handleChatFileSelect} />
          <button onClick={() => chatFileRef.current?.click()} disabled={extracting} className="flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center hover:bg-white/5 transition-colors" style={{ color: attachedFile ? '#c9a84c' : 'var(--text-muted)' }} title="Attach PDF or image for analysis">
            <Paperclip size={15} />
          </button>
          <textarea ref={taRef} value={input} onChange={e => setInput(e.target.value)} onKeyDown={kd} placeholder={attachedFile ? 'Add instructions (or just send to analyze)...' : 'Ask anything about Indian law...'} rows={1} className="flex-1 text-[13px] leading-relaxed py-2 px-1.5 outline-none resize-none bg-transparent" style={{ color: 'var(--text-primary)', maxHeight: '130px' }} />
          <button onClick={send} disabled={!canSend} className="flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center transition-all"
            style={{ background: canSend ? '#c9a84c' : (isDark ? 'rgba(255,255,255,0.04)' : 'rgba(0,0,0,0.03)'), color: canSend ? '#fff' : 'var(--text-muted)', boxShadow: canSend ? '0 3px 12px rgba(201,168,76,0.4)' : 'none' }}>
            <ArrowUp size={15} />
          </button>
        </div>
        <p className="text-[9px] mt-1 text-center" style={{ color: 'var(--text-muted)' }}>AI can make mistakes. Verify legal info. 📎 Attach PDFs or images for contract analysis.</p>
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
      {/* AI Tools */}
      <div className="flex-1 overflow-y-auto px-3 py-2">
        <p className="text-[9px] font-bold uppercase tracking-widest px-2 mb-2 mt-1" style={{ color: 'var(--text-muted)' }}>AI Tools</p>
        <div className="grid grid-cols-2 gap-2">
          {tools.map(t => (
            <button key={t.id} onClick={() => toolClick(t)} className="group flex flex-col items-center rounded-2xl p-2.5 text-center transition-all hover:scale-[1.03] hover:shadow-md" style={{ background: isDark ? 'rgba(255,255,255,0.03)' : 'rgba(0,0,0,0.02)', border: `1px solid ${b}` }}>
              <t.icon size={16} className="mb-1.5 transition-colors group-hover:text-[#c9a84c]" style={{ color: 'var(--text-secondary)' }} />
              <span className="text-[10px] font-bold leading-tight" style={{ color: 'var(--text-primary)' }}>{t.label}</span>
              <span className="text-[8px] mt-0.5" style={{ color: 'var(--text-muted)' }}>{t.desc}</span>
            </button>
          ))}
        </div>
      </div>

      {/* Sources & Documents */}
      {(sidebarDocs.uploads.length > 0 || sidebarDocs.exports.length > 0) && (
        <div className="flex-shrink-0 px-3 py-2" style={{ borderTop: `1px solid ${b}` }}>
          <p className="text-[9px] font-bold uppercase tracking-widest px-2 mb-2 mt-1" style={{ color: 'var(--text-muted)' }}>Sources & Documents</p>
          <div className="space-y-1 max-h-40 overflow-y-auto">
            {sidebarDocs.exports.map((d, i) => (
              <button key={`exp-${i}`} onClick={() => downloadDocument(d.filename)}
                className="w-full flex items-center gap-2 px-2.5 py-2 rounded-lg text-left transition-all hover:bg-white/5 group"
                style={{ background: isDark ? 'rgba(201,168,76,0.06)' : 'rgba(201,168,76,0.04)' }}>
                <FileText size={12} style={{ color: '#c9a84c', flexShrink: 0 }} />
                <div className="min-w-0 flex-1">
                  <p className="text-[10px] font-semibold truncate" style={{ color: 'var(--text-primary)' }}>{d.filename}</p>
                  <p className="text-[8px]" style={{ color: 'var(--text-muted)' }}>{d.format?.toUpperCase() || 'DOC'} · Exported</p>
                </div>
                <Download size={10} className="opacity-0 group-hover:opacity-100 transition-opacity" style={{ color: '#c9a84c' }} />
              </button>
            ))}
            {sidebarDocs.uploads.map((u, i) => (
              <button key={`upl-${i}`} onClick={() => downloadEvidence(u.filename)}
                className="w-full flex items-center gap-2 px-2.5 py-2 rounded-lg text-left transition-all hover:bg-white/5 group">
                {(u.content_type || '').startsWith('image')
                  ? <Image size={12} style={{ color: '#3b82f6', flexShrink: 0 }} />
                  : <File size={12} style={{ color: '#ef4444', flexShrink: 0 }} />}
                <div className="min-w-0 flex-1">
                  <p className="text-[10px] font-semibold truncate" style={{ color: 'var(--text-primary)' }}>{u.filename || u.original}</p>
                  <p className="text-[8px]" style={{ color: 'var(--text-muted)' }}>{u.size_bytes ? (u.size_bytes > 1048576 ? (u.size_bytes / 1048576).toFixed(1) + ' MB' : Math.round(u.size_bytes / 1024) + ' KB') : ''} · Uploaded</p>
                </div>
                <Download size={10} className="opacity-0 group-hover:opacity-100 transition-opacity" style={{ color: 'var(--text-muted)' }} />
              </button>
            ))}
          </div>
        </div>
      )}

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
                      <button onClick={() => downloadEvidence(f.name)} className="opacity-0 group-hover:opacity-100 transition-opacity p-1.5 rounded-lg hover:bg-blue-500/10" style={{ color: 'var(--text-muted)' }} title="Download"><Download size={12} /></button>
                      <button onClick={() => deleteEvidence(f.id)} className="opacity-0 group-hover:opacity-100 transition-opacity p-1.5 rounded-lg hover:bg-red-500/10" style={{ color: 'var(--text-muted)' }} title="Delete"><Trash2 size={12} /></button>
                    </div>
                  ))}
                </div>
              )}
            </div>
            <div className="flex-shrink-0 px-5 py-4" style={{ borderTop: `1px solid ${b}` }}>
              <input ref={fileInputRef} type="file" multiple accept=".pdf,.jpg,.jpeg,.png,.doc,.docx" className="hidden" onChange={handleFileUpload} />
              <button onClick={() => fileInputRef.current?.click()} disabled={uploadingEvidence} className="w-full flex items-center justify-center gap-2 rounded-xl py-3 transition-all hover:scale-[1.01] hover:shadow-md disabled:opacity-50 disabled:cursor-not-allowed"
                style={{ background: isDark ? 'rgba(201,168,76,0.1)' : 'rgba(201,168,76,0.08)', border: '1px dashed rgba(201,168,76,0.3)', color: '#c9a84c' }}>
                <Upload size={16} className={uploadingEvidence ? 'animate-pulse' : ''} />
                <span className="text-[12px] font-bold">{uploadingEvidence ? 'Uploading...' : 'Upload Evidence'}</span>
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
            {!rp && <button onClick={() => setRp(true)} className="w-7 h-7 rounded-lg flex items-center justify-center transition-all hover:bg-white/5" style={{ color: 'var(--text-secondary)' }} title="Open Translation Panel"><PanelRightOpen size={14} /></button>}
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
                {messages.filter(msg => msg.role === 'user' || msg.content).map((msg, i) => (
                  <div key={i} className={`flex w-full ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                    {msg.role === 'assistant' && <div className="flex-shrink-0 w-7 h-7 rounded-full flex items-center justify-center mr-2.5 mt-1" style={{ background: isDark ? '#151515' : '#fff', border: `1px solid ${b}` }}><Scale size={12} style={{ color: isDark ? '#fff' : '#111' }} /></div>}
                    <div className={`max-w-[80%] flex flex-col ${msg.role === 'user' ? 'items-end' : 'items-start'}`}>
                      <div className={`px-4 py-3 text-[13px] leading-relaxed ${msg.role === 'user' ? 'rounded-2xl rounded-tr-sm' : 'rounded-2xl rounded-tl-sm'}`}
                        style={msg.role === 'user' ? { background: isDark ? '#1a1a1a' : '#111', color: '#fff' } : { background: isDark ? 'rgba(255,255,255,0.03)' : 'rgba(0,0,0,0.02)', border: `1px solid ${b}`, color: 'var(--text-primary)' }}>
                        {msg.role === 'user'
                          ? msg.content.replace(/\n\n\[System Request: Please respond to the above query in .* language\.\]/g, '')
                          : <MarkdownMessage content={msg.content} isDark={isDark} />
                        }
                      </div>
                      {/* Thinking panel — only for assistant messages with steps */}
                      {msg.role === 'assistant' && msg.steps?.length > 0 && (
                        <ThinkingPanel steps={msg.steps} isDark={isDark} />
                      )}
                    </div>
                    {msg.role === 'user' && <div className="flex-shrink-0 w-7 h-7 rounded-full flex items-center justify-center ml-2.5 mt-1" style={{ background: isDark ? '#1a1a1a' : '#eee' }}><User size={12} style={{ color: 'var(--text-muted)' }} /></div>}
                  </div>
                ))}
                {isLoading && (
                  <div className="flex justify-start">
                    <div className="flex-shrink-0 w-7 h-7 rounded-full flex items-center justify-center mr-2.5 mt-1" style={{ background: isDark ? '#151515' : '#fff', border: `1px solid ${b}` }}>
                      <Scale size={12} style={{ color: isDark ? '#fff' : '#111' }} />
                    </div>
                    <div className="rounded-2xl rounded-tl-sm px-4 py-3" style={{ background: isDark ? 'rgba(255,255,255,0.03)' : 'rgba(0,0,0,0.02)', border: `1px solid ${b}` }}>
                      <div className="flex items-center gap-2">
                        <div className="flex gap-1">
                          {[0, 150, 300].map(d => <span key={d} className="w-1.5 h-1.5 rounded-full bg-[#c9a84c] animate-bounce" style={{ animationDelay: `${d}ms` }} />)}
                        </div>
                        {/* Show last tool being called */}
                        {messages.length > 0 && messages[messages.length - 1]?.steps?.length > 0 && (() => {
                          const lastSteps = messages[messages.length - 1].steps
                          const lastTool = [...lastSteps].reverse().find(s => s.type === 'tool')
                          return lastTool ? (
                            <span className="text-[9px] font-semibold px-1.5 py-0.5 rounded-full" style={{ background: `${toolColor(lastTool.name)}15`, color: toolColor(lastTool.name) }}>
                              {toolLabel(lastTool.name)}
                            </span>
                          ) : null
                        })()}
                      </div>
                    </div>
                  </div>
                )}
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
            <h3 className="text-[11px] font-bold uppercase tracking-wider" style={{ color: 'var(--text-muted)' }}>Response Language</h3>
            <button onClick={() => setRp(false)} className="w-6 h-6 rounded-lg flex items-center justify-center hover:bg-white/5" style={{ color: 'var(--text-muted)' }}><X size={12} /></button>
          </div>
          <div className="flex-1 overflow-y-auto px-3 py-3">
            <div className="grid grid-cols-2 gap-2">
              {languages.map(l => {
                const isActive = targetLang === l.name;
                return (
                  <button key={l.code} onClick={() => setTargetLang(l.name)} className="group flex flex-col items-center rounded-2xl p-3 text-center transition-all hover:scale-[1.03]" style={{ background: isActive ? 'rgba(201,168,76,0.1)' : (isDark ? 'rgba(255,255,255,0.03)' : 'rgba(0,0,0,0.02)'), border: `1px solid ${isActive ? '#c9a84c' : b}`, boxShadow: isActive ? '0 4px 12px rgba(201,168,76,0.15)' : 'none' }}>
                    <span className="text-xl mb-1.5">{l.flag}</span>
                    <span className="text-[11px] font-bold leading-tight" style={{ color: isActive ? '#c9a84c' : 'var(--text-primary)' }}>{l.name}</span>
                    <span className="text-[9px] mt-0.5" style={{ color: isActive ? 'rgba(201,168,76,0.8)' : 'var(--text-muted)' }}>{l.native}</span>
                  </button>
                )
              })}
            </div>
          </div>
          <div className="flex-shrink-0 px-3 py-3" style={{ borderTop: `1px solid ${b}` }}>
            <div className="rounded-xl p-3" style={{ background: isDark ? 'rgba(59,130,246,0.06)' : 'rgba(59,130,246,0.05)', border: '1px solid rgba(59,130,246,0.12)' }}>
              <p className="text-[10px] font-bold mb-0.5 flex items-center gap-1.5" style={{ color: '#3b82f6' }}><Languages size={10} /> How to use</p>
              <p className="text-[9px] leading-relaxed" style={{ color: 'var(--text-muted)' }}>Select a language and all future responses will be translated automatically.</p>
            </div>
          </div>
        </aside>
      )}
    </div>
  )
}

export default DashboardPage
