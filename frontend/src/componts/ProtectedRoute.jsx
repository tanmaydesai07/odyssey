import { Navigate } from 'react-router-dom'

/**
 * Wraps a route and redirects to /login if no JWT token is found in localStorage.
 */
const ProtectedRoute = ({ children }) => {
  const token = localStorage.getItem('token')
  if (!token) return <Navigate to="/login" replace />
  return children
}

export default ProtectedRoute
