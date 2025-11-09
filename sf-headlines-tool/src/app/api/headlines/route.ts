import { NextResponse } from 'next/server';
import { mockHeadlinesData } from '@/data/mockHeadlines';
import { fetchWithFallback } from '@/lib/api';

export async function GET(request: Request) {
  const { searchParams } = new URL(request.url);
  const meetingId = searchParams.get('meetingId');

  const data = await fetchWithFallback(
    `${process.env.NEXT_PUBLIC_API_URL}/api/headlines/${meetingId}`,
    mockHeadlinesData
  );

  return NextResponse.json(data);
}