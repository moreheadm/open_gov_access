import { NextResponse } from 'next/server';
import { mockHeadlinesData } from '@/data/mockHeadlines';
import { getOfficialIdFromName } from '@/data/supervisors';
import { HeadlinesData, Headline } from '@/types';

// Backend API configuration
const BACKEND_API_URL = process.env.BACKEND_API_URL || 'http://localhost:8000';

interface MomentSummary {
  id: string;
  headline: string;
  summary: string;
  timestamps: string;
}

interface PersonSummary {
  name: string;
  role: string;
  moments: MomentSummary[];
}

interface MeetingSummaryResponse {
  meeting_id: number;
  meeting_title?: string;
  meeting_datetime: string;
  people: PersonSummary[];
}

export async function GET(request: Request) {
  const { searchParams } = new URL(request.url);
  const meetingId = searchParams.get('meetingId');

  if (!meetingId) {
    return NextResponse.json({ error: 'Meeting ID is required' }, { status: 400 });
  }

  try {
    // Call the backend API to get meeting summary
    const response = await fetch(`${BACKEND_API_URL}/api/meetings/${meetingId}/summary`, {
      headers: {
        'Accept': 'application/json',
      },
    });

    if (!response.ok) {
      console.error(`Backend API error: ${response.status} ${response.statusText}`);
      // Fallback to mock data if backend fails
      return NextResponse.json(mockHeadlinesData);
    }

    const data: MeetingSummaryResponse = await response.json();

    // Transform backend response to frontend format
    const headlines: HeadlinesData = {};

    for (const person of data.people) {
      // Clean up the name - remove "Supervisor" prefix if present
      const cleanName = person.name.replace(/^Supervisor\s+/i, '').trim();

      // Get official ID from name (works for both supervisors and mayor)
      const officialId = getOfficialIdFromName(cleanName);

      if (!officialId) {
        console.warn(`Could not find official ID for: ${person.name} (cleaned: ${cleanName})`);
        continue;
      }

      // Transform moments into headlines
      headlines[officialId] = person.moments.map((moment, index) => {
        // Format the text: <strong>(headline)</strong> summary [timestamps]
        const formattedText = `<strong>(${moment.headline})</strong> ${moment.summary} [${moment.timestamps}]`;

        const headline: Headline = {
          id: `${officialId}-${moment.id}`,
          text: formattedText,
          factChecks: 0,
          isActive: false,
          checkedBy: [],
          sentiment: null,
          loadingSentiment: false,
        };

        return headline;
      });
    }

    // Return both headlines and meeting metadata
    return NextResponse.json({
      headlines,
      meeting: {
        id: data.meeting_id,
        title: data.meeting_title,
        datetime: data.meeting_datetime,
      }
    });

  } catch (error) {
    console.error('Error fetching meeting summary:', error);
    // Fallback to mock data on error
    return NextResponse.json({
      headlines: mockHeadlinesData,
      meeting: null
    });
  }
}