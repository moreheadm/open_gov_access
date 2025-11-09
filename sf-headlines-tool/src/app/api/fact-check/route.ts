import { NextResponse } from 'next/server';
import { postWithFallback } from '@/lib/api';

export async function POST(request: Request) {
  const body = await request.json();
  const { headlineId, note, userInitials } = body;

  // Generate fallback response
  const fallbackData = {
    success: true,
    headlineId,
    userInitials,
    timestamp: new Date().toISOString(),
    isMock: true
  };

  const data = await postWithFallback(
    `${process.env.NEXT_PUBLIC_API_URL}/api/fact-check`,
    { headlineId, note, userInitials },
    fallbackData
  );

  return NextResponse.json(data);
}