import { useState } from 'react'
import api from '../api'

export default function Suggestions() {
  const [result, setResult] = useState<any>(null)
  const [loading, setLoading] = useState(false)
  const [lookback, setLookback] = useState(90)

  const fetchSuggestions = async () => {
    setLoading(true)
    try {
      const res = await api.get(`/suggestions?lookback_days=${lookback}`)
      setResult(res.data)
    } catch (e: any) {
      setResult({ suggestions: 'Error: ' + (e.response?.data?.detail || e.message) })
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="space-y-4">
      <h1 className="text-xl font-bold text-white">AI Suggestions</h1>
      <div className="bg-gray-900 rounded-xl border border-gray-800 p-4">
        <div className="text-gray-400 text-sm mb-4">
          Analyzes your last N days of campaign performance, mailing events, and revenue trends
          to suggest what to run, what to revive, and what to pause.
        </div>
        <div className="flex items-center gap-3">
          <select
            className="bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white"
            value={lookback}
            onChange={e => setLookback(parseInt(e.target.value))}
          >
            <option value={30}>Last 30 days</option>
            <option value={60}>Last 60 days</option>
            <option value={90}>Last 90 days</option>
            <option value={180}>Last 180 days</option>
            <option value={365}>Last 365 days</option>
          </select>
          <button
            onClick={fetchSuggestions}
            disabled={loading}
            className="bg-green-500 text-black px-6 py-2 rounded-lg text-sm font-bold hover:bg-green-400 disabled:opacity-50 transition"
          >
            {loading ? 'Analyzing...' : 'Get AI Suggestions'}
          </button>
        </div>
      </div>

      {result && (
        <div className="bg-gray-900 rounded-xl border border-gray-800 p-5">
          <div className="text-green-400 text-sm font-medium mb-3">
            GPT-4 Analysis {result.model && `(${result.model})`}
            {result.tokens_used && <span className="text-gray-600 ml-2">{result.tokens_used} tokens</span>}
          </div>
          <div className="text-gray-300 text-sm whitespace-pre-wrap leading-relaxed">{result.suggestions}</div>
          {result.raw_context && (
            <details className="mt-4">
              <summary className="text-gray-600 text-xs cursor-pointer hover:text-gray-400">View raw context sent to AI</summary>
              <pre className="mt-2 text-gray-700 text-xs font-mono whitespace-pre-wrap overflow-auto max-h-64">{result.raw_context}</pre>
            </details>
          )}
        </div>
      )}
    </div>
  )
}
