import { Routes, Route, Navigate } from "react-router-dom"
import Navbar from "./components/Navbar.jsx"
import InteractiveBackground from "./components/InteractiveBackground.jsx"
import Upload from "./pages/Upload.jsx"
import Report from "./pages/Report.jsx"
import Dashboard from "./pages/Dashboard.jsx"

export default function App() {
  return (
    <div className="bg-grid relative min-h-screen font-sans text-foreground">
      <InteractiveBackground />
      <Navbar />
      <Routes>
        <Route path="/" element={<Upload />} />
        <Route path="/upload" element={<Navigate to="/" replace />} />
        <Route path="/report/:contractId" element={<Report />} />
        <Route path="/dashboard" element={<Dashboard />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </div>
  )
}
