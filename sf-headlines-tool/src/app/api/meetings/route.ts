import { NextResponse } from 'next/server';
import { meetings } from '@/data/meetings';

// Backend API configuration
const BACKEND_API_URL = process.env.BACKEND_API_URL || 'http://localhost:8000';

interface BackendMeeting {
  id: number;
  meeting_datetime: string;
  meeting_type: string;
}

export async function GET() {
  try {
    // Fetch meetings from backend API
    const response = await fetch(`${BACKEND_API_URL}/api/meetings?limit=50`, {
      headers: {
        'Accept': 'application/json',
      },
    });

    if (!response.ok) {
      console.error(`Backend API error: ${response.status} ${response.statusText}`);
      // Fallback to mock data if backend fails
      return NextResponse.json(meetings);
    }

    const backendMeetings: BackendMeeting[] = await response.json();

    // Transform backend meetings to frontend format
    const transformedMeetings = backendMeetings.map(meeting => {
      const date = new Date(meeting.meeting_datetime);
      const dateStr = date.toISOString().split('T')[0]; // YYYY-MM-DD
      const month = dateStr.substring(0, 7); // YYYY-MM

      return {
        id: meeting.id.toString(), // Convert to string for frontend
        date: dateStr,
        title: `Board of Supervisors ${meeting.meeting_type.charAt(0).toUpperCase() + meeting.meeting_type.slice(1)} Meeting - ${date.toLocaleDateString('en-US', { month: 'long', day: 'numeric', year: 'numeric' })}`,
        month: month,
      };
    });

    return NextResponse.json(transformedMeetings);

  } catch (error) {
    console.error('Error fetching meetings:', error);
    // Fallback to mock data on error
    return NextResponse.json(meetings);
  }
}
