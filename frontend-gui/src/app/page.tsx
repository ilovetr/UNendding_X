'use client'

import { useEffect } from 'react'
import { useRouter } from 'next/navigation'

export default function Home() {
  const router = useRouter()

  useEffect(() => {
    // Redirect to dashboard - this is the local GUI, not the public website
    router.replace('/dashboard')
  }, [router])

  return (
    <div className="min-h-screen flex items-center justify-center bg-slate-50">
      <div className="text-center">
        <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center mx-auto mb-4">
          <span className="text-white font-bold text-sm">川</span>
        </div>
        <p className="text-slate-500 text-sm">川流 · UnendingX GUI</p>
        <p className="text-slate-400 text-xs mt-1">Loading...</p>
      </div>
    </div>
  )
}
