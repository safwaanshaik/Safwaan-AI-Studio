'use client'

import React, { useState } from 'react'
import { useRouter } from 'next/navigation'

export default function StudioPage() {
  const [trend, setTrend] = useState('')
  const [duration, setDuration] = useState(30)
  const [isGenerating, setIsGenerating] = useState(false)
  const router = useRouter()

  const handleGenerate = async () => {
    if (!trend.trim()) {
      alert('Please enter a trend or topic')
      return
    }

    setIsGenerating(true)
    try {
      const response = await fetch('/api/generate-video', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          prompt: trend,
          duration: duration,
          auto_post: true
        }),
      })

      if (!response.ok) {
        throw new Error('Failed to generate video')
      }

      const data = await response.json()
      router.push(`/preview/${data.id}`)
    } catch (error) {
      console.error('Error generating video:', error)
      alert('Failed to generate video. Please try again.')
    } finally {
      setIsGenerating(false)
    }
  }

  const handleTrySample = () => {
    setTrend('AI Music Revolution 2024')
    setDuration(30)
  }

  return (
    <div className="app-content p-6 max-w-5xl mx-auto">
      <div className="bg-slate-900/60 p-6 rounded-lg">
        <h1 className="text-2xl font-bold mb-6">Create New Cinematic Video</h1>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-2">
              Trend / Topic
            </label>
            <input
              type="text"
              value={trend}
              onChange={(e) => setTrend(e.target.value)}
              className="w-full p-3 bg-black/40 rounded-lg border border-gray-600 focus:border-indigo-500 focus:outline-none text-white"
              placeholder="e.g. AI Technology, Space Exploration, Cooking Tips..."
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-300 mb-2">
              Duration (seconds)
            </label>
            <input
              type="range"
              min="15"
              max="90"
              value={duration}
              onChange={(e) => setDuration(Number(e.target.value))}
              className="w-full h-2 bg-gray-700 rounded-lg appearance-none cursor-pointer"
            />
            <div className="text-center mt-2 text-gray-300 font-semibold">
              {duration} seconds
            </div>
          </div>
        </div>

        <div className="mt-8 flex gap-4">
          <button
            onClick={handleGenerate}
            disabled={isGenerating || !trend.trim()}
            className="glow-button px-6 py-3 bg-gradient-to-r from-green-600 to-emerald-600 text-white rounded-lg hover:from-green-700 hover:to-emerald-700 transition-all disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
          >
            {isGenerating ? (
              <>
                <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
                Generating...
              </>
            ) : (
              <>
                🎬 Generate Video
              </>
            )}
          </button>

          <button
            onClick={handleTrySample}
            className="px-6 py-3 bg-gray-700 text-white rounded-lg hover:bg-gray-600 transition-colors"
          >
            Try Sample
          </button>
        </div>

        <div className="mt-6 p-4 bg-blue-900/20 rounded-lg border border-blue-500/30">
          <h3 className="text-lg font-semibold text-blue-300 mb-2">What happens next?</h3>
          <ul className="text-sm text-gray-300 space-y-1">
            <li>🎯 AI analyzes your trend for viral potential</li>
            <li>🎬 Generates a professional HD video using advanced AI models</li>
            <li>📤 Automatically posts to YouTube, TikTok, Instagram, and Facebook</li>
            <li>💰 Tracks revenue from all platforms in real-time</li>
            <li>📊 Sends automated performance reports</li>
          </ul>
        </div>
      </div>
    </div>
  )
}