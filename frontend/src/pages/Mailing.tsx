import { useEffect, useState } from 'react'
import api from '../api'

export default function Mailing() {
  const [events, setEvents] = useState<any[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    api.get('/inbound/events?limit=50').then(r => setEvents(r.data)).finally(() => setLoading(false))
  }, [])

  return (
    <div className="space-y-4">
      <h1 className="text-xl font-bold text-white">Mailing Events</h1>

      <div className="bg-gray-900 rounded-xl border border-gray-800 p-4">
        <div className="text-gray-400 text-sm font-medium mb-2">Inbound API Endpoint</div>
        <code className="text-green-400 text-xs font-mono block bg-gray-800 rounded-lg px-3 py-2">
          POST /api/inbound
        </code>
        <div className="text-gray-600 text-xs mt-2 font-mono">
          Body: sub_id, prompt_used, list_used, sends, opens, clicks, extra_data
        </div>
      </div>

      <div className="bg-gray-900 rounded-xl border border-gray-800 overflow-hidden">
        <div className="px-4 py-3 border-b border-gray-800 text-gray-400 text-sm font-medium">Recent Events ({events.length})</div>
        {loading ? (
          <div className="text-gray-500 text-sm text-center py-8">Loading...</div>
        ) : (
          <div className="divide-y divide-gray-800">
            {events.map(e => (
              <div key={e.id} className="px-4 py-3">
                <div className="flex items-center justify-between mb-1">
                  <span className="text-green-400 font-mono text-sm">{e.sub_id}</span>
                  <span className="text-gray-600 text-xs">{new Date(e.received_at).toLocaleString()}</span>
                </div>
                {e.list_used && <div className="text-gray-400 text-xs">List: {e.list_used}</div>}
                {(e.sends || e.opens || e.clicks) && (
                  <div className="text-gray-600 text-xs mt-0.5">
                    {e.sends && `Sends: ${e.sends}`}
                    {e.opens && ` · Opens: ${e.opens}`}
                    {e.clicks && ` · Clicks: ${e.clicks}`}
                  </div>
                )}
                {e.prompt_used && (
                  <div className="text-gray-700 text-xs mt-1 truncate">Prompt: {e.prompt_used}</div>
                )}
              </div>
            ))}
            {events.length === 0 && (
              <div className="text-gray-500 text-sm text-center py-8">No mailing events yet. Joe will POST to /api/inbound.</div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
