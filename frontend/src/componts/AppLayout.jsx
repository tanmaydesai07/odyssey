import { Outlet } from 'react-router-dom'
import TopNav from './TopNav'

const AppLayout = () => {
  return (
    <div className="min-h-screen" style={{ background: 'var(--bg-primary)', color: 'var(--text-primary)' }}>
      <TopNav />
      <main className="px-4 pt-[5rem] sm:px-6 lg:px-10 pb-6">
        <Outlet />
      </main>
    </div>
  )
}

export default AppLayout
