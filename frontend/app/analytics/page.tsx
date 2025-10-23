'use client'

import React, { useState, useEffect } from 'react'

interface AnalyticsData {
  totalRevenue: number
  monthlyRevenue: number
  platformBreakdown: Record<string, number>
  recentTransactions: Array<{
    id: number
    platform: string
    amount: number
    recorded_at: string
  }>
  totalVideos: number
  activeTrends: number
}

export default function AnalyticsPage() {
  const [analytics, setAnalytics] = useState<AnalyticsData | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetchAnalytics()
  }, [])

  const fetchAnalytics = async () => {
    try {
      const response = await fetch('/api/analytics')
      if (response.ok) {
        const data = await response.json()
        setAnalytics(data)
      }
    } catch (error) {
      console.error('Failed to fetch analytics:', error)
    } finally {
      setLoading(false)
    }
  }

  if (loading) {
    return (
      <div className="app-content p-6 max-w-7xl mx-auto">
        <div className="flex items-center justify-center h-64">
          <div className="w-8 h-8 border-4 border-purple-500 border-t-transparent rounded-full animate-spin"></div>
        </div>
      </div>
    )
  }

  return (
    <div className="app-content p-6 max-w-7xl mx-auto">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-white mb-2">Revenue Analytics</h1>
        <p className="text-gray-400">Track your viral video earnings across all platforms</p>
      </div>

      {/* Key Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
        <div className="bg-white/10 backdrop-blur-lg rounded-xl p-6 border border-white/20">
          <div className="text-center">
            <div className="text-3xl font-bold text-white mb-2">
              ${analytics?.totalRevenue?.toFixed(2) || '0.00'}
            </div>
            <div className="text-gray-400">Total Revenue</div>
          </div>
        </div>

        <div className="bg-white/10 backdrop-blur-lg rounded-xl p-6 border border-white/20">
          <div className="text-center">
            <div className="text-3xl font-bold text-white mb-2">
              ${analytics?.monthlyRevenue?.toFixed(2) || '0.00'}
            </div>
            <div className="text-gray-400">This Month</div>
          </div>
        </div>

        <div className="bg-white/10 backdrop-blur-lg rounded-xl p-6 border border-white/20">
          <div className="text-center">
            <div className="text-3xl font-bold text-white mb-2">
              {analytics?.totalVideos || 0}
            </div>
            <div className="text-gray-400">Videos Generated</div>
          </div>
        </div>

        <div className="bg-white/10 backdrop-blur-lg rounded-xl p-6 border border-white/20">
          <div className="text-center">
            <div className="text-3xl font-bold text-white mb-2">
              {analytics?.activeTrends || 0}
            </div>
            <div className="text-gray-400">Active Trends</div>
          </div>
        </div>
      </div>

      {/* Platform Breakdown */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-white/10 backdrop-blur-lg rounded-xl p-6 border border-white/20">
          <h3 className="text-xl font-semibold text-white mb-4">Revenue by Platform</h3>
          <div className="space-y-3">
            {analytics?.platformBreakdown && Object.entries(analytics.platformBreakdown).map(([platform, amount]) => (
              <div key={platform} className="flex justify-between items-center">
                <span className="text-gray-300 capitalize">{platform}</span>
                <span className="text-white font-semibold">${amount.toFixed(2)}</span>
              </div>
            ))}
            {(!analytics?.platformBreakdown || Object.keys(analytics.platformBreakdown).length === 0) && (
              <p className="text-gray-400">No revenue data yet</p>
            )}
          </div>
        </div>

        <div className="bg-white/10 backdrop-blur-lg rounded-xl p-6 border border-white/20">
          <h3 className="text-xl font-semibold text-white mb-4">Recent Transactions</h3>
          <div className="space-y-3 max-h-64 overflow-y-auto">
            {analytics?.recentTransactions?.map((transaction) => (
              <div key={transaction.id} className="flex justify-between items-center py-2 border-b border-white/10">
                <div>
                  <span className="text-gray-300 capitalize">{transaction.platform}</span>
                  <div className="text-xs text-gray-500">
                    {new Date(transaction.recorded_at).toLocaleDateString()}
                  </div>
                </div>
                <span className="text-green-400 font-semibold">
                  +${transaction.amount.toFixed(2)}
                </span>
              </div>
            ))}
            {(!analytics?.recentTransactions || analytics.recentTransactions.length === 0) && (
              <p className="text-gray-400">No transactions yet</p>
            )}
          </div>
        </div>
      </div>

      {/* Performance Insights */}
      <div className="mt-8 bg-white/10 backdrop-blur-lg rounded-xl p-6 border border-white/20">
        <h3 className="text-xl font-semibold text-white mb-4">Performance Insights</h3>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="text-center">
            <div className="text-2xl font-bold text-blue-400 mb-1">
              {analytics?.totalVideos ? (analytics.totalRevenue / analytics.totalVideos).toFixed(2) : '0.00'}
            </div>
            <div className="text-sm text-gray-400">Avg Revenue per Video</div>
          </div>
          <div className="text-center">
            <div className="text-2xl font-bold text-green-400 mb-1">
              {analytics?.totalVideos && analytics?.activeTrends ?
                ((analytics.totalVideos / Math.max(analytics.activeTrends, 1)) * 100).toFixed(1) : '0.0'}%
            </div>
            <div className="text-sm text-gray-400">Trend Conversion Rate</div>
          </div>
          <div className="text-center">
            <div className="text-2xl font-bold text-purple-400 mb-1">
              {analytics?.monthlyRevenue ? (analytics.monthlyRevenue * 12).toFixed(2) : '0.00'}
            </div>
            <div className="text-sm text-gray-400">Projected Annual Revenue</div>
          </div>
        </div>
      </div>
    </div>
  )
}