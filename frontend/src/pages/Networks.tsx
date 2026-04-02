import { useEffect, useState } from 'react'
import api from '../api'

const NETWORK_TYPES = ['hasoffers', 'everflow', 'custom']

interface TestResult { ok: boolean; message: string; loading: boolean }

export default function Networks() {
  const [networks, setNetworks] = useState<any[]>([])
  const [accounts, setAccounts] = useState<any[]>([])
  const [showNetForm, setShowNetForm] = useState(false)
  const [showAccForm, setShowAccForm] = useState(false)
  const [netForm, setNetForm] = useState({ name: '', network_type: 'hasoffers' })
  const [accForm, setAccForm] = useState({
    network_id: 0, label: '', api_key: '', api_base_url: '',
    network_id_value: '', access_mode: 'affiliate',
  })
  const [testResults, setTestResults] = useState<Record<number, TestResult>>({})

  const load = async () => {
    const [n, a] = await Promise.all([api.get('/affiliates/networks'), api.get('/affiliates/accounts')])
    setNetworks(n.data)
    setAccounts(a.data)
  }
  useEffect(() => { load() }, [])

  const selectedNetworkType = networks.find(n => n.id === accForm.network_id)?.type || 'hasoffers'
  const isHasOffers = selectedNetworkType === 'hasoffers'

  const createNetwork = async () => {
    await api.post('/affiliates/networks', netForm)
    setShowNetForm(false)
    setNetForm({ name: '', network_type: 'hasoffers' })
    load()
  }

  const createAccount = async () => {
    const config: Record<string, any> = {}
    if (isHasOffers) {
      config.access_mode = accForm.access_mode
    }
    await api.post('/affiliates/accounts', {
      network_id: accForm.network_id,
      label: accForm.label,
      api_key: accForm.api_key,
      api_base_url: accForm.api_base_url,
      network_id_value: accForm.network_id_value,
      config_json: config,
    })
    setShowAccForm(false)
    setAccForm({ network_id: 0, label: '', api_key: '', api_base_url: '', network_id_value: '', access_mode: 'affiliate' })
    load()
  }

  const deleteNetwork = async (id: number) => {
    if (!confirm('Delete this network?')) return
    await api.delete(`/affiliates/networks/${id}`)
    load()
  }

  const deleteAccount = async (id: number) => {
    if (!confirm('Delete this account?')) return
    await api.delete(`/affiliates/accounts/${id}`)
    load()
  }

  const testConnection = async (id: number) => {
    setTestResults(r => ({ ...r, [id]: { ok: false, message: '', loading: true } }))
    try {
      const res = await api.get(`/affiliates/accounts/${id}/test`)
      setTestResults(r => ({ ...r, [id]: { ok: res.data.ok, message: res.data.message, loading: false } }))
    } catch (e: any) {
      setTestResults(r => ({ ...r, [id]: { ok: false, message: e.response?.data?.detail || e.message, loading: false } }))
    }
  }

  const getNetworkName = (id: number) => networks.find(n => n.id === id)?.name || `Network ${id}`
  const getNetworkType = (id: number) => networks.find(n => n.id === id)?.type || ''

  return (
    <div className="space-y-6">
      <h1 className="text-xl font-bold text-white">Affiliate Networks</h1>

      {/* Networks */}
      <div className="bg-gray-900 rounded-xl border border-gray-800 overflow-hidden">
        <div className="px-4 py-3 border-b border-gray-800 flex items-center justify-between">
          <span className="text-gray-400 text-sm font-medium">Networks</span>
          <button onClick={() => setShowNetForm(!showNetForm)} className="text-green-400 text-sm hover:text-green-300">+ Add Network</button>
        </div>
        {showNetForm && (
          <div className="px-4 py-3 bg-gray-800/50 border-b border-gray-700 flex flex-wrap gap-2 items-end">
            <input className="bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white w-40 focus:outline-none focus:border-green-500" placeholder="Display name" value={netForm.name} onChange={e => setNetForm({...netForm, name: e.target.value})} />
            <select className="bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white" value={netForm.network_type} onChange={e => setNetForm({...netForm, network_type: e.target.value})}>
              {NETWORK_TYPES.map(t => <option key={t} value={t}>{t}</option>)}
            </select>
            <button onClick={createNetwork} className="bg-green-500 text-black px-4 py-2 rounded-lg text-sm font-medium hover:bg-green-400">Save</button>
            <button onClick={() => setShowNetForm(false)} className="text-gray-500 text-sm">Cancel</button>
          </div>
        )}
        <div className="divide-y divide-gray-800">
          {networks.map(n => (
            <div key={n.id} className="flex items-center justify-between px-4 py-3">
              <div>
                <span className="text-white text-sm font-medium">{n.name}</span>
                <span className="ml-2 px-2 py-0.5 rounded-full bg-blue-500/20 text-blue-400 text-xs">{n.type}</span>
              </div>
              <button onClick={() => deleteNetwork(n.id)} className="text-gray-600 hover:text-red-400 text-sm">Remove</button>
            </div>
          ))}
          {networks.length === 0 && <div className="text-gray-500 text-sm text-center py-6">No networks yet</div>}
        </div>
      </div>

      {/* Accounts */}
      <div className="bg-gray-900 rounded-xl border border-gray-800 overflow-hidden">
        <div className="px-4 py-3 border-b border-gray-800 flex items-center justify-between">
          <span className="text-gray-400 text-sm font-medium">Accounts</span>
          <button onClick={() => setShowAccForm(!showAccForm)} className="text-green-400 text-sm hover:text-green-300">+ Add Account</button>
        </div>

        {showAccForm && (
          <div className="px-4 py-3 bg-gray-800/50 border-b border-gray-700 space-y-4">
            {/* Row 1: Network + Label */}
            <div className="flex flex-wrap gap-3">
              <div className="flex flex-col gap-1">
                <label className="text-gray-500 text-xs">Network *</label>
                <select className="bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white" value={accForm.network_id} onChange={e => setAccForm({...accForm, network_id: parseInt(e.target.value)})}>
                  <option value={0}>Select Network</option>
                  {networks.map(n => <option key={n.id} value={n.id}>{n.name} ({n.type})</option>)}
                </select>
              </div>
              <div className="flex flex-col gap-1">
                <label className="text-gray-500 text-xs">Label *</label>
                <input className="bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white w-36 focus:outline-none focus:border-green-500" placeholder="e.g. Main Account" value={accForm.label} onChange={e => setAccForm({...accForm, label: e.target.value})} />
              </div>
              {isHasOffers && (
                <div className="flex flex-col gap-1">
                  <label className="text-gray-500 text-xs">Access Mode</label>
                  <select className="bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white" value={accForm.access_mode} onChange={e => setAccForm({...accForm, access_mode: e.target.value})}>
                    <option value="affiliate">Affiliate (most users)</option>
                    <option value="network">Network Admin</option>
                  </select>
                </div>
              )}
            </div>

            {/* Row 2: Credentials */}
            <div className="flex flex-wrap gap-3">
              <div className="flex flex-col gap-1">
                <label className="text-gray-500 text-xs">
                  {isHasOffers ? 'Network ID *' : 'Network ID (optional)'}
                </label>
                <input
                  className={`bg-gray-800 border rounded-lg px-3 py-2 text-sm text-white w-44 focus:outline-none focus:border-green-500 ${isHasOffers ? 'border-yellow-600/40' : 'border-gray-700'}`}
                  placeholder={isHasOffers ? 'e.g. neptuneads' : 'Optional'}
                  value={accForm.network_id_value}
                  onChange={e => setAccForm({...accForm, network_id_value: e.target.value})}
                />
                {isHasOffers && <span className="text-yellow-600/70 text-xs">From your dashboard URL: neptuneads.hasoffers.com</span>}
              </div>

              <div className="flex flex-col gap-1">
                <label className="text-gray-500 text-xs">
                  {isHasOffers ? (accForm.access_mode === 'affiliate' ? 'API Key * (Tools → APIs in your dashboard)' : 'Network Token *') : 'API Key *'}
                </label>
                <input
                  className="bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white w-72 focus:outline-none focus:border-green-500 font-mono text-xs"
                  placeholder="Paste token here"
                  value={accForm.api_key}
                  onChange={e => setAccForm({...accForm, api_key: e.target.value})}
                />
              </div>
            </div>

            <div className="flex gap-2 items-center">
              <button onClick={createAccount} className="bg-green-500 text-black px-4 py-2 rounded-lg text-sm font-medium hover:bg-green-400">Save Account</button>
              <button onClick={() => setShowAccForm(false)} className="text-gray-500 text-sm">Cancel</button>
            </div>
          </div>
        )}

        <div className="divide-y divide-gray-800">
          {accounts.map(a => (
            <div key={a.id} className="px-4 py-3">
              <div className="flex items-start justify-between gap-2">
                <div className="flex-1 min-w-0">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="text-white text-sm font-medium">{a.label}</span>
                    <span className="text-gray-500 text-xs">{getNetworkName(a.network_id)}</span>
                    <span className="px-1.5 py-0.5 rounded bg-gray-800 text-gray-500 text-xs">{getNetworkType(a.network_id)}</span>
                    {a.network_id_value && <span className="text-yellow-600/70 text-xs font-mono">ID: {a.network_id_value}</span>}
                  </div>
                  {testResults[a.id] && (
                    <div className={`mt-1.5 text-xs px-2 py-1 rounded-lg inline-block ${testResults[a.id].loading ? 'text-gray-500' : testResults[a.id].ok ? 'text-green-400 bg-green-500/10' : 'text-red-400 bg-red-500/10'}`}>
                      {testResults[a.id].loading ? '⟳ Testing...' : testResults[a.id].ok ? `✓ ${testResults[a.id].message}` : `✗ ${testResults[a.id].message}`}
                    </div>
                  )}
                </div>
                <div className="flex items-center gap-3 shrink-0">
                  <button onClick={() => testConnection(a.id)} className="text-blue-400 hover:text-blue-300 text-xs font-medium border border-blue-500/30 px-2 py-1 rounded-lg hover:border-blue-400/50 transition">
                    Test
                  </button>
                  <button onClick={() => deleteAccount(a.id)} className="text-gray-600 hover:text-red-400 text-sm">Remove</button>
                </div>
              </div>
            </div>
          ))}
          {accounts.length === 0 && <div className="text-gray-500 text-sm text-center py-6">No accounts yet</div>}
        </div>
      </div>
    </div>
  )
}
