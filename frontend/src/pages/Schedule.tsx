export default function Schedule() {
  return (
    <div className="space-y-4">
      <h1 className="text-xl font-bold text-white">Schedule</h1>
      <div className="bg-gray-900 rounded-xl border border-gray-800 p-8 text-center">
        <div className="text-4xl mb-4">📅</div>
        <div className="text-white font-semibold text-lg mb-2">Coming Soon</div>
        <div className="text-gray-500 text-sm max-w-md mx-auto">
          AI-powered mailing schedule optimization. This will analyze your campaign
          performance, mailing events, and affiliate revenue data to suggest the
          optimal send schedule to maximize daily revenue.
        </div>
        <div className="mt-6 space-y-2 text-left max-w-sm mx-auto">
          {[
            'AI-suggested send times based on conversion patterns',
            'List performance scoring and rotation',
            'Campaign pairing recommendations',
            'Revenue-maximizing weekly schedule',
          ].map((f) => (
            <div key={f} className="flex items-center gap-2 text-gray-600 text-sm">
              <span className="text-gray-700">○</span> {f}
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
