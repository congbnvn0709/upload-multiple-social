import React, { useState, useEffect } from 'react'

export default function App() {
  const [healthStatus, setHealthStatus] = useState('checking...')

  useEffect(() => {
    fetch('/api/health')
      .then(res => res.json())
      .then(data => setHealthStatus(data.status))
      .catch(() => setHealthStatus('disconnected'))
  }, [])

  return (
    <div className="min-h-screen bg-slate-900 text-slate-100 p-8">
      <header className="mb-8">
        <h1 className="text-3xl font-bold">Multi-Platform Social Video Publisher</h1>
        <p className="text-slate-400 mt-2">Backend Status: <span className="font-semibold text-emerald-400">{healthStatus}</span></p>
      </header>
    </div>
  )
}
