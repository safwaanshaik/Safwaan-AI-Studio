import { NextRequest, NextResponse } from 'next/server'

export async function POST(request: NextRequest) {
  try {
    const body = await request.json()
    const { prompt, duration = 30, auto_post = true } = body

    if (!prompt || typeof prompt !== 'string' || prompt.length < 10) {
      return NextResponse.json(
        { error: 'Prompt must be at least 10 characters long' },
        { status: 400 }
      )
    }

    // Call the backend API
    const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000'
    const response = await fetch(`${backendUrl}/generate-video`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ prompt, duration, auto_post }),
    })

    if (!response.ok) {
      const error = await response.text()
      return NextResponse.json(
        { error: `Backend error: ${error}` },
        { status: response.status }
      )
    }

    const data = await response.json()
    return NextResponse.json(data)

  } catch (error) {
    console.error('API route error:', error)
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    )
  }
}