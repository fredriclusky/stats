import { useEffect, useState } from 'react'
import api from '../api'

export default function SubIDs() {
  const [subids, setSubids] = useState<any[]>([])
  // mappings state removed
  const [logs, setLogs] = useState<any[]>([])
  const [showForm, setShowForm] = useState(false)
  const [form, setForm] = useState({ value: '', label: '', campaign_mapping_id: '', notes: '' })

  const load = async () => {
    const [s, l] = await Promise.all([api.get('/outbound/subids'), api.get('/outbound/log?limit=20')])
    setSubids(s.data)
    setLogs(l.data)
  }
  useEffect(() => { load() }, [])

  const create = async () => {
    await api.post('/outbound/subids', {
      ...form,
      campaign_mapping_id: form.campaign_mapping_id ? parseInt(form.campaign_mapping_id) : null
    })
    setShowForm(false)
    setForm({ value: '', label: '', campaign_mapping_id: '', notes: '' })
    load()
  }

  const fmt = (n: number) => '$' + n.toLocaleString('en-US', { minimumFractionDigits: 2 })

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-bold text-white">Sub-ID Registry</h1>
        <button onClick={() => setShowForm(!showForm)} className="bg-green-500 text-black px-4 py-2 rounded-lg text-sm font-medium hover:bg-green-400">+ New Sub-ID</button>
      </div>

      {showForm && (
        <div className="bg-gray-900 rounded-xl border border-gray-800 p-4 space-y-3">
          <div className="text-gray-400 text-sm font-medium">Register Sub-ID for Joe's System</div>
          <div className="grid grid-cols-2 gap-3">
            <input className="bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white font-mono focus:outline-none focus:border-green-500" placeholder="Sub-ID value (e.g. LIST1)" value={form.value} onChange={e => setForm({...form, value: e.target.value})} />
            <input className="bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-green-500" placeholder="Label (your reference)" value={form.label} onChange={e => setForm({...form, label: e.target.value})} />
            <input className="bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-green-500" placeholder="Campaign Mapping ID (optional)" value={form.campaign_mapping_id} onChange={e => setForm({...form, campaign_mapping_id: e.target.value})} />
            <input className="bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-green-500" placeholder="Notes" value={form.notes} onChange={e => setForm({...form, notes: e.target.value})} />
          </div>
          <div className="flex gap-2">
            <button onClick={create} className="bg-green-500 text-black px-4 py-2 rounded-lg text-sm font-medium hover:bg-green-400">Save</button>
            <button onClick={() => setShowForm(false)} className="text-gray-500 text-sm">Cancel</button>
          </div>
        </div>
      )}

      <div className="bg-gray-900 rounded-xl border border-gray-800 overflow-hidden">
        <div className="px-4 py-3 border-b border-gray-800 text-gray-400 text-sm font-medium">Registered Sub-IDs</div>
        <div className="divide-y divide-gray-800">
          {subids.map(s => (
            <div key={s.id} className="px-4 py-3 flex items-center justify-between">
              <div>
                <span className="text-green-400 font-mono text-sm font-medium">{s.value}</span>
                {s.label && <span className="ml-2 text-gray-400 text-sm">{s.label}</span>}
                {s.notes && <div className="text-gray-600 text-xs mt-0.5">{s.notes}</div>}
                {s.last_seen_at && <div className="text-gray-700 text-xs">Last seen: {new Date(s.last_seen_at).toLocaleDateString()}</div>}
              </div>
              <div className="text-right">
                <span className={`text-xs px-2 py-0.5 rounded-full ${s.active ? 'bg-green-500/20 text-green-400' : 'bg-gray-700 text-gray-500'}`}>
                  {s.active ? 'active' : 'inactive'}
                </span>
              </div>
            </div>
          ))}
          {subids.length === 0 && <div className="text-gray-500 text-sm text-center py-8">No Sub-IDs registered yet</div>}
        </div>
      </div>

      <div className="bg-gray-900 rounded-xl border border-gray-800 overflow-hidden">
        <div className="px-4 py-3 border-b border-gray-800 text-gray-400 text-sm font-medium">Recent Outbound Requests (Joe's System)</div>
        <div className="divide-y divide-gray-800">
          {logs.map(l => (
            <div key={l.id} className="px-4 py-2 flex items-center justify-between">
              <div>
                <span className="text-gray-300 font-mono text-sm">{l.sub_id}</span>
                <span className="ml-2 text-gray-600 text-xs">{new Date(l.sent_at).toLocaleString()}</span>
              </div>
              <span className="text-green-400 text-sm font-medium">{fmt(l.revenue_sent)}</span>
            </div>
          ))}
          {logs.length === 0 && <div className="text-gray-500 text-sm text-center py-6">No outbound requests yet</div>}
        </div>
      </div>

      <div className="bg-gray-900 rounded-xl border border-gray-800 p-4">
        <div className="text-gray-400 text-sm font-medium mb-2">Outbound API Endpoint</div>
        <code className="text-green-400 text-xs font-mono block bg-gray-800 rounded-lg px-3 py-2">
          GET /api/outbound/revenue?sub_id=YOUR_SUB_ID&start_date=2026-01-01&end_date=2026-01-31
        </code>
        <div className="text-gray-600 text-xs mt-2">Returns: {'{ "sub_id": "...", "revenue": 123.45, "start_date": "...", "end_date": "..." }'}</div>
      </div>
    </div>
  )
}
