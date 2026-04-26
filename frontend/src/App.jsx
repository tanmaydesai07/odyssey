import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import './App.css'
import AppLayout from './componts/AppLayout'
import ProtectedRoute from './componts/ProtectedRoute'
import { LegalProvider } from './componts/LegalDataContext'
import { ThemeProvider } from './ThemeContext'
import LandingPage from './pages/LandingPage'
import LoginPage from './pages/LoginPage'
import NotebooksPage from './pages/NotebooksPage'
import DashboardPage from './pages/DashboardPage'
import NotFoundPage from './pages/NotFoundPage'

function App() {
  return (
    <ThemeProvider>
      <LegalProvider>
        <BrowserRouter>
          <Routes>
            {/* Landing page with top nav */}
            <Route element={<AppLayout />}>
              <Route path="/" element={<LandingPage />} />
              <Route path="/login" element={<LoginPage />} />
              <Route path="/home" element={<Navigate to="/" replace />} />
              <Route path="*" element={<NotFoundPage />} />
            </Route>
            {/* Notebooks — grid view of all cases, protected */}
            <Route
              path="/notebooks"
              element={
                <ProtectedRoute>
                  <NotebooksPage />
                </ProtectedRoute>
              }
            />
            {/* Dashboard — full-screen, no top nav, protected */}
            <Route
              path="/dashboard/:caseId?"
              element={
                <ProtectedRoute>
                  <DashboardPage />
                </ProtectedRoute>
              }
            />
          </Routes>
        </BrowserRouter>
      </LegalProvider>
    </ThemeProvider>
  )
}

export default App
