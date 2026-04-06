import { useEffect, useState } from 'react'
import api from '../api'

const PERIODS = [
  { label: 'Today', value: 'today' },
  { label: 'Yesterday', value: 'yesterday' },
  { label: '7 Days', value: 'week' },
  { label: '30 Days', value: 'month' },
  { label: 'Year', value: 'year' },
]

const fmt$ = (n: number) => '$' + n.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
const fmtEpc = (n: number) => '$' + n.toLocaleString('en-US', { minimumFractionDigits: 4, maximumFractionDigits: 4 })

export default function SubIDs() {
  const [period, setPeriod] = useState('week')
  const [startDate, setStartDate] = useState('')
  const [endDate, setEndDate] = useState('')
  const [useCustom, setUseCustom] = useState(false)
  const [search, setSearch] = useState('')
  const [rows, setRows] = useState<any[]>([])
  const [logs, setLogs] = useState<any[]>([])
  const [loading, setLoading] = useState(false)
  const [expanded, setExpanded] = useState<Set<string>>(new Set())

  const load = async () => {
    setLoading(true)
    try {
      const params: Record<string, string> = {}
      if (useCustom && startDate && endDate) {
        params.start_date = startDate
        params.end_date = endDate
      } else {
        params.period = period
      }
      if (search.trim()) params.search = search.trim()

      const [subRes, logRes] = await Promise.all([
        api.get('/stats/joe-subids', { params }),
        api.get('/outbound/log?limit=20'),
      ])
      setRows(subRes.data)
      setLogs(logRes.data)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [period, useCustom, startDate, endDate])

  const handleSearch = (e: React.FormEvent) => { e.preventDefault(); load() }

  const toggle = (id: string) => {
    setExpanded(prev => {
      const next = new Set(prev)
      next.has(id) ? next.delete(id) : next.add(id)
      return next
    })
  }

  const totalRevenue = rows.reduce((s, r) => s + r.revenue, 0)
  const totalClicks = rows.reduce((s, r) => s + r.clicks, 0)
  const totalConv = rows.reduce((s, r) => s + r.conversions, 0)

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between flex-wrap gap-3">
        <h1 className="text-xl font-bold text-white">Sub-ID Tracker</h1>
        <div className="text-gray-500 text-xs">Auto-populated from network sync · Joe's unique IDs per account</div>
      </div>

      {/* Period + Date Range */}
      <div className="bg-gray-900 rounded-xl border border-gray-800 px-4 py-3 flex flex-wrap items-center gap-3">
        {!useCustom && PERIODS.map(p => (
          <button
            key={p.value}
            onClick={() => { setPeriod(p.value); setUseCustom(false) }}
            className={`px-3 py-1.5 rounded-lg text-sm font-medium transition ${
              period === p.value && !useCustom
                ? 'bg-green-500 text-black'
                : 'text-gray-400 hover:text-white hover:bg-gray-800'
            }`}
          >
            {p.label}
          </button>
        ))}
        <button
          onClick={() => setUseCustom(c => !c)}
          className={`px-3 py-1.5 rounded-lg text-sm font-medium transition ${
            useCustom ? 'bg-blue-500 text-white' : 'text-gray-400 hover:text-white hover:bg-gray-800'
          }`}
        >
          Custom Range
        </button>
        {useCustom && (
          <div className="flex items-center gap-2">
            <input
              type="date"
              className="bg-gray-800 border border-gray-700 rounded-lg px-3 py-1.5 text-sm text-white focus:outline-none focus:border-green-500"
              value={startDate}
              onChange={e => setStartDate(e.target.value)}
            />
            <span className="text-gray-500 text-sm">to</span>
            <input
              type="date"
              className="bg-gray-800 border border-gray-700 rounded-lg px-3 py-1.5 text-sm text-white focus:outline-none focus:border-green-500"
              value={endDate}
              onChange={e => setEndDate(e.target.value)}
            />
          </div>
        )}
      </div>

      {/* Search */}
      <form onSubmit={handleSearch} className="flex gap-2">
        <input
          type="text"
          placeholder="Search Sub-ID value..."
          className="flex-1 bg-gray-900 border border-gray-800 rounded-lg px-4 py-2.5 text-sm text-white placeholder-gray-600 focus:outline-none focus:border-green-500"
          value={search}
          onChange={e => setSearch(e.target.value)}
        />
        <button type="submit" className="bg-green-500 text-black px-4 py-2 rounded-lg text-sm font-medium hover:bg-green-400">
          Search
        </button>
        {search && (
          <button type="button" onClick={() => { setSearch(''); setTimeout(load, 0) }} className="text-gray-500 text-sm px-3 hover:text-white">
            Clear
          </button>
        )}
      </form>

      {/* Summary bar */}
      {rows.length > 0 && (
        <div className="grid grid-cols-3 gap-3">
          <div className="bg-gray-900 border border-gray-800 rounded-xl px-4 py-3">
            <div className="text-gray-500 text-xs mb-0.5">Total Revenue</div>
            <div className="text-green-400 font-bold text-lg">{fmt$(totalRevenue)}</div>
          </div>
          <div className="bg-gray-900 border border-gray-800 rounded-xl px-4 py-3">
            <div className="text-gray-500 text-xs mb-0.5">Total Clicks</div>
            <div className="text-white font-bold text-lg">{totalClicks.toLocaleString()}</div>
          </div>
          <div className="bg-gray-900 border border-gray-800 rounded-xl px-4 py-3">
            <div className="text-gray-500 text-xs mb-0.5">Total Conv.</div>
            <div className="text-white font-bold text-lg">{totalConv.toLocaleString()}</div>
          </div>
        </div>
      )}

      {/* Main table */}
      <div className="bg-gray-900 rounded-xl border border-gray-800 overflow-hidden">
        <div className="px-4 py-3 border-b border-gray-800 flex items-center justify-between">
          <span className="text-gray-400 text-sm font-medium">
            Joe's Sub-IDs {rows.length > 0 && <span className="text-gray-600">({rows.length})</span>}
          </span>
          {loading && <span className="text-gray-600 text-xs">Loading...</span>}
        </div>

        {/* Table header */}
        {rows.length > 0 && (
          <div className="grid grid-cols-6 gap-2 px-4 py-2 border-b border-gray-800/50 text-gray-600 text-xs font-medium uppercase tracking-wide">
            <div className="col-span-2">Sub-ID</div>
            <div className="text-right">Revenue</div>
            <div className="text-right">Clicks</div>
            <div className="text-right">Conv.</div>
            <div className="text-right">Last Seen</div>
          </div>
        )}

        <div className="divide-y divide-gray-800/50">
          {rows.map(row => {
            const isOpen = expanded.has(row.sub_id)
            return (
              <div key={row.sub_id}>
                {/* Main row */}
                <button
                  className="w-full grid grid-cols-6 gap-2 px-4 py-3 text-left hover:bg-gray-800/30 transition"
                  onClick={() => toggle(row.sub_id)}
                >
                  <div className="col-span-2 flex items-start gap-2">
                    <span className="text-gray-500 text-xs mt-0.5 w-3 shrink-0">{isOpen ? '▼' : '▶'}</span>
                    <div className="min-w-0">
                      <div className="text-green-400 font-mono text-sm font-medium truncate">{row.sub_id}</div>
                      {row.offer_names?.length > 0 && (
                        <div className="text-gray-600 text-xs truncate">{row.offer_names.join(', ')}</div>
                      )}
                      <div className="flex flex-wrap gap-1 mt-0.5">
                        {row.accounts?.map((a: any) => (
                          <span key={a.account_id} className="text-xs px-1.5 py-0.5 rounded bg-gray-800 text-gray-500">
                            {a.account_label}
                          </span>
                        ))}
                      </div>
                    </div>
                  </div>
                  <div className="text-right text-green-400 font-medium text-sm self-center">{fmt$(row.revenue)}</div>
                  <div className="text-right text-gray-300 text-sm self-center">{row.clicks.toLocaleString()}</div>
                  <div className="text-right text-gray-300 text-sm self-center">{row.conversions.toLocaleString()}</div>
                  <div className="text-right text-gray-500 text-xs self-center">{row.last_seen}</div>
                </button>

                {/* Expanded detail */}
                {isOpen && (
                  <div className="bg-gray-800/20 border-t border-gray-800/50 px-6 py-3 space-y-3">
                    {/* Per-account summary */}
                    {row.accounts?.length > 1 && (
                      <div>
                        <div className="text-gray-600 text-xs font-medium uppercase tracking-wide mb-1.5">By Account</div>
                        <div className="grid grid-cols-1 gap-1">
                          {row.accounts.map((a: any) => (
                            <div key={a.account_id} className="flex items-center justify-between text-xs py-1">
                              <span className="text-gray-400">{a.account_label} <span className="text-gray-600">({a.network_name})</span></span>
                              <span className="text-green-400 font-medium">{fmt$(a.revenue)}</span>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* Day-by-day */}
                    <div>
                      <div className="text-gray-600 text-xs font-medium uppercase tracking-wide mb-1.5">Day-by-Day</div>
                      <div className="rounded-lg border border-gray-800 overflow-hidden">
                        <div className="grid grid-cols-5 gap-2 px-3 py-1.5 text-gray-600 text-xs font-medium bg-gray-800/40">
                          <div>Date</div>
                          <div>Account</div>
                          <div className="text-right">Revenue</div>
                          <div className="text-right">Clicks</div>
                          <div className="text-right">Conv.</div>
                        </div>
                        {row.days?.map((d: any, i: number) => (
                          <div key={i} className="grid grid-cols-5 gap-2 px-3 py-1.5 text-xs border-t border-gray-800/50 hover:bg-gray-800/20">
                            <div className="text-gray-400 font-mono">{d.date}</div>
                            <div className="text-gray-500 truncate">{d.account_label}</div>
                            <div className="text-right text-green-400">{fmt$(d.revenue)}</div>
                            <div className="text-right text-gray-400">{d.clicks.toLocaleString()}</div>
                            <div className="text-right text-gray-400">{d.conversions.toLocaleString()}</div>
                          </div>
                        ))}
                      </div>
                    </div>

                    {/* EPC */}
                    <div className="text-gray-600 text-xs">
                      EPC: <span className="text-gray-400">{fmtEpc(row.epc)}</span>
                      &nbsp;&nbsp;First seen: <span className="text-gray-400">{row.first_seen}</span>
                    </div>
                  </div>
                )}
              </div>
            )
          })}
          {!loading && rows.length === 0 && (
            <div className="text-gray-500 text-sm text-center py-12">
              <div>No Sub-IDs found for this period</div>
              <div className="text-gray-700 text-xs mt-1">Data is synced automatically every 15 minutes</div>
            </div>
          )}
        </div>
      </div>

      {/* Outbound log */}
      <div className="bg-gray-900 rounded-xl border border-gray-800 overflow-hidden">
        <div className="px-4 py-3 border-b border-gray-800 text-gray-400 text-sm font-medium">
          Recent Outbound Requests (Joe's System)
        </div>
        <div className="divide-y divide-gray-800">
          {logs.map((l: any) => (
            <div key={l.id} className="px-4 py-2.5 flex items-center justify-between">
              <div>
                <span className="text-gray-300 font-mono text-sm">{l.sub_id}</span>
                <span className="ml-2 text-gray-600 text-xs">{new Date(l.sent_at).toLocaleString()}</span>
              </div>
              <span className="text-green-400 text-sm font-medium">{fmt$(l.revenue_sent)}</span>
            </div>
          ))}
          {logs.length === 0 && <div className="text-gray-500 text-sm text-center py-6">No outbound requests yet</div>}
        </div>
      </div>

      {/* Outbound API reference */}
      <div className="bg-gray-900 rounded-xl border border-gray-800 p-4">
        <div className="text-gray-400 text-sm font-medium mb-2">Outbound API Endpoint</div>
        <code className="text-green-400 text-xs font-mono block bg-gray-800 rounded-lg px-3 py-2">
          GET /api/outbound/revenue?sub_id=YOUR_SUB_ID&start_date=2026-01-01&end_date=2026-01-31
        </code>
        <div className="text-gray-600 text-xs mt-2">{'Returns: { "sub_id": "...", "revenue": 123.45, "start_date": "...", "end_date": "..." }'}</div>
      </div>
    </div>
  )
}
