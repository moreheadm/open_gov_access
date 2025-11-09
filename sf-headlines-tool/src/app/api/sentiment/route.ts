import { NextResponse } from 'next/server';

export async function GET(request: Request) {
  const { searchParams } = new URL(request.url);
  const headlineId = searchParams.get('headlineId');

  // Simulate API processing time
  await new Promise(resolve => setTimeout(resolve, 1500));

  // In a real app, this would:
  // 1. Fetch the headline text
  // 2. Analyze sentiment using AI or sentiment analysis API
  // 3. Return the sentiment score
  
  // For now, return a random score
  const randomScore = Math.floor(Math.random() * 10) + 1;
  
  return NextResponse.json({ 
    headlineId,
    score: randomScore 
  });
}