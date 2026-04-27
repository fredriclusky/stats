import { useCallback, useEffect, useRef, useState } from 'react'
import { Area, AreaChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import api from '../api'

const PERIODS = ['today', 'yesterday', 'week', 'month', 'year'] as const
type Period = typeof PERIODS[number] | 'custom'

interface Summary { revenue: number; clicks: number; conversions: number; start: string; end: string }
interface DayRow { date: string; revenue: number }
interface AccountRow { account_id: number; account_label: string; network_name: string; revenue: number; clicks: number; conversions: number }

function today() {
  return new Date().toISOString().slice(0, 10)
}

function fmt(n: number) {
  return '$' + n.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

function StatCard({ label, value, sub }: { label: string; value: string; sub?: string }) {
  return (
    <div className="bg-gray-900 rounded-xl p-4 border border-gray-800">
      <div className="text-gray-500 text-xs uppercase tracking-wide mb-1">{label}</div>
      <div className="text-2xl font-bold text-white">{value}</div>
      {sub && <div className="text-gray-500 text-xs mt-1">{sub}</div>}
    </div>
  )
}

export default function KarlinStats() {
  const [period, setPeriod] = useState<Period>('today')
  const [customStart, setCustomStart] = useState(today())
  const [customEnd, setCustomEnd] = useState(today())
  const [showCal, setShowCal] = useState(false)
  const [summary, setSummary] = useState<Summary | null>(null)
  const [daily, setDaily] = useState<DayRow[]>([])
  const [accounts, setAccounts] = useState<AccountRow[]>([])
  const [loading, setLoading] = useState(true)
  const calRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (calRef.current && !calRef.current.contains(e.target as Node)) setShowCal(false)
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [])

  const buildQs = useCallback(() => {
    if (period === 'custom') return `period=custom&start_date=${customStart}&end_date=${customEnd}`
    return `period=${period}`
  }, [period, customStart, customEnd])

  const loadStats = useCallback(() => {
    setLoading(true)
    const qs = buildQs()
    const trendQs = period === 'today' || period === 'yesterday' ? 'period=month' : qs
    Promise.all([
      api.get(`/partner/karlin/summary?${qs}`),
      api.get(`/partner/karlin/daily?${trendQs}`),
      api.get(`/partner/karlin/by-account?${qs}`),
    ]).then(([s, d, a]) => {
      setSummary(s.data)
      setDaily(d.data)
      setAccounts(a.data)
    }).finally(() => setLoading(false))
  }, [buildQs, period])

  useEffect(() => { loadStats() }, [loadStats])

  const logout = () => {
    localStorage.removeItem('token')
    localStorage.removeItem('role')
    window.location.href = '/login'
  }

  const periodLabel = period === 'custom' ? `${customStart} -> ${customEnd}` : period

  return (
    <div className="min-h-screen bg-gray-950 text-white">
      <div className="max-w-5xl mx-auto px-4 py-6 space-y-6">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h1 className="text-xl font-bold text-white">Karlin Stats</h1>
            <div className="text-gray-500 text-sm">Revenue dashboard</div>
          </div>
          <div className="flex items-center gap-2 flex-wrap">
            <div className="flex items-center bg-gray-900 rounded-xl border border-gray-800 p-1 gap-1">
              {PERIODS.map(p => (
                <button
                  key={p}
                  onClick={() => { setPeriod(p); setShowCal(false) }}
                  className={`px-3 py-1.5 rounded-lg text-sm font-medium transition capitalize ${
                    period === p ? 'bg-green-500 text-black' : 'text-gray-400 hover:text-white'
                  }`}
                >
                  {p}
                </button>
              ))}
              <div className="relative" ref={calRef}>
                <button
                  onClick={() => setShowCal(v => !v)}
                  className={`px-3 py-1.5 rounded-lg text-sm font-medium transition ${
                    period === 'custom' ? 'bg-green-500 text-black' : 'text-gray-400 hover:text-white'
                  }`}
                >
                  Range
                </button>
                {showCal && (
                  <div className="absolute right-0 top-full mt-2 z-50 bg-gray-900 border border-gray-700 rounded-xl shadow-2xl p-4 w-72">
                    <div className="text-gray-400 text-xs font-medium uppercase tracking-wide mb-3">Custom Date Range</div>
                    <div className="space-y-3">
                      <div>
                        <label className="text-gray-500 text-xs block mb-1">Start Date</label>
                        <input type="date" value={customStart} max={customEnd} onChange={e => setCustomStart(e.target.value)} className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-green-500 [color-scheme:dark]" />
                      </div>
                      <div>
                        <label className="text-gray-500 text-xs block mb-1">End Date</label>
                        <input type="date" value={customEnd} min={customStart} max={today()} onChange={e => setCustomEnd(e.target.value)} className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-green-500 [color-scheme:dark]" />
                      </div>
                      <button onClick={() => { setShowCal(false); setPeriod('custom') }} className="w-full bg-green-500 hover:bg-green-400 text-black font-semibold py-2 rounded-lg text-sm transition">Apply Range</button>
                    </div>
                  </div>
                )}
              </div>
            </div>
            <button onClick={logout} className="text-gray-500 hover:text-white text-sm px-3 py-1.5">Logout</button>
          </div>
        </div>

        {loading ? (
          <div className="text-gray-500 text-center py-12">Loading...</div>
        ) : (
          <>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
              <StatCard label="Revenue" value={fmt(summary?.revenue || 0)} />
              <StatCard label="Conversions" value={(summary?.conversions || 0).toLocaleString()} />
              <StatCard label="Clicks" value={(summary?.clicks || 0).toLocaleString()} />
              <StatCard label="EPC" value={summary?.clicks ? fmt((summary.revenue || 0) / summary.clicks) : '$0.00'} sub="Earnings per click" />
            </div>

            <div className="bg-gray-900 rounded-xl border border-gray-800 p-4">
              <div className="text-gray-400 text-sm font-medium mb-4">Revenue Trend</div>
              <ResponsiveContainer width="100%" height={220}>
                <AreaChart data={daily}>
                  <defs>
                    <linearGradient id="karlinRev" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#22c55e" stopOpacity={0.3} />
                      <stop offset="95%" stopColor="#22c55e" stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <XAxis dataKey="date" tick={{ fontSize: 11, fill: '#6b7280' }} tickLine={false} />
                  <YAxis tick={{ fontSize: 11, fill: '#6b7280' }} tickLine={false} axisLine={false} tickFormatter={(v) => '$' + v} />
                  <Tooltip contentStyle={{ background: '#111827', border: '1px solid #374151', borderRadius: 8 }} formatter={(v: any) => [fmt(Number(v)), 'Revenue']} />
                  <Area type="monotone" dataKey="revenue" stroke="#22c55e" strokeWidth={2} fill="url(#karlinRev)" />
                </AreaChart>
              </ResponsiveContainer>
            </div>

            <div className="bg-gray-900 rounded-xl border border-gray-800 overflow-hidden">
              <div className="px-4 py-3 border-b border-gray-800 text-gray-400 text-sm font-medium">
                By Account - <span className="text-gray-500 font-normal capitalize">{periodLabel}</span>
              </div>
              <div className="divide-y divide-gray-800">
                {accounts.map(a => (
                  <div key={a.account_id} className="flex items-center justify-between px-4 py-3">
                    <div className="min-w-0">
                      <div className="text-white text-sm font-medium truncate">{a.account_label}</div>
                      <div className="text-gray-500 text-xs">{a.network_name} - {a.clicks.toLocaleString()} clicks - {a.conversions} conv</div>
                    </div>
                    <div className="text-green-400 font-bold text-sm shrink-0 ml-4">{fmt(a.revenue)}</div>
                  </div>
                ))}
                {accounts.length === 0 && <div className="text-gray-500 text-sm text-center py-8">No Karlin account data for this period.</div>}
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  )
}
