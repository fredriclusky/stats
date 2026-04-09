import { useEffect, useState, useCallback, useRef } from 'react'
import api from '../api'

const PERIODS = ['today', 'yesterday', 'week', 'month', 'year'] as const
type Period = typeof PERIODS[number] | 'custom'
type SortKey = 'revenue' | 'epc' | 'clicks' | 'conversions' | 'last_seen' | 'network_name'

interface AccountBreakdown {
  account_id: number
  account_label: string
  network_name: string
  revenue: number
  clicks: number
  conversions: number
}

interface OfferRow {
  offer_name: string
  brand: string | null
  network_id: number
  network_name: string
  revenue: number
  clicks: number
  conversions: number
  epc: number
  first_seen: string | null
  last_seen: string | null
  account_count: number
  accounts: AccountBreakdown[]
}

interface Network { id: number; name: string; type: string }
interface Account { id: number; network_id: number; label: string }

function today() { return new Date().toISOString().slice(0, 10) }
function fmt(n: number) { return '$' + n.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) }
function fmtEpc(epcCents: number) {
  // epc from API is already revenue/clicks*100 (cents)
  return epcCents.toFixed(4) + '¢'
}
function fmtNum(n: number) { return n.toLocaleString('en-US') }

const NETWORK_COLORS: Record<string, string> = {
  NeptuneAds: 'bg-indigo-900/50 text-indigo-300',
  Prescott:   'bg-purple-900/50 text-purple-300',
}
function networkBadge(name: string) {
  const cls = NETWORK_COLORS[name] ?? 'bg-gray-800 text-gray-400'
  return <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${cls}`}>{name}</span>
}

export default function OfferIntelligence() {
  const [period, setPeriod] = useState<Period>('week')
  const [customStart, setCustomStart] = useState(today())
  const [customEnd, setCustomEnd] = useState(today())
  const [showCal, setShowCal] = useState(false)
  const calRef = useRef<HTMLDivElement>(null)

  const [rows, setRows] = useState<OfferRow[]>([])
  const [networks, setNetworks] = useState<Network[]>([])
  const [accounts, setAccounts] = useState<Account[]>([])
  const [selectedNetwork, setSelectedNetwork] = useState<number | null>(null)
  const [selectedAccount, setSelectedAccount] = useState<number | null>(null)

  const [loading, setLoading] = useState(true)
  const [sortKey, setSortKey] = useState<SortKey>('epc')
  const [sortAsc, setSortAsc] = useState(false)
  const [expanded, setExpanded] = useState<Set<string>>(new Set())
  const [search, setSearch] = useState('')

  // Load networks + accounts once on mount
  useEffect(() => {
    Promise.all([
      api.get('/affiliates/networks'),
      api.get('/affiliates/accounts'),
    ]).then(([n, a]) => {
      setNetworks(n.data)
      setAccounts(a.data)
    })
  }, [])

  // Reset account when network changes
  useEffect(() => { setSelectedAccount(null) }, [selectedNetwork])

  // Filtered accounts for dropdown
  const accountsForDropdown = selectedNetwork
    ? accounts.filter(a => a.network_id === selectedNetwork)
    : accounts

  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (calRef.current && !calRef.current.contains(e.target as Node)) setShowCal(false)
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [])

  const buildQs = useCallback(() => {
    const params: string[] = []
    if (period === 'custom') {
      params.push(`period=custom&start_date=${customStart}&end_date=${customEnd}`)
    } else {
      params.push(`period=${period}`)
    }
    if (selectedNetwork !== null) params.push(`network_id=${selectedNetwork}`)
    if (selectedAccount !== null) params.push(`account_id=${selectedAccount}`)
    return params.join('&')
  }, [period, customStart, customEnd, selectedNetwork, selectedAccount])

  const loadData = useCallback(() => {
    setLoading(true)
    api.get(`/stats/offer-intelligence?${buildQs()}`)
      .then(r => setRows(r.data))
      .finally(() => setLoading(false))
  }, [buildQs])

  useEffect(() => { loadData() }, [loadData])

  const applyCustomRange = () => { setShowCal(false); setPeriod('custom') }
  const handlePeriodClick = (p: typeof PERIODS[number]) => { setPeriod(p); setShowCal(false) }

  const handleSort = (key: SortKey) => {
    if (sortKey === key) setSortAsc(a => !a)
    else { setSortKey(key); setSortAsc(false) }
  }
  const toggleExpand = (key: string) => {
    setExpanded(prev => { const s = new Set(prev); s.has(key) ? s.delete(key) : s.add(key); return s })
  }

  const periodLabel = period === 'custom' ? `${customStart} – ${customEnd}` : period.charAt(0).toUpperCase() + period.slice(1)

  const filtered = rows.filter(r => {
    if (!search) return true
    const q = search.toLowerCase()
    return r.offer_name.toLowerCase().includes(q) || (r.brand || '').toLowerCase().includes(q) || r.network_name.toLowerCase().includes(q)
  })

  const sorted = [...filtered].sort((a, b) => {
    const av: any = a[sortKey] ?? ''
    const bv: any = b[sortKey] ?? ''
    if (typeof av === 'string' && typeof bv === 'string') return sortAsc ? av.localeCompare(bv) : bv.localeCompare(av)
    return sortAsc ? av - bv : bv - av
  })

  const SortBtn = ({ col, label }: { col: SortKey; label: string }) => (
    <button onClick={() => handleSort(col)}
      className={`flex items-center gap-1 hover:text-white transition-colors whitespace-nowrap ${sortKey === col ? 'text-green-400' : 'text-gray-400'}`}>
      {label}
      <span className="text-xs">{sortKey === col ? (sortAsc ? '▲' : '▼') : '⇅'}</span>
    </button>
  )

  const showNetworkCol = selectedNetwork === null && selectedAccount === null

  return (
    <div className="space-y-5">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-xl font-bold text-white">Offer Intelligence</h1>
        <span className="text-gray-500 text-sm">All networks · both accounts combined</span>
      </div>

      {/* Period controls */}
      <div className="flex flex-wrap items-center gap-2" ref={calRef}>
        {PERIODS.map(p => (
          <button key={p} onClick={() => handlePeriodClick(p)}
            className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${period === p ? 'bg-green-600 text-white' : 'bg-gray-800 text-gray-400 hover:bg-gray-700'}`}>
            {p.charAt(0).toUpperCase() + p.slice(1)}
          </button>
        ))}

        {/* Calendar */}
        <div className="relative">
          <button onClick={() => setShowCal(v => !v)}
            className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-colors flex items-center gap-1.5 ${period === 'custom' ? 'bg-green-600 text-white' : 'bg-gray-800 text-gray-400 hover:bg-gray-700'}`}>
            <span>📅</span>{period === 'custom' ? periodLabel : 'Custom'}
          </button>
          {showCal && (
            <div className="absolute top-10 left-0 z-50 bg-gray-900 border border-gray-700 rounded-xl p-4 shadow-2xl w-72">
              <div className="text-gray-400 text-xs uppercase tracking-wide mb-3">Custom Date Range</div>
              <div className="space-y-3 mb-4">
                <div>
                  <label className="text-gray-500 text-xs block mb-1">From</label>
                  <input type="date" value={customStart} onChange={e => setCustomStart(e.target.value)}
                    className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-white text-sm" />
                </div>
                <div>
                  <label className="text-gray-500 text-xs block mb-1">To</label>
                  <input type="date" value={customEnd} onChange={e => setCustomEnd(e.target.value)}
                    className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-white text-sm" />
                </div>
              </div>
              <div className="flex flex-wrap gap-2 mb-4">
                {[['Last 3d', 3], ['Last 7d', 7], ['Last 14d', 14], ['Last 30d', 30], ['Last 60d', 60], ['Last 90d', 90]].map(([label, days]) => (
                  <button key={label} onClick={() => {
                    const end = today()
                    const start = new Date(Date.now() - (Number(days) - 1) * 86400000).toISOString().slice(0, 10)
                    setCustomStart(start); setCustomEnd(end)
                  }} className="px-2 py-1 bg-gray-800 hover:bg-gray-700 text-gray-300 text-xs rounded-lg">{label}</button>
                ))}
              </div>
              <button onClick={applyCustomRange} className="w-full bg-green-600 hover:bg-green-500 text-white rounded-lg py-2 text-sm font-medium">Apply Range</button>
            </div>
          )}
        </div>
      </div>

      {/* Network / Account filters */}
      <div className="flex flex-wrap items-center gap-3">
        <div className="flex items-center gap-2">
          <label className="text-gray-500 text-xs uppercase tracking-wide">Network</label>
          <select
            value={selectedNetwork ?? ''}
            onChange={e => setSelectedNetwork(e.target.value === '' ? null : Number(e.target.value))}
            className="bg-gray-800 border border-gray-700 rounded-lg px-3 py-1.5 text-white text-sm min-w-[140px]"
          >
            <option value="">All Networks</option>
            {networks.map(n => <option key={n.id} value={n.id}>{n.name}</option>)}
          </select>
        </div>

        <div className="flex items-center gap-2">
          <label className="text-gray-500 text-xs uppercase tracking-wide">Account</label>
          <select
            value={selectedAccount ?? ''}
            onChange={e => setSelectedAccount(e.target.value === '' ? null : Number(e.target.value))}
            className="bg-gray-800 border border-gray-700 rounded-lg px-3 py-1.5 text-white text-sm min-w-[180px]"
          >
            <option value="">All Accounts</option>
            {accountsForDropdown.map(a => <option key={a.id} value={a.id}>{a.label}</option>)}
          </select>
        </div>

        {(selectedNetwork !== null || selectedAccount !== null) && (
          <button onClick={() => { setSelectedNetwork(null); setSelectedAccount(null) }}
            className="text-xs text-gray-500 hover:text-white px-2 py-1 rounded-lg hover:bg-gray-800 transition-colors">
            ✕ Clear filters
          </button>
        )}

        {/* Search — push right */}
        <div className="ml-auto">
          <input type="text" placeholder="Search offer or brand…" value={search} onChange={e => setSearch(e.target.value)}
            className="bg-gray-800 border border-gray-700 rounded-lg px-3 py-1.5 text-white text-sm w-52 placeholder-gray-600" />
        </div>
      </div>

      {/* Table */}
      <div className="bg-gray-900 rounded-xl border border-gray-800 overflow-hidden">
        {loading ? (
          <div className="p-10 text-center text-gray-500">Loading…</div>
        ) : sorted.length === 0 ? (
          <div className="p-10 text-center text-gray-500">No data for this period.</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-800 bg-gray-950">
                  <th className="px-4 py-3 w-8"></th>
                  {showNetworkCol && (
                    <th className="px-4 py-3 text-left">
                      <SortBtn col="network_name" label="Network" />
                    </th>
                  )}
                  <th className="px-4 py-3 text-left text-gray-400 font-medium">Offer</th>
                  <th className="px-4 py-3 text-left text-gray-400 font-medium">Brand</th>
                  <th className="px-4 py-3 text-right"><SortBtn col="revenue" label="Revenue" /></th>
                  <th className="px-4 py-3 text-right"><SortBtn col="epc" label="EPC" /></th>
                  <th className="px-4 py-3 text-right"><SortBtn col="clicks" label="Clicks" /></th>
                  <th className="px-4 py-3 text-right"><SortBtn col="conversions" label="Conv." /></th>
                  <th className="px-4 py-3 text-right"><SortBtn col="last_seen" label="Last Seen" /></th>
                  <th className="px-4 py-3 text-center text-gray-400 font-medium">Accts</th>
                </tr>
              </thead>
              <tbody>
                {sorted.map((row, i) => {
                  const key = `${row.network_id}|${row.offer_name}|${row.brand}`
                  const isOpen = expanded.has(key)
                  const epcColor = row.epc >= 0.08 ? 'text-green-400' : row.epc >= 0.04 ? 'text-yellow-400' : 'text-red-400'
                  return (
                    <>
                      <tr key={key} onClick={() => toggleExpand(key)}
                        className={`border-b border-gray-800 cursor-pointer transition-colors ${i % 2 === 0 ? 'bg-gray-900 hover:bg-gray-800' : 'bg-gray-900/60 hover:bg-gray-800'}`}>
                        <td className="px-4 py-3 text-gray-600 text-center">{isOpen ? '▾' : '▸'}</td>
                        {showNetworkCol && (
                          <td className="px-4 py-3">{networkBadge(row.network_name)}</td>
                        )}
                        <td className="px-4 py-3 text-white max-w-xs">
                          <span className="line-clamp-2 leading-snug">{row.offer_name}</span>
                        </td>
                        <td className="px-4 py-3">
                          {row.brand
                            ? <span className="bg-blue-900/50 text-blue-300 px-2 py-0.5 rounded-full text-xs font-mono">{row.brand}</span>
                            : <span className="text-gray-600 text-xs">—</span>}
                        </td>
                        <td className="px-4 py-3 text-right text-white font-semibold">{fmt(row.revenue)}</td>
                        <td className={`px-4 py-3 text-right font-mono text-xs ${epcColor}`}>{fmtEpc(row.epc)}</td>
                        <td className="px-4 py-3 text-right text-gray-300">{fmtNum(row.clicks)}</td>
                        <td className="px-4 py-3 text-right text-gray-300">{row.conversions}</td>
                        <td className="px-4 py-3 text-right text-gray-500 text-xs">{row.last_seen ?? '—'}</td>
                        <td className="px-4 py-3 text-center">
                          <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${row.account_count >= 2 ? 'bg-green-900/50 text-green-400' : 'bg-gray-800 text-gray-500'}`}>
                            {row.account_count === 1 ? '1 acct' : `${row.account_count} accts`}
                          </span>
                        </td>
                      </tr>

                      {isOpen && (
                        <tr key={`${key}-detail`} className="border-b border-gray-800 bg-gray-950">
                          <td colSpan={showNetworkCol ? 10 : 9} className="px-6 py-3">
                            <div className="text-xs text-gray-500 uppercase tracking-wide mb-2">
                              Per-account breakdown · {periodLabel}
                            </div>
                            <div className="flex flex-wrap gap-3">
                              {row.accounts.map(acct => (
                                <div key={`${acct.account_id}-${acct.account_label}`}
                                  className="bg-gray-900 rounded-lg px-4 py-2 border border-gray-800 min-w-[180px]">
                                  <div className="flex items-center gap-2 mb-1">
                                    {networkBadge(acct.network_name)}
                                    <span className="text-gray-300 text-xs font-medium">{acct.account_label}</span>
                                  </div>
                                  <div className="text-white font-semibold">{fmt(acct.revenue)}</div>
                                  <div className="text-gray-500 text-xs mt-0.5">
                                    {fmtNum(acct.clicks)} clicks · {acct.conversions} conv.
                                  </div>
                                </div>
                              ))}
                            </div>
                            {row.first_seen && (
                              <div className="mt-2 text-gray-600 text-xs">Active: {row.first_seen} → {row.last_seen}</div>
                            )}
                          </td>
                        </tr>
                      )}
                    </>
                  )
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>

      <div className="text-gray-600 text-xs text-right">
        {sorted.length} offer/brand combination{sorted.length !== 1 ? 's' : ''} · {periodLabel}
        {selectedNetwork !== null && ` · ${networks.find(n => n.id === selectedNetwork)?.name}`}
        {selectedAccount !== null && ` · ${accounts.find(a => a.id === selectedAccount)?.label}`}
      </div>
    </div>
  )
}
