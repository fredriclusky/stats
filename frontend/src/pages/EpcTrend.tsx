import { useEffect, useState } from 'react'
import { Area, AreaChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import api from '../api'

interface DateRow { date: string; revenue: number; clicks: number; conversions: number; epc: number }
interface HourRow { hour: number; label: string; revenue: number; clicks: number; conversions: number; epc: number; accounts: any[] }

function fmt(n: number) {
  return '$' + n.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

function fmtEpc(n: number) {
  return '$' + n.toLocaleString('en-US', { minimumFractionDigits: 4, maximumFractionDigits: 4 })
}

export default function EpcTrend() {
  const [dates, setDates] = useState<DateRow[]>([])
  const [selectedDate, setSelectedDate] = useState<string>('')
  const [hourly, setHourly] = useState<HourRow[]>([])
  const [errors, setErrors] = useState<any[]>([])
  const [loadingDates, setLoadingDates] = useState(true)
  const [loadingHours, setLoadingHours] = useState(false)

  useEffect(() => {
    setLoadingDates(true)
    api.get('/stats/epc-dates?period=month')
      .then(res => {
        setDates(res.data)
        if (res.data.length > 0) setSelectedDate(res.data[0].date)
      })
      .finally(() => setLoadingDates(false))
  }, [])

  useEffect(() => {
    if (!selectedDate) return
    setLoadingHours(true)
    api.get('/stats/epc-hourly', { params: { date: selectedDate } })
      .then(res => {
        setHourly(res.data.rows || [])
        setErrors(res.data.errors || [])
      })
      .finally(() => setLoadingHours(false))
  }, [selectedDate])

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between gap-3 flex-wrap">
        <div>
          <h1 className="text-xl font-bold text-white">EPC Trend Drilldown</h1>
          <div className="text-gray-500 text-sm">Click a date to view EPC by hour.</div>
        </div>
        <a href="/" className="text-gray-400 hover:text-white text-sm">Back to Dashboard</a>
      </div>

      <div className="bg-gray-900 rounded-xl border border-gray-800 overflow-hidden">
        <div className="px-4 py-3 border-b border-gray-800 text-gray-400 text-sm font-medium">Dates</div>
        {loadingDates ? (
          <div className="text-gray-500 text-sm text-center py-8">Loading dates...</div>
        ) : (
          <div className="divide-y divide-gray-800 max-h-80 overflow-auto">
            {dates.map(row => (
              <button
                key={row.date}
                onClick={() => setSelectedDate(row.date)}
                className={`w-full grid grid-cols-5 gap-3 px-4 py-3 text-left hover:bg-gray-800/40 transition ${selectedDate === row.date ? 'bg-gray-800/70' : ''}`}
              >
                <div className="text-white text-sm font-medium">{row.date}</div>
                <div className="text-green-400 text-sm text-right">{fmt(row.revenue)}</div>
                <div className="text-gray-300 text-sm text-right">{row.clicks.toLocaleString()} clicks</div>
                <div className="text-gray-300 text-sm text-right">{row.conversions} conv</div>
                <div className="text-blue-400 text-sm text-right font-mono">{fmtEpc(row.epc)}</div>
              </button>
            ))}
          </div>
        )}
      </div>

      {selectedDate && (
        <div className="bg-gray-900 rounded-xl border border-gray-800 p-4">
          <div className="flex items-center justify-between mb-4">
            <div className="text-gray-400 text-sm font-medium">Hourly EPC - {selectedDate}</div>
            {loadingHours && <div className="text-gray-600 text-xs">Loading hourly network data...</div>}
          </div>
          <ResponsiveContainer width="100%" height={220}>
            <AreaChart data={hourly}>
              <defs>
                <linearGradient id="hourlyEpc" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#60a5fa" stopOpacity={0.3} />
                  <stop offset="95%" stopColor="#60a5fa" stopOpacity={0} />
                </linearGradient>
              </defs>
              <XAxis dataKey="label" tick={{ fontSize: 11, fill: '#6b7280' }} tickLine={false} />
              <YAxis tick={{ fontSize: 11, fill: '#6b7280' }} tickLine={false} axisLine={false} tickFormatter={(v) => '$' + Number(v).toFixed(2)} />
              <Tooltip
                contentStyle={{ background: '#111827', border: '1px solid #374151', borderRadius: 8 }}
                formatter={(v: any) => [fmtEpc(Number(v)), 'EPC']}
              />
              <Area type="monotone" dataKey="epc" stroke="#60a5fa" strokeWidth={2} fill="url(#hourlyEpc)" />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      )}

      {selectedDate && (
        <div className="bg-gray-900 rounded-xl border border-gray-800 overflow-hidden">
          <div className="px-4 py-3 border-b border-gray-800 text-gray-400 text-sm font-medium">Hourly Detail</div>
          <div className="grid grid-cols-5 gap-3 px-4 py-2 border-b border-gray-800/50 text-gray-600 text-xs font-medium uppercase tracking-wide">
            <div>Hour</div>
            <div className="text-right">Revenue</div>
            <div className="text-right">Clicks</div>
            <div className="text-right">Conv.</div>
            <div className="text-right">EPC</div>
          </div>
          <div className="divide-y divide-gray-800/50">
            {hourly.map(row => (
              <div key={row.hour} className="grid grid-cols-5 gap-3 px-4 py-2 text-sm">
                <div className="text-white font-mono">{row.label}</div>
                <div className="text-green-400 text-right">{fmt(row.revenue)}</div>
                <div className="text-gray-300 text-right">{row.clicks.toLocaleString()}</div>
                <div className="text-gray-300 text-right">{row.conversions}</div>
                <div className="text-blue-400 text-right font-mono">{fmtEpc(row.epc)}</div>
              </div>
            ))}
          </div>
        </div>
      )}

      {errors.length > 0 && (
        <div className="bg-yellow-500/10 border border-yellow-500/30 text-yellow-300 rounded-xl p-4 text-sm">
          Some accounts could not load hourly data: {errors.map(e => e.account).join(', ')}
        </div>
      )}
    </div>
  )
}
