import { Link, useLocation, useNavigate } from 'react-router-dom'

const nav = [
  { path: '/', label: 'Dashboard', icon: '📊' },
  { path: '/offers', label: 'Offers', icon: '🔍' },
  { path: '/campaigns', label: 'Campaigns', icon: '🎯' },
  { path: '/networks', label: 'Networks', icon: '🔗' },
  { path: '/subids', label: 'Sub-IDs', icon: '🔑' },
  { path: '/mailing', label: 'Mailing', icon: '✉️' },
  { path: '/suggestions', label: 'AI Suggestions', icon: '🤖' },
  { path: '/schedule', label: 'Schedule', icon: '📅' },
]

export default function Layout({ children }: { children: React.ReactNode }) {
  const location = useLocation()
  const navigate = useNavigate()
  const role = localStorage.getItem('role')

  const logout = () => {
    localStorage.removeItem('token')
    localStorage.removeItem('role')
    navigate('/login')
  }

  return (
    <div className="min-h-screen bg-gray-950 flex">
      {/* Sidebar */}
      <aside className="hidden md:flex flex-col w-56 bg-gray-900 border-r border-gray-800 p-4">
        <div className="text-green-400 font-bold text-lg mb-8 px-2">Stats Tool</div>
        <nav className="flex-1 space-y-1">
          {nav.filter(n => role === 'admin' || n.path === '/').map(({ path, label, icon }) => (
            <Link
              key={path}
              to={path}
              className={`flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition ${
                location.pathname === path
                  ? 'bg-green-500/20 text-green-400 font-medium'
                  : 'text-gray-400 hover:bg-gray-800 hover:text-white'
              }`}
            >
              <span>{icon}</span>{label}
            </Link>
          ))}
        </nav>
        <button onClick={logout} className="text-gray-500 hover:text-white text-sm px-3 py-2 rounded-lg hover:bg-gray-800 text-left transition">
          Sign Out
        </button>
      </aside>

      {/* Mobile top bar */}
      <div className="md:hidden fixed top-0 left-0 right-0 bg-gray-900 border-b border-gray-800 z-50 px-4 py-3 flex items-center justify-between">
        <span className="text-green-400 font-bold">Stats Tool</span>
        <div className="flex gap-1">
          {nav.filter(n => role === 'admin' || n.path === '/').slice(0, 5).map(({ path, icon }) => (
            <Link
              key={path}
              to={path}
              className={`p-2 rounded-lg text-lg ${location.pathname === path ? 'bg-green-500/20' : ''}`}
            >
              {icon}
            </Link>
          ))}
        </div>
      </div>

      {/* Main content */}
      <main className="flex-1 p-4 md:p-6 mt-14 md:mt-0 overflow-auto">
        {children}
      </main>
    </div>
  )
}
