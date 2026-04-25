import { Scale } from 'lucide-react'
import { Link } from 'react-router-dom'

const FooterBar = () => {
  return (
    <footer className="px-4 pb-6 pt-8 sm:px-6 lg:px-10">
      <div className="mx-auto max-w-6xl rounded-2xl px-6 py-5 flex flex-col items-center justify-between gap-4 text-center sm:flex-row sm:text-left"
        style={{ background: 'var(--bg-secondary)', border: '1px solid var(--border)' }}>
        <div className="flex items-center gap-2.5">
          <span className="inline-flex h-7 w-7 items-center justify-center rounded-lg text-white" style={{ background: '#0a0a0a' }}>
            <Scale size={13} />
          </span>
          <p className="font-['Sora'] text-sm font-bold" style={{ color: 'var(--text-primary)' }}>NyayaMitr</p>
          <span className="text-xs font-medium" style={{ color: 'var(--text-muted)' }}>· AI Legal Assistance</span>
        </div>
        <div className="flex items-center gap-5 text-sm font-semibold" style={{ color: 'var(--text-muted)' }}>
          <Link to="/consult" className="transition-colors hover:text-[var(--text-primary)]">Consult</Link>
          <Link to="/analysis" className="transition-colors hover:text-[var(--text-primary)]">Case Analysis</Link>
          <Link to="/documents" className="transition-colors hover:text-[var(--text-primary)]">Documents</Link>
        </div>
      </div>
    </footer>
  )
}

export default FooterBar
