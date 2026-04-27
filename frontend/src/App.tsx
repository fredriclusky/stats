import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import Login from './pages/Login'
import Layout from './components/Layout'
import Dashboard from './pages/Dashboard'
import Campaigns from './pages/Campaigns'
import Networks from './pages/Networks'
import SubIDs from './pages/SubIDs'
import Mailing from './pages/Mailing'
import Suggestions from './pages/Suggestions'
import Schedule from './pages/Schedule'
import OfferIntelligence from './pages/OfferIntelligence'
import PartnerView from './pages/PartnerView'
import KarlinStats from './pages/KarlinStats'

function RequireAuth({ children }: { children: React.ReactNode }) {
  const token = localStorage.getItem('token')
  if (!token) return <Navigate to="/login" replace />
  return <>{children}</>
}

function RequireAdmin({ children }: { children: React.ReactNode }) {
  const role = localStorage.getItem('role')
  if (role !== 'admin') return <Navigate to="/karlin" replace />
  return <>{children}</>
}

function HomeRoute() {
  const role = localStorage.getItem('role')
  if (role === 'partner') return <Navigate to="/karlin" replace />
  return <Layout><Dashboard /></Layout>
}

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route path="/karlin" element={<RequireAuth><KarlinStats /></RequireAuth>} />
        <Route path="/partner" element={<RequireAuth><PartnerView /></RequireAuth>} />
        <Route path="/" element={<RequireAuth><HomeRoute /></RequireAuth>} />
        <Route path="/campaigns" element={<RequireAuth><RequireAdmin><Layout><Campaigns /></Layout></RequireAdmin></RequireAuth>} />
        <Route path="/networks" element={<RequireAuth><RequireAdmin><Layout><Networks /></Layout></RequireAdmin></RequireAuth>} />
        <Route path="/subids" element={<RequireAuth><RequireAdmin><Layout><SubIDs /></Layout></RequireAdmin></RequireAuth>} />
        <Route path="/mailing" element={<RequireAuth><RequireAdmin><Layout><Mailing /></Layout></RequireAdmin></RequireAuth>} />
        <Route path="/suggestions" element={<RequireAuth><RequireAdmin><Layout><Suggestions /></Layout></RequireAdmin></RequireAuth>} />
        <Route path="/offers" element={<RequireAuth><RequireAdmin><Layout><OfferIntelligence /></Layout></RequireAdmin></RequireAuth>} />
        <Route path="/schedule" element={<RequireAuth><RequireAdmin><Layout><Schedule /></Layout></RequireAdmin></RequireAuth>} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  )
}
