'use client';

import { useState, useEffect } from 'react';
import { TrendingUp, ChevronDown } from 'lucide-react';
import { Meeting } from '@/types';

interface MeetingSelectorProps {
  onMeetingSelect: (meetingId: string) => void;
}

export default function MeetingSelector({ onMeetingSelect }: MeetingSelectorProps) {
  const [selectedMonth, setSelectedMonth] = useState('all');
  const [meetings, setMeetings] = useState<Meeting[]>([]);
  const [uniqueMonths, setUniqueMonths] = useState<string[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Fetch all meetings on initial load to get unique months
  useEffect(() => {
    const fetchAllMeetings = async () => {
      try {
        const response = await fetch('/api/meetings?month=all');
        if (!response.ok) throw new Error('Failed to fetch meetings');

        const data = await response.json();

        // Extract unique months for the dropdown
        const months = [...new Set(data.map((m: Meeting) => m.month))].sort().reverse();
        setUniqueMonths(months);
        setIsLoading(false);
      } catch (err) {
        setError('Failed to load meetings');
        setIsLoading(false);
      }
    };

    fetchAllMeetings();
  }, []);

  // Fetch meetings when month changes
  useEffect(() => {
    const fetchMeetingsByMonth = async () => {
      setIsLoading(true);
      try {
        const response = await fetch(`/api/meetings?month=${selectedMonth}`);
        if (!response.ok) throw new Error('Failed to fetch meetings');

        const data = await response.json();
        setMeetings(data);
        setError(null);
      } catch (err) {
        setError('Failed to load meetings for selected month');
      } finally {
        setIsLoading(false);
      }
    };

    // Always fetch when month changes (including when it changes to 'all')
    fetchMeetingsByMonth();
  }, [selectedMonth]);

  const formatMonth = (monthStr: string) => {
    const [year, month] = monthStr.split('-');
    const date = new Date(parseInt(year), parseInt(month) - 1);
    return date.toLocaleDateString('en-US', { month: 'long', year: 'numeric' });
  };

  return (
    <div className="flex items-center justify-center min-h-[70vh] px-8">
      <div className="w-full max-w-2xl">
        <div className="text-center mb-8">
          <TrendingUp className="w-20 h-20 mx-auto mb-4 text-blue-400" />
          <h2 className="text-3xl font-bold mb-2">Select a Meeting</h2>
          <p className="text-gray-400">Choose a board meeting to analyze headline sentiment</p>
        </div>

        <div className="mb-6">
          <label className="block text-sm font-semibold text-gray-300 mb-2">
            Filter by Month
          </label>
          <select
            value={selectedMonth}
            onChange={(e) => setSelectedMonth(e.target.value)}
            className="w-full px-4 py-3 bg-gray-800 text-white rounded-lg border border-gray-700 focus:border-blue-500 focus:outline-none cursor-pointer"
            disabled={isLoading}
          >
            <option value="all">All Meetings</option>
            {uniqueMonths.map(month => (
              <option key={month} value={month}>
                {formatMonth(month)}
              </option>
            ))}
          </select>
        </div>
        
        {error && (
          <div className="mb-4 p-4 bg-red-900/30 border border-red-500 rounded-lg text-center">
            <p className="text-sm text-red-300">{error}</p>
          </div>
        )}
        
        <div className="space-y-3 max-h-[400px] overflow-y-auto pr-2">
          {isLoading ? (
            <div className="text-center py-12">
              <div className="animate-spin w-12 h-12 border-4 border-blue-500 border-t-transparent rounded-full mx-auto mb-4"></div>
              <p className="text-gray-400">Loading meetings...</p>
            </div>
          ) : meetings.length > 0 ? (
            meetings.map(meeting => (
              <button
                key={meeting.id}
                onClick={() => onMeetingSelect(meeting.id)}
                className="w-full p-6 bg-gray-800/50 backdrop-blur-sm border border-gray-700 rounded-xl hover:border-blue-500 hover:bg-gray-800/70 transition-all text-left group"
              >
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-blue-400 font-semibold mb-1">{meeting.date}</p>
                    <p className="text-lg font-medium group-hover:text-blue-300 transition-colors">{meeting.title}</p>
                  </div>
                  <ChevronDown className="w-6 h-6 text-gray-500 group-hover:text-blue-400 transform -rotate-90" />
                </div>
              </button>
            ))
          ) : (
            <div className="text-center py-12 text-gray-400">
              <p>No meetings found for this month</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}