import { useEffect, useState } from 'react'
import { AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts'
import api from '../api'

const PERIODS = ['today', 'yesterday', 'week', 'month', 'year'] as const
type Period = typeof PERIODS[number]

export default function PartnerView() {
  const [period, setPeriod] = useState<Period>('month')
  const [summary, setSummary] = useState<any>(null)
  const [campaigns, setCampaigns] = useState<any[]>([])
  const [daily, setDaily] = useState<any[]>([])

  useEffect(() => {
    Promise.all([
      api.get(`/partner/summary?period=${period}`),
      api.get(`/partner/by-campaign?period=${period}`),
      api.get(`/partner/daily?period=${period}`)
    ]).then(([s, c, d]) => {
      setSummary(s.data)
      setCampaigns(c.data)
      setDaily(d.data)
    })
  }, [period])

  const fmt = (n: number) => '$' + n.toLocaleString('en-US', { minimumFractionDigits: 2 })

  return (
    <div className="min-h-screen bg-gray-950 p-4 space-y-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <div className="text-green-400 font-bold text-lg">Revenue Stats</div>
          <div className="text-gray-600 text-xs">Partner View</div>
        </div>
        <div className="flex bg-gray-900 rounded-xl border border-gray-800 p-1 gap-1">
          {PERIODS.map(p => (
            <button key={p} onClick={() => setPeriod(p)}
              className={`px-3 py-1.5 rounded-lg text-sm font-medium transition capitalize ${period === p ? 'bg-green-500 text-black' : 'text-gray-400 hover:text-white'}`}>
              {p}
            </button>
          ))}
        </div>
      </div>

      <div className="grid grid-cols-2 gap-3">
        <div className="bg-gray-900 rounded-xl p-4 border border-gray-800 col-span-2">
          <div className="text-gray-500 text-xs uppercase">Total Revenue</div>
          <div className="text-3xl font-bold text-green-400 mt-1">{fmt(summary?.revenue || 0)}</div>
        </div>
        <div className="bg-gray-900 rounded-xl p-4 border border-gray-800">
          <div className="text-gray-500 text-xs uppercase">Conversions</div>
          <div className="text-xl font-bold text-white mt-1">{(summary?.conversions || 0).toLocaleString()}</div>
        </div>
        <div className="bg-gray-900 rounded-xl p-4 border border-gray-800">
          <div className="text-gray-500 text-xs uppercase">EPC</div>
          <div className="text-xl font-bold text-white mt-1">
            {summary?.clicks ? fmt((summary.revenue || 0) / summary.clicks) : '$0.00'}
          </div>
        </div>
      </div>

      {daily.length > 0 && (
        <div className="bg-gray-900 rounded-xl border border-gray-800 p-4">
          <ResponsiveContainer width="100%" height={150}>
            <AreaChart data={daily}>
              <defs>
                <linearGradient id="revp" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#22c55e" stopOpacity={0.3} />
                  <stop offset="95%" stopColor="#22c55e" stopOpacity={0} />
                </linearGradient>
              </defs>
              <XAxis dataKey="date" tick={{ fontSize: 10, fill: '#6b7280' }} tickLine={false} />
              <YAxis tick={{ fontSize: 10, fill: '#6b7280' }} tickLine={false} axisLine={false} tickFormatter={(v) => '$' + v} />
              <Tooltip contentStyle={{ background: '#111827', border: '1px solid #374151', borderRadius: 8 }} formatter={(v: any) => [fmt(Number(v)), "Revenue"]} />
              <Area type="monotone" dataKey="revenue" stroke="#22c55e" strokeWidth={2} fill="url(#revp)" />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      )}

      <div className="bg-gray-900 rounded-xl border border-gray-800 overflow-hidden">
        <div className="px-4 py-3 border-b border-gray-800 text-gray-400 text-sm font-medium">By Campaign</div>
        <div className="divide-y divide-gray-800">
          {campaigns.map((c: any) => (
            <div key={c.campaign_id} className="flex items-center justify-between px-4 py-3">
              <span className="text-gray-300 text-sm">{c.campaign_name}</span>
              <span className="text-green-400 font-bold">{fmt(c.revenue)}</span>
            </div>
          ))}
          {campaigns.length === 0 && <div className="text-gray-500 text-sm text-center py-6">No data</div>}
        </div>
      </div>
    </div>
  )
}
