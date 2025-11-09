import { NextResponse } from 'next/server';
import { meetings } from '@/data/meetings';
import { fetchWithFallback } from '@/lib/api';

export async function GET(request: Request) {
  const { searchParams } = new URL(request.url);
  const month = searchParams.get('month') || 'all';

  // Filter meetings by month for fallback data
  const filteredMeetings = month === 'all' 
    ? meetings 
    : meetings.filter(m => m.month === month);

  const data = await fetchWithFallback(
    `${process.env.NEXT_PUBLIC_API_URL}/api/meetings${month !== 'all' ? `?month=${month}` : ''}`,
    filteredMeetings
  );

  return NextResponse.json(data);
}
// import { NextResponse } from 'next/server';
// import { fetchWithFallback } from '@/lib/api';

// export async function GET(request: Request) {
//   const { searchParams } = new URL(request.url);
//   const headlineId = searchParams.get('headlineId');

//   // Generate fallback data
//   const fallbackData = {
//     headlineId,
//     score: Math.floor(Math.random() * 10) + 1,
//     isMock: true
//   };

//   // Add artificial delay for fallback to simulate processing
//   const dataWithDelay = await new Promise(async (resolve) => {
//     const data = await fetchWithFallback(
//       `${process.env.NEXT_PUBLIC_API_URL}/api/sentiment/${headlineId}`,
//       fallbackData,
//       {
//         signal: AbortSignal.timeout(10000), // 10 second timeout for AI processing
//       }
//     );
    
//     // If using mock data, add delay to simulate processing
//     if (data.isMock) {
//       setTimeout(() => resolve(data), 1500);
//     } else {
//       resolve(data);
//     }
//   });

//   return NextResponse.json(dataWithDelay);
// }