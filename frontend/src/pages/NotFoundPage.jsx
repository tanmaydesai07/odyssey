import { Home } from 'lucide-react'
import { Link } from 'react-router-dom'

const NotFoundPage = () => {
  return (
    <div className="mx-auto flex min-h-[60vh] w-full max-w-3xl items-center justify-center">
      <section className="bento px-8 py-10 text-center">
        <p className="text-6xl font-extrabold" style={{ color: 'var(--text-primary)' }}>404</p>
        <h1 className="mt-2 text-2xl font-extrabold" style={{ color: 'var(--text-primary)' }}>Page not found</h1>
        <p className="mt-2 text-sm" style={{ color: 'var(--text-secondary)' }}>
          The page you're looking for doesn't exist.
        </p>
        <Link to="/" className="btn-accent mt-6">
          <Home size={16} />
          Back to Home
        </Link>
      </section>
    </div>
  )
}

export default NotFoundPage
