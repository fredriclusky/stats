import { useEffect, useState, useCallback, useRef } from 'react'
import { AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts'
import api from '../api'

const PERIODS = ['today', 'yesterday', 'week', 'month', 'year'] as const
type Period = typeof PERIODS[number] | 'custom'

interface Summary { revenue: number; clicks: number; conversions: number; start: string; end: string }
interface CampaignRow { campaign_id: number; campaign_name: string; revenue: number; clicks: number; conversions: number }
interface DayRow { date: string; revenue: number }
interface AccountRow { account_id: number; account_label: string; network_name: string; revenue: number; clicks: number; conversions: number }

function StatCard({ label, value, sub }: { label: string; value: string; sub?: string }) {
  return (
    <div className="bg-gray-900 rounded-xl p-4 border border-gray-800">
      <div className="text-gray-500 text-xs uppercase tracking-wide mb-1">{label}</div>
      <div className="text-2xl font-bold text-white">{value}</div>
      {sub && <div className="text-gray-500 text-xs mt-1">{sub}</div>}
    </div>
  )
}

function today() {
  return new Date().toISOString().slice(0, 10)
}

export default function Dashboard() {
  const [period, setPeriod] = useState<Period>('week')
  const [customStart, setCustomStart] = useState(today())
  const [customEnd, setCustomEnd] = useState(today())
  const [showCal, setShowCal] = useState(false)
  const calRef = useRef<HTMLDivElement>(null)

  const [summary, setSummary] = useState<Summary | null>(null)
  const [campaigns, setCampaigns] = useState<CampaignRow[]>([])
  const [daily, setDaily] = useState<DayRow[]>([])
  const [accounts, setAccounts] = useState<AccountRow[]>([])
  const [loading, setLoading] = useState(true)
  const [syncing, setSyncing] = useState(false)
  const [syncMsg, setSyncMsg] = useState<{ text: string; ok: boolean } | null>(null)
  const [lastSynced, setLastSynced] = useState<string | null>(null)

  // Close calendar on outside click
  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (calRef.current && !calRef.current.contains(e.target as Node)) {
        setShowCal(false)
      }
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [])

  const buildQs = useCallback(() => {
    if (period === 'custom') {
      return `period=custom&start_date=${customStart}&end_date=${customEnd}`
    }
    return `period=${period}`
  }, [period, customStart, customEnd])

  const loadStats = useCallback(() => {
    setLoading(true)
    const qs = buildQs()
    const trendQs = (period === 'today' || period === 'yesterday')
      ? `period=month`
      : qs
    Promise.all([
      api.get(`/stats/summary?${qs}`),
      api.get(`/stats/by-campaign?${qs}`),
      api.get(`/stats/daily?${trendQs}`),
      api.get(`/stats/by-account?${qs}`),
    ]).then(([s, c, d, a]) => {
      setSummary(s.data)
      setCampaigns(c.data.slice(0, 10))
      setDaily(d.data)
      setAccounts(a.data)
    }).finally(() => setLoading(false))
  }, [buildQs, period])

  useEffect(() => { loadStats() }, [loadStats])

  const applyCustomRange = () => {
    setShowCal(false)
    setPeriod('custom')
  }

  const handlePeriodClick = (p: typeof PERIODS[number]) => {
    setPeriod(p)
    setShowCal(false)
  }

  const handleSync = async () => {
    setSyncing(true)
    setSyncMsg(null)
    try {
      await api.post('/sync/now?days_back=2')
      setSyncMsg({ text: 'Sync started — stats updating in background', ok: true })
      setLastSynced(new Date().toLocaleTimeString())
      setTimeout(() => loadStats(), 3000)
    } catch (e: any) {
      setSyncMsg({ text: 'Sync failed: ' + (e.response?.data?.detail || e.message), ok: false })
    } finally {
      setSyncing(false)
      setTimeout(() => setSyncMsg(null), 5000)
    }
  }

  const fmt = (n: number) => '$' + n.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })

  const periodLabel = period === 'custom'
    ? `${customStart} → ${customEnd}`
    : period

  return (
    <div className="space-y-6">
      {/* Header row */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <h1 className="text-xl font-bold text-white">Dashboard</h1>
          {lastSynced && <span className="text-gray-600 text-xs">Last sync: {lastSynced}</span>}
        </div>
        <div className="flex items-center gap-2 flex-wrap">
          <button
            onClick={handleSync}
            disabled={syncing}
            className="flex items-center gap-2 bg-gray-800 hover:bg-gray-700 border border-gray-700 text-gray-300 hover:text-white px-3 py-1.5 rounded-lg text-sm font-medium transition disabled:opacity-50"
          >
            <span className={syncing ? 'animate-spin inline-block' : ''}>⟳</span>
            {syncing ? 'Syncing...' : 'Sync Now'}
          </button>

          {/* Period buttons + calendar toggle */}
          <div className="flex items-center bg-gray-900 rounded-xl border border-gray-800 p-1 gap-1">
            {PERIODS.map(p => (
              <button
                key={p}
                onClick={() => handlePeriodClick(p)}
                className={`px-3 py-1.5 rounded-lg text-sm font-medium transition capitalize ${
                  period === p ? 'bg-green-500 text-black' : 'text-gray-400 hover:text-white'
                }`}
              >
                {p}
              </button>
            ))}

            {/* Calendar toggle button */}
            <div className="relative" ref={calRef}>
              <button
                onClick={() => setShowCal(v => !v)}
                title="Custom date range"
                className={`px-3 py-1.5 rounded-lg text-sm font-medium transition flex items-center gap-1.5 ${
                  period === 'custom'
                    ? 'bg-green-500 text-black'
                    : 'text-gray-400 hover:text-white'
                }`}
              >
                <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <rect x="3" y="4" width="18" height="18" rx="2" strokeWidth="2"/>
                  <line x1="3" y1="9" x2="21" y2="9" strokeWidth="2"/>
                  <line x1="8" y1="2" x2="8" y2="6" strokeWidth="2"/>
                  <line x1="16" y1="2" x2="16" y2="6" strokeWidth="2"/>
                </svg>
                {period === 'custom' ? `${customStart} – ${customEnd}` : 'Range'}
              </button>

              {showCal && (
                <div className="absolute right-0 top-full mt-2 z-50 bg-gray-900 border border-gray-700 rounded-xl shadow-2xl p-4 w-72">
                  <div className="text-gray-400 text-xs font-medium uppercase tracking-wide mb-3">Custom Date Range</div>
                  <div className="space-y-3">
                    <div>
                      <label className="text-gray-500 text-xs block mb-1">Start Date</label>
                      <input
                        type="date"
                        value={customStart}
                        max={customEnd}
                        onChange={e => setCustomStart(e.target.value)}
                        className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-green-500 [color-scheme:dark]"
                      />
                    </div>
                    <div>
                      <label className="text-gray-500 text-xs block mb-1">End Date</label>
                      <input
                        type="date"
                        value={customEnd}
                        min={customStart}
                        max={today()}
                        onChange={e => setCustomEnd(e.target.value)}
                        className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-green-500 [color-scheme:dark]"
                      />
                    </div>

                    {/* Quick presets inside the dropdown */}
                    <div className="pt-1 border-t border-gray-800">
                      <div className="text-gray-500 text-xs mb-2">Quick presets</div>
                      <div className="grid grid-cols-2 gap-1.5">
                        {[
                          { label: 'Last 3 days', days: 3 },
                          { label: 'Last 14 days', days: 14 },
                          { label: 'Last 30 days', days: 30 },
                          { label: 'Last 60 days', days: 60 },
                          { label: 'Last 90 days', days: 90 },
                          { label: 'Last 6 months', days: 180 },
                        ].map(({ label, days }) => {
                          const s = new Date()
                          s.setDate(s.getDate() - (days - 1))
                          const sv = s.toISOString().slice(0, 10)
                          return (
                            <button
                              key={days}
                              onClick={() => { setCustomStart(sv); setCustomEnd(today()); }}
                              className="text-xs text-gray-400 hover:text-white bg-gray-800 hover:bg-gray-700 px-2 py-1.5 rounded-lg text-left transition"
                            >
                              {label}
                            </button>
                          )
                        })}
                      </div>
                    </div>

                    <button
                      onClick={applyCustomRange}
                      className="w-full bg-green-500 hover:bg-green-400 text-black font-semibold py-2 rounded-lg text-sm transition"
                    >
                      Apply Range
                    </button>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>

      {syncMsg && (
        <div className={`text-sm px-4 py-2 rounded-lg border ${syncMsg.ok ? 'bg-green-500/10 border-green-500/30 text-green-400' : 'bg-red-500/10 border-red-500/30 text-red-400'}`}>
          {syncMsg.text}
        </div>
      )}

      {loading ? (
        <div className="text-gray-500 text-center py-12">Loading...</div>
      ) : (
        <>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            <StatCard label="Revenue" value={fmt(summary?.revenue || 0)} />
            <StatCard label="Conversions" value={(summary?.conversions || 0).toLocaleString()} />
            <StatCard label="Clicks" value={(summary?.clicks || 0).toLocaleString()} />
            <StatCard
              label="EPC"
              value={summary?.clicks ? fmt((summary.revenue || 0) / summary.clicks) : '$0.00'}
              sub="Earnings per click"
            />
          </div>

          {accounts.length > 0 && (
            <div className="bg-gray-900 rounded-xl border border-gray-800 overflow-hidden">
              <div className="px-4 py-3 border-b border-gray-800 text-gray-400 text-sm font-medium">
                By Account — <span className="text-gray-500 font-normal capitalize">{periodLabel}</span>
              </div>
              <div className="divide-y divide-gray-800">
                {accounts.map(a => (
                  <div key={a.account_id} className="flex items-center justify-between px-4 py-3">
                    <div className="min-w-0">
                      <div className="text-white text-sm font-medium truncate">{a.account_label}</div>
                      <div className="text-gray-500 text-xs">{a.network_name} · {a.clicks.toLocaleString()} clicks · {a.conversions} conv</div>
                    </div>
                    <div className="text-green-400 font-bold text-sm shrink-0 ml-4">{fmt(a.revenue)}</div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {daily.length > 0 && (
            <div className="bg-gray-900 rounded-xl border border-gray-800 p-4">
              <div className="text-gray-400 text-sm font-medium mb-4">Revenue Trend</div>
              <ResponsiveContainer width="100%" height={180}>
                <AreaChart data={daily}>
                  <defs>
                    <linearGradient id="rev" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#22c55e" stopOpacity={0.3} />
                      <stop offset="95%" stopColor="#22c55e" stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <XAxis dataKey="date" tick={{ fontSize: 11, fill: '#6b7280' }} tickLine={false} />
                  <YAxis tick={{ fontSize: 11, fill: '#6b7280' }} tickLine={false} axisLine={false} tickFormatter={(v) => '$' + v} />
                  <Tooltip
                    contentStyle={{ background: '#111827', border: '1px solid #374151', borderRadius: 8 }}
                    formatter={(v: any) => [fmt(Number(v)), 'Revenue']}
                  />
                  <Area type="monotone" dataKey="revenue" stroke="#22c55e" strokeWidth={2} fill="url(#rev)" />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          )}

          <div className="bg-gray-900 rounded-xl border border-gray-800 overflow-hidden">
            <div className="px-4 py-3 border-b border-gray-800 text-gray-400 text-sm font-medium">
              Top Campaigns — <span className="text-gray-500 font-normal capitalize">{periodLabel}</span>
            </div>
            {campaigns.length === 0 ? (
              <div className="text-gray-500 text-sm text-center py-8">No data yet. Add affiliate accounts and sync.</div>
            ) : (
              <div className="divide-y divide-gray-800">
                {campaigns.map((c) => (
                  <div key={c.campaign_id} className="flex items-center justify-between px-4 py-3">
                    <div>
                      <div className="text-white text-sm font-medium">{c.campaign_name}</div>
                      <div className="text-gray-500 text-xs">{c.clicks.toLocaleString()} clicks · {c.conversions} conv</div>
                    </div>
                    <div className="text-green-400 font-bold">{fmt(c.revenue)}</div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </>
      )}
    </div>
  )
}
