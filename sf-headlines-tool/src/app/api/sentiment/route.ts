import { NextResponse } from 'next/server';

export async function GET(request: Request) {
  const { searchParams } = new URL(request.url);
  const headlineId = searchParams.get('headlineId');

  try {
    // Try to fetch from your real sentiment analysis API
    const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/sentiment/${headlineId}`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
      signal: AbortSignal.timeout(10000), // 10 second timeout for AI processing
    });

    if (!response.ok) {
      throw new Error(`API responded with status: ${response.status}`);
    }

    const data = await response.json();
    return NextResponse.json(data);
    
  } catch (error) {
    console.error('Failed to fetch sentiment from API, using random score:', error);
    
    // Simulate processing time
    await new Promise(resolve => setTimeout(resolve, 1500));
    
    // Fallback to random score
    const randomScore = Math.floor(Math.random() * 10) + 1;
    
    return NextResponse.json({ 
      headlineId,
      score: randomScore,
      isMock: true // Flag to indicate this is mock data
    });
  }
}