'use client';

import { useState } from 'react';
import { TrendingUp, ChevronDown } from 'lucide-react';
import { Meeting } from '@/types';

interface MeetingSelectorProps {
  meetings: Meeting[];
  onMeetingSelect: (meetingId: string) => void;
}

export default function MeetingSelector({ meetings, onMeetingSelect }: MeetingSelectorProps) {
  const [selectedMonth, setSelectedMonth] = useState('all');

  const uniqueMonths = [...new Set(meetings.map(m => m.month))].sort().reverse();
  
  const formatMonth = (monthStr: string) => {
    const [year, month] = monthStr.split('-');
    const date = new Date(parseInt(year), parseInt(month) - 1);
    return date.toLocaleDateString('en-US', { month: 'long', year: 'numeric' });
  };

  const filteredMeetings = selectedMonth === 'all' 
    ? meetings 
    : meetings.filter(m => m.month === selectedMonth);

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
          >
            <option value="all">All Meetings</option>
            {uniqueMonths.map(month => (
              <option key={month} value={month}>
                {formatMonth(month)}
              </option>
            ))}
          </select>
        </div>
        
        <div className="space-y-3 max-h-[400px] overflow-y-auto pr-2">
          {filteredMeetings.length > 0 ? (
            filteredMeetings.map(meeting => (
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