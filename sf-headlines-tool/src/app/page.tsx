'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import MeetingSelector from '@/components/MeetingSelector';
import LoadingSpinner from '@/components/LoadingSpinner';
import InitialsPrompt from '@/components/InitialsPrompt';
import { Meeting } from '@/types';

export default function HomePage() {
  const router = useRouter();
  const [userInitials, setUserInitials] = useState('');
  const [isProcessing, setIsProcessing] = useState(false);
  const [meetings, setMeetings] = useState<Meeting[]>([]);
  const [isLoadingMeetings, setIsLoadingMeetings] = useState(true);

  // Fetch meetings from API on mount
  useEffect(() => {
    const fetchMeetings = async () => {
      try {
        const response = await fetch('/api/meetings');
        const data = await response.json();
        setMeetings(data);
      } catch (error) {
        console.error('Error fetching meetings:', error);
      } finally {
        setIsLoadingMeetings(false);
      }
    };

    fetchMeetings();
  }, []);

  const handleMeetingSelect = async (meetingId: string) => {
    setIsProcessing(true);

    // Simulate processing time
    setTimeout(() => {
      router.push(`/headlines?meeting=${meetingId}&initials=${userInitials}`);
    }, 2000);
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-blue-900 to-slate-900 text-white overflow-hidden">
      <div className="text-center pt-8 pb-4">
        <h1 className="text-6xl font-bold mb-2 bg-gradient-to-r from-blue-400 to-cyan-400 bg-clip-text text-transparent">
          SF Board Headlines Research Tool
        </h1>
        <p className="text-lg text-gray-300">Analyze potential headlines from board of supervisors meetings</p>

        <InitialsPrompt
          userInitials={userInitials}
          onInitialsSet={setUserInitials}
        />
      </div>

      {isLoadingMeetings ? (
        <LoadingSpinner
          message="Loading meetings..."
          submessage="Fetching available meetings"
        />
      ) : isProcessing ? (
        <LoadingSpinner
          message="Analyzing meeting transcripts..."
          submessage="Generating potential headlines"
        />
      ) : (
        <MeetingSelector
          onMeetingSelect={handleMeetingSelect}
        />
      )}
    </div>
  );
}