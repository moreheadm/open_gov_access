'use client';

import { useState, useEffect, Suspense } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { Circle } from 'lucide-react';
import SupervisorWheel from '@/components/SupervisorWheel';
import HeadlineCard from '@/components/HeadlineCard';
import InitialsPrompt from '@/components/InitialsPrompt';
import LoadingSpinner from '@/components/LoadingSpinner';
import { supervisors } from '@/data/supervisors';
import { HeadlinesData, Headline } from '@/types';

function HeadlinesContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const meetingId = searchParams.get('meeting');
  const initialInitials = searchParams.get('initials') || '';

  const [userInitials, setUserInitials] = useState(initialInitials);
  const [headlines, setHeadlines] = useState<HeadlinesData>({});
  const [meetingTitle, setMeetingTitle] = useState<string | null>(null);
  const [meetingDatetime, setMeetingDatetime] = useState<string | null>(null);
  const [selectedSupervisor, setSelectedSupervisor] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    // Fetch headlines from API
    const fetchHeadlines = async () => {
      try {
        const response = await fetch(`/api/headlines?meetingId=${meetingId}`);
        const data = await response.json();
        setHeadlines(data.headlines || data); // Support both new and old format
        if (data.meeting) {
          setMeetingTitle(data.meeting.title);
          setMeetingDatetime(data.meeting.datetime);
        }
      } catch (error) {
        console.error('Error fetching headlines:', error);
      } finally {
        setIsLoading(false);
      }
    };

    if (meetingId) {
      fetchHeadlines();
    }
  }, [meetingId]);

  const handleFactCheck = (supervisorId: string, headlineId: string) => {
    // This is just for UI state, actual submission happens in handleSubmitFactCheck
  };

  const handleSubmitFactCheck = async (supervisorId: string, headlineId: string, note: string) => {
    setHeadlines(prev => ({
      ...prev,
      [supervisorId]: prev[supervisorId].map(headline => {
        if (headline.id === headlineId) {
          const newCheckedBy = [...headline.checkedBy, userInitials];
          const newFactChecks = newCheckedBy.length;
          
          return { 
            ...headline, 
            factChecks: newFactChecks, 
            isActive: newFactChecks >= 2,
            checkedBy: newCheckedBy
          };
        }
        return headline;
      })
    }));

    // In a real app, you'd send this to an API
    // await fetch('/api/fact-check', { method: 'POST', body: JSON.stringify({ headlineId, note, userInitials }) });
  };

  const handleGetSentiment = async (supervisorId: string, headlineId: string) => {
    setHeadlines(prev => ({
      ...prev,
      [supervisorId]: prev[supervisorId].map(headline => {
        if (headline.id === headlineId) {
          return { ...headline, loadingSentiment: true };
        }
        return headline;
      })
    }));

    try {
      const response = await fetch(`/api/sentiment?headlineId=${headlineId}`);
      const data = await response.json();
      
      setHeadlines(prev => ({
        ...prev,
        [supervisorId]: prev[supervisorId].map(headline => {
          if (headline.id === headlineId) {
            return { 
              ...headline, 
              sentiment: data.score,
              loadingSentiment: false
            };
          }
          return headline;
        })
      }));
    } catch (error) {
      console.error('Error fetching sentiment:', error);
      setHeadlines(prev => ({
        ...prev,
        [supervisorId]: prev[supervisorId].map(headline => {
          if (headline.id === headlineId) {
            return { ...headline, loadingSentiment: false };
          }
          return headline;
        })
      }));
    }
  };

  const handleBackToMeetings = () => {
    router.push('/');
  };

  const selectedSupervisorData = supervisors.find(s => s.id === selectedSupervisor);

  if (isLoading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-900 via-blue-900 to-slate-900 text-white">
        <LoadingSpinner message="Loading headlines..." />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-blue-900 to-slate-900 text-white overflow-hidden">
      <div className="text-center pt-8 pb-4">
        <h1 className="text-6xl font-bold mb-2 bg-gradient-to-r from-blue-400 to-cyan-400 bg-clip-text text-transparent">
          SF Board Headlines Research Tool
        </h1>
        <p className="text-lg text-gray-300">Analyze potential headlines from board of supervisors meetings</p>

        {meetingTitle && (
          <div className="mt-4 mb-2">
            <h2 className="text-2xl font-semibold text-blue-300">{meetingTitle}</h2>
            {meetingDatetime && (
              <p className="text-sm text-gray-400 mt-1">
                {new Date(meetingDatetime).toLocaleDateString('en-US', {
                  weekday: 'long',
                  year: 'numeric',
                  month: 'long',
                  day: 'numeric',
                  hour: 'numeric',
                  minute: '2-digit'
                })}
              </p>
            )}
          </div>
        )}

        <InitialsPrompt
          userInitials={userInitials}
          onInitialsSet={setUserInitials}
        />
      </div>

      <div className="flex flex-col lg:flex-row items-start justify-center gap-8 px-8 py-8">
        <SupervisorWheel
          supervisors={supervisors}
          headlines={headlines}
          selectedSupervisor={selectedSupervisor}
          onSupervisorSelect={setSelectedSupervisor}
          onBackToMeetings={handleBackToMeetings}
        />

        <div className="w-full lg:w-1/2">
          <div className="bg-gray-800/50 backdrop-blur-sm rounded-2xl p-8 border border-gray-700 min-h-[500px]">
            <h2 className="text-3xl font-bold mb-6">
              {selectedSupervisorData?.name || 'Select a Supervisor'}
            </h2>
            
            {selectedSupervisor && headlines[selectedSupervisor]?.map(headline => (
              <HeadlineCard
                key={headline.id}
                headline={headline}
                supervisor={selectedSupervisorData!}
                userInitials={userInitials}
                onFactCheck={(headlineId) => handleFactCheck(selectedSupervisor, headlineId)}
                onSubmitFactCheck={(headlineId, note) => handleSubmitFactCheck(selectedSupervisor, headlineId, note)}
                onGetSentiment={(headlineId) => handleGetSentiment(selectedSupervisor, headlineId)}
              />
            ))}
            
            {!selectedSupervisor && (
              <div className="text-center text-gray-400 py-24">
                <Circle className="w-16 h-16 mx-auto mb-4 opacity-50" />
                <p className="text-xl">Click a supervisor in the wheel to view their headlines</p>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

export default function HeadlinesPage() {
  return (
    <Suspense fallback={<LoadingSpinner />}>
      <HeadlinesContent />
    </Suspense>
  );
}