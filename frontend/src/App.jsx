import { Routes, Route, Navigate } from "react-router-dom"
import { AuthProvider, useAuth } from "./context/AuthContext.jsx"
import Navbar from "./components/Navbar.jsx"
import InteractiveBackground from "./components/InteractiveBackground.jsx"
import Upload from "./pages/Upload.jsx"
import Report from "./pages/Report.jsx"
import Dashboard from "./pages/Dashboard.jsx"
import Login from "./pages/Login.jsx"
import About from "./pages/About.jsx"

function ProtectedRoute({ children }) {
  const { session, loading } = useAuth()
  if (loading) {
    return (
      <div className="flex min-h-[calc(100vh-69px)] items-center justify-center">
        <div className="text-muted">Loading...</div>
      </div>
    )
  }
  if (!session) return <Navigate to="/" replace />
  return children
}

export default function App() {
  return (
    <AuthProvider>
      <div className="bg-grid relative min-h-screen font-sans text-foreground">
        <InteractiveBackground />
        <Navbar />
        <Routes>
          <Route path="/" element={<Login />} />
          <Route path="/login" element={<Navigate to="/" replace />} />
          <Route path="/signup" element={<Navigate to="/" replace />} />
          <Route path="/upload" element={<ProtectedRoute><Upload /></ProtectedRoute>} />
          <Route path="/report/:contractId" element={<ProtectedRoute><Report /></ProtectedRoute>} />
          <Route path="/dashboard" element={<ProtectedRoute><Dashboard /></ProtectedRoute>} />
          <Route path="/about" element={<ProtectedRoute><About /></ProtectedRoute>} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </div>
    </AuthProvider>
  )
}
