'use client'

import React from 'react'
import Link from 'next/link'

export default function LandingPage() {
  return (
    <>
      <div className="stars" aria-hidden="true">
        <div className="star-layer layer-1"></div>
        <div className="star-layer layer-2"></div>
        <div className="star-layer layer-3"></div>
      </div>

      <main className="app-content min-h-screen flex flex-col items-center justify-center px-6">
        <header className="text-center mb-8">
          <h1 className="text-4xl md:text-6xl font-extrabold leading-tight">
            CINEMATRIX AI
          </h1>
          <p className="mt-4 text-lg text-gray-300 max-w-2xl">
            Auto trending cinematic videos — AI-powered, optimized for social.
          </p>
        </header>

        <div className="w-full max-w-4xl grid grid-cols-1 md:grid-cols-2 gap-6">
          <div className="p-6 bg-gradient-to-tr from-slate-900/70 to-slate-800/60 rounded-lg">
            <h2 className="text-xl font-semibold">Studio</h2>
            <p className="mt-2 text-sm text-gray-300">
              Pick trend — generate — preview — publish.
            </p>
            <Link href="/studio" className="inline-block mt-4 px-5 py-3 bg-indigo-600 rounded-lg text-white hover:bg-indigo-700 transition-colors">
              Open Studio
            </Link>
          </div>

          <div className="p-6 bg-gradient-to-tr from-slate-900/70 to-slate-800/60 rounded-lg">
            <h2 className="text-xl font-semibold">Analytics</h2>
            <p className="mt-2 text-sm text-gray-300">
              Track revenue from YouTube, TikTok, and Instagram.
            </p>
            <Link href="/analytics" className="inline-block mt-4 px-5 py-3 bg-green-600 rounded-lg text-white hover:bg-green-700 transition-colors">
              View Analytics
            </Link>
          </div>
        </div>

        <footer className="mt-12 text-sm text-gray-400">
          Mobile-ready • Beauty-first UI • Live progress
        </footer>
      </main>
    </>
  )
}