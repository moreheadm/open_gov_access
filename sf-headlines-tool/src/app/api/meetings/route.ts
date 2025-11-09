import { NextResponse } from 'next/server';
import { meetings } from '@/data/meetings';

export async function GET() {
  // In a real app, this would fetch from a database
  return NextResponse.json(meetings);
}