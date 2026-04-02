import { useEffect, useState } from 'react'
import api from '../api'

export default function Campaigns() {
  const [campaigns, setCampaigns] = useState<any[]>([])
  const [accounts, setAccounts] = useState<any[]>([])
  const [mappings, setMappings] = useState<Record<number, any[]>>({})
  const [showForm, setShowForm] = useState(false)
  const [showMapForm, setShowMapForm] = useState<number | null>(null)
  const [form, setForm] = useState({ name: '', notes: '', tags: '' })
  const [mapForm, setMapForm] = useState({ campaign_id: 0, account_id: 0, network_campaign_id: '', network_campaign_name: '' })

  // Discover panel state
  const [discoverAccount, setDiscoverAccount] = useState<number>(0)
  const [discovered, setDiscovered] = useState<any[]>([])
  const [discovering, setDiscovering] = useState(false)
  const [discoverError, setDiscoverError] = useState('')
  const [quickMap, setQuickMap] = useState<Record<string, number>>({}) // network_id → campaign_id

  const load = async () => {
    const [c, a] = await Promise.all([api.get('/campaigns'), api.get('/affiliates/accounts')])
    setCampaigns(c.data)
    setAccounts(a.data)
  }
  useEffect(() => { load() }, [])

  const loadMappings = async (cid: number) => {
    if (mappings[cid] !== undefined) {
      setMappings(m => { const n = { ...m }; delete n[cid]; return n })
      return
    }
    const res = await api.get(`/campaigns/${cid}/mappings`)
    setMappings(m => ({ ...m, [cid]: res.data }))
  }

  const createCampaign = async () => {
    await api.post('/campaigns', form)
    setShowForm(false)
    setForm({ name: '', notes: '', tags: '' })
    load()
  }

  const createMapping = async () => {
    await api.post('/campaigns/mappings', mapForm)
    setShowMapForm(null)
    const res = await api.get(`/campaigns/${mapForm.campaign_id}/mappings`)
    setMappings(m => ({ ...m, [mapForm.campaign_id]: res.data }))
  }

  const deleteMapping = async (mid: number, cid: number) => {
    if (!confirm('Remove this mapping?')) return
    await api.delete(`/campaigns/mappings/${mid}`)
    const res = await api.get(`/campaigns/${cid}/mappings`)
    setMappings(m => ({ ...m, [cid]: res.data }))
  }

  const discoverCampaigns = async () => {
    if (!discoverAccount) return
    setDiscovering(true)
    setDiscoverError('')
    setDiscovered([])
    try {
      const res = await api.get(`/campaigns/discover/${discoverAccount}`)
      setDiscovered(res.data)
    } catch (e: any) {
      setDiscoverError(e.response?.data?.detail || e.message)
    } finally {
      setDiscovering(false)
    }
  }

  const quickMapCampaign = async (networkCampaign: any) => {
    const selectedCampaignId = quickMap[networkCampaign.id]
    if (!selectedCampaignId && selectedCampaignId !== 0) return
    // If 0, create a new canonical campaign with the network campaign name
    let cid = selectedCampaignId
    if (cid === 0) {
      const res = await api.post('/campaigns', { name: networkCampaign.name })
      cid = res.data.id
      await load()
    }
    await api.post('/campaigns/mappings', {
      campaign_id: cid,
      account_id: discoverAccount,
      network_campaign_id: networkCampaign.id,
      network_campaign_name: networkCampaign.name,
    })
    setDiscovered(d => d.map(c => c.id === networkCampaign.id ? { ...c, already_mapped: true } : c))
    load()
  }

  const getAccountLabel = (id: number) => accounts.find(a => a.id === id)?.label || `Account ${id}`

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-bold text-white">Campaigns</h1>
        <button onClick={() => setShowForm(!showForm)} className="bg-green-500 text-black px-4 py-2 rounded-lg text-sm font-medium hover:bg-green-400">+ New Campaign</button>
      </div>

      {showForm && (
        <div className="bg-gray-900 rounded-xl border border-gray-800 p-4 space-y-3">
          <div className="text-gray-400 text-sm font-medium">Create Canonical Campaign</div>
          <input className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-green-500" placeholder="Campaign name" value={form.name} onChange={e => setForm({...form, name: e.target.value})} />
          <input className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-green-500" placeholder="Notes (optional)" value={form.notes} onChange={e => setForm({...form, notes: e.target.value})} />
          <input className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-green-500" placeholder="Tags (comma separated)" value={form.tags} onChange={e => setForm({...form, tags: e.target.value})} />
          <div className="flex gap-2">
            <button onClick={createCampaign} className="bg-green-500 text-black px-4 py-2 rounded-lg text-sm font-medium hover:bg-green-400">Save</button>
            <button onClick={() => setShowForm(false)} className="text-gray-500 text-sm">Cancel</button>
          </div>
        </div>
      )}

      {/* Discover from Network */}
      <div className="bg-gray-900 rounded-xl border border-gray-800 overflow-hidden">
        <div className="px-4 py-3 border-b border-gray-800">
          <div className="text-gray-400 text-sm font-medium mb-2">Discover Campaigns from Network</div>
          <div className="flex flex-wrap gap-2 items-center">
            <select
              className="bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none"
              value={discoverAccount}
              onChange={e => { setDiscoverAccount(parseInt(e.target.value)); setDiscovered([]) }}
            >
              <option value={0}>Select an account</option>
              {accounts.map(a => <option key={a.id} value={a.id}>{a.label}</option>)}
            </select>
            <button
              onClick={discoverCampaigns}
              disabled={!discoverAccount || discovering}
              className="bg-blue-600 hover:bg-blue-500 text-white px-4 py-2 rounded-lg text-sm font-medium transition disabled:opacity-40"
            >
              {discovering ? 'Fetching...' : 'Fetch Campaigns'}
            </button>
            {discoverError && <span className="text-red-400 text-xs">{discoverError}</span>}
          </div>
        </div>

        {discovered.length > 0 && (
          <div>
            <div className="px-4 py-2 bg-gray-800/40 text-gray-500 text-xs">
              {discovered.length} campaigns found · Select a canonical campaign to map each one (or "New" to auto-create)
            </div>
            <div className="divide-y divide-gray-800 max-h-96 overflow-y-auto">
              {discovered.map(nc => (
                <div key={nc.id} className="flex items-center gap-3 px-4 py-3">
                  <div className="flex-1 min-w-0">
                    <div className="text-white text-sm truncate">{nc.name}</div>
                    <div className="text-gray-600 text-xs font-mono">ID: {nc.id} · {nc.status}</div>
                  </div>
                  {nc.already_mapped ? (
                    <span className="text-green-500 text-xs font-medium shrink-0">✓ Mapped</span>
                  ) : (
                    <div className="flex items-center gap-2 shrink-0">
                      <select
                        className="bg-gray-800 border border-gray-700 rounded-lg px-2 py-1.5 text-xs text-white focus:outline-none max-w-40"
                        value={quickMap[nc.id] ?? ''}
                        onChange={e => setQuickMap(m => ({ ...m, [nc.id]: parseInt(e.target.value) }))}
                      >
                        <option value="">-- map to --</option>
                        <option value={0}>+ New Campaign</option>
                        {campaigns.map(c => <option key={c.id} value={c.id}>{c.name}</option>)}
                      </select>
                      <button
                        onClick={() => quickMapCampaign(nc)}
                        disabled={quickMap[nc.id] === undefined || quickMap[nc.id] === null || String(quickMap[nc.id]) === ''}
                        className="bg-green-500 text-black px-3 py-1.5 rounded-lg text-xs font-medium hover:bg-green-400 disabled:opacity-30 transition"
                      >
                        Map
                      </button>
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Existing canonical campaigns */}
      <div className="space-y-3">
        {campaigns.length > 0 && (
          <div className="text-gray-500 text-xs uppercase tracking-wide px-1">Canonical Campaigns ({campaigns.length})</div>
        )}
        {campaigns.map(c => (
          <div key={c.id} className="bg-gray-900 rounded-xl border border-gray-800 overflow-hidden">
            <div className="flex items-center justify-between px-4 py-3 cursor-pointer" onClick={() => loadMappings(c.id)}>
              <div>
                <div className="text-white font-medium">{c.name}</div>
                {c.tags && <div className="text-gray-500 text-xs mt-0.5">{c.tags}</div>}
              </div>
              <div className="flex items-center gap-3">
                <button
                  onClick={(e) => { e.stopPropagation(); setMapForm({...mapForm, campaign_id: c.id}); setShowMapForm(c.id) }}
                  className="text-green-500 text-xs hover:text-green-400"
                >
                  + Map Manually
                </button>
                <span className="text-gray-600 text-xs">{mappings[c.id] !== undefined ? '▲' : '▼'}</span>
              </div>
            </div>

            {showMapForm === c.id && (
              <div className="px-4 py-3 bg-gray-800/50 border-t border-gray-700 flex flex-wrap gap-2 items-end">
                <select className="bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white" value={mapForm.account_id} onChange={e => setMapForm({...mapForm, account_id: parseInt(e.target.value)})}>
                  <option value={0}>Select Account</option>
                  {accounts.map(a => <option key={a.id} value={a.id}>{a.label}</option>)}
                </select>
                <input className="bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white w-36 focus:outline-none focus:border-green-500" placeholder="Network Campaign ID" value={mapForm.network_campaign_id} onChange={e => setMapForm({...mapForm, network_campaign_id: e.target.value})} />
                <input className="bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white w-40 focus:outline-none focus:border-green-500" placeholder="Name on network (optional)" value={mapForm.network_campaign_name} onChange={e => setMapForm({...mapForm, network_campaign_name: e.target.value})} />
                <button onClick={createMapping} className="bg-green-500 text-black px-3 py-2 rounded-lg text-sm font-medium">Save</button>
                <button onClick={() => setShowMapForm(null)} className="text-gray-500 text-sm">Cancel</button>
              </div>
            )}

            {mappings[c.id] !== undefined && (
              <div className="border-t border-gray-800 divide-y divide-gray-800">
                {mappings[c.id].length === 0 && (
                  <div className="px-4 py-3 text-gray-600 text-xs">No account mappings yet</div>
                )}
                {mappings[c.id].map((m: any) => (
                  <div key={m.id} className="flex items-center justify-between px-4 py-2">
                    <div>
                      <span className="text-gray-300 text-sm">{getAccountLabel(m.account_id)}</span>
                      <span className="mx-2 text-gray-700">·</span>
                      <span className="text-gray-500 text-xs font-mono">ID: {m.network_campaign_id}</span>
                      {m.network_campaign_name && <span className="ml-2 text-gray-600 text-xs">{m.network_campaign_name}</span>}
                    </div>
                    <button onClick={() => deleteMapping(m.id, c.id)} className="text-gray-700 hover:text-red-400 text-xs">Remove</button>
                  </div>
                ))}
              </div>
            )}
          </div>
        ))}

        {campaigns.length === 0 && (
          <div className="bg-gray-900 rounded-xl border border-gray-800 text-gray-500 text-sm text-center py-12">
            Use "Fetch Campaigns" above to pull campaigns from your affiliate account and map them.
          </div>
        )}
      </div>
    </div>
  )
}
