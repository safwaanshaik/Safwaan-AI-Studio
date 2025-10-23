import { NextRequest, NextResponse } from 'next/server'

export async function GET(request: NextRequest) {
  try {
    // Get the backend URL from environment or construct it
    const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000'

    // Forward the request to the backend
    const backendResponse = await fetch(`${backendUrl}/stats`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
    })

    if (!backendResponse.ok) {
      throw new Error(`Backend responded with status: ${backendResponse.status}`)
    }

    const data = await backendResponse.json()

    // Transform backend data to frontend format
    const analytics = {
      totalRevenue: data.total_revenue || 0,
      monthlyRevenue: data.monthly_revenue || 0,
      platformBreakdown: data.platform_revenue || {},
      recentTransactions: data.recent_transactions || [],
      totalVideos: data.total_videos || 0,
      activeTrends: 0 // This would need to be added to backend /stats endpoint
    }

    return NextResponse.json(analytics)
  } catch (error) {
    console.error('Analytics API error:', error)
    return NextResponse.json(
      {
        totalRevenue: 0,
        monthlyRevenue: 0,
        platformBreakdown: {},
        recentTransactions: [],
        totalVideos: 0,
        activeTrends: 0
      },
      { status: 500 }
    )
  }
}