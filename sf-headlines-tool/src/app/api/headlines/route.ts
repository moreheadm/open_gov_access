import { NextResponse } from 'next/server';
import { mockHeadlinesData } from '@/data/mockHeadlines';

export async function GET(request: Request) {
  const { searchParams } = new URL(request.url);
  const meetingId = searchParams.get('meetingId');

  // In a real app, this would:
  // 1. Fetch the meeting transcript from a database
  // 2. Process it with AI to generate headlines
  // 3. Return the generated headlines
  
  // For now, we return mock data
  return NextResponse.json(mockHeadlinesData);
}