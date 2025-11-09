'use client';

import { useState } from 'react';
import { TrendingUp, RefreshCw, CheckCircle, Circle } from 'lucide-react';
import { Headline, Supervisor } from '@/types';

interface HeadlineCardProps {
  headline: Headline;
  supervisor: Supervisor;
  userInitials: string;
  onFactCheck: (headlineId: string) => void;
  onSubmitFactCheck: (headlineId: string, note: string) => void;
  onGetSentiment: (headlineId: string) => void;
}

export default function HeadlineCard({ 
  headline, 
  supervisor, 
  userInitials,
  onFactCheck,
  onSubmitFactCheck,
  onGetSentiment
}: HeadlineCardProps) {
  const [expandedFactCheck, setExpandedFactCheck] = useState(false);
  const [factCheckNote, setFactCheckNote] = useState('');

  const getSentimentColor = (score: number) => {
    if (score <= 3) return 'from-red-500 to-orange-500';
    if (score <= 6) return 'from-yellow-500 to-amber-500';
    return 'from-green-500 to-emerald-500';
  };

  const handleFactCheckClick = () => {
    if (!userInitials) {
      alert('Please enter your initials first!');
      return;
    }

    if (headline.checkedBy.includes(userInitials)) {
      alert('You have already fact-checked this headline!');
      return;
    }

    setExpandedFactCheck(!expandedFactCheck);
    if (expandedFactCheck) {
      setFactCheckNote('');
    }
    onFactCheck(headline.id);
  };

  const handleSubmit = () => {
    if (!factCheckNote.trim()) {
      alert('Please add a note before submitting your fact check!');
      return;
    }

    onSubmitFactCheck(headline.id, factCheckNote);
    setExpandedFactCheck(false);
    setFactCheckNote('');
  };

  return (
    <div className="bg-gray-900/80 rounded-xl p-6 mb-4 border border-gray-700">
      <div className="flex items-start justify-between mb-4">
        <p className="text-sm font-semibold" style={{ color: supervisor.color }}>
          {supervisor.handle}
        </p>
        <div className="flex items-center gap-3">
          {headline.checkedBy && headline.checkedBy.length > 0 && (
            <div className="flex -space-x-2">
              {headline.checkedBy.map((initials, idx) => (
                <div
                  key={idx}
                  className="w-8 h-8 rounded-full bg-gradient-to-br from-blue-500 to-cyan-600 flex items-center justify-center text-xs font-bold border-2 border-gray-900 shadow-lg"
                  title={`Verified by ${initials}`}
                >
                  {initials}
                </div>
              ))}
            </div>
          )}
          
          <div className="flex items-center gap-2">
            {headline.factChecks === 0 && <Circle className="w-5 h-5 text-gray-500" />}
            {headline.factChecks === 1 && <CheckCircle className="w-5 h-5 text-yellow-400" />}
            {headline.factChecks >= 2 && <CheckCircle className="w-5 h-5 text-green-400" />}
            <span className="text-sm font-bold">{headline.factChecks}/2</span>
          </div>
        </div>
      </div>
      
      <p className="mb-6 text-base leading-relaxed" dangerouslySetInnerHTML={{ __html: headline.text }}></p>
      
      {headline.sentiment !== null && (
        <div className="mb-4 p-4 bg-gray-800/60 rounded-lg border border-gray-600">
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm font-semibold text-gray-300">Twitter Sentiment Score</span>
            <span className="text-2xl font-bold">{headline.sentiment}/10</span>
          </div>
          <div className="w-full h-4 bg-gray-700 rounded-full overflow-hidden">
            <div 
              className={`h-full bg-gradient-to-r ${getSentimentColor(headline.sentiment)} transition-all duration-1000`}
              style={{ width: `${headline.sentiment * 10}%` }}
            />
          </div>
          <p className="text-xs text-gray-400 mt-2">
            {headline.sentiment <= 3 && 'Low public interest'}
            {headline.sentiment > 3 && headline.sentiment <= 6 && 'Moderate public interest'}
            {headline.sentiment > 6 && 'High public interest'}
          </p>
        </div>
      )}
      
      <div className="flex flex-wrap gap-2">
        <button
          onClick={handleFactCheckClick}
          disabled={headline.checkedBy?.includes(userInitials)}
          className="px-4 py-2 bg-blue-600 rounded-lg hover:bg-blue-700 disabled:bg-gray-600 disabled:cursor-not-allowed text-sm font-semibold transition-colors"
        >
          Fact Check
        </button>

        <button
          onClick={() => onGetSentiment(headline.id)}
          disabled={headline.loadingSentiment}
          className="px-4 py-2 bg-cyan-600 rounded-lg hover:bg-cyan-700 disabled:bg-gray-600 text-sm font-semibold transition-colors flex items-center gap-2"
        >
          {headline.loadingSentiment ? (
            <>
              <RefreshCw className="w-4 h-4 animate-spin" />
              Analyzing...
            </>
          ) : (
            <>
              <TrendingUp className="w-4 h-4" />
              Get Sentiment
            </>
          )}
        </button>
        
        {headline.isActive && (
          <button
            className="px-4 py-2 bg-yellow-500 text-gray-900 rounded-lg hover:bg-yellow-400 text-sm font-bold transition-colors"
          >
            📋 Export Headline
          </button>
        )}
      </div>

      {expandedFactCheck && (
        <div className="mt-4 p-4 bg-gray-800 rounded-lg border border-blue-500">
          <label className="block text-sm font-semibold mb-3">
            Fact Check Notes
          </label>
          
          <div className="mb-3 p-3 bg-gray-900/60 rounded border border-gray-700">
            <p className="text-xs font-semibold text-gray-400 mb-2">CITED TRANSCRIPT SECTIONS:</p>
            <div className="text-sm text-gray-300 space-y-1">
              {headline.text.match(/\[[\d:,\s]+\]/g)?.slice(0, 3).map((timestamp, idx) => (
                <div key={idx} className="text-xs font-mono text-blue-300">
                  {timestamp}
                </div>
              ))}
            </div>
          </div>

          <textarea
            value={factCheckNote}
            onChange={(e) => setFactCheckNote(e.target.value)}
            placeholder="Add your fact-checking notes here (e.g., verified claims, found discrepancies, etc.)..."
            className="w-full h-24 px-3 py-2 bg-gray-900 text-white rounded border border-gray-600 focus:border-blue-500 focus:outline-none text-sm"
          />
          <div className="flex gap-2 mt-3">
            <button
              onClick={handleSubmit}
              className="px-4 py-2 bg-blue-600 rounded hover:bg-blue-700 text-sm font-semibold"
            >
              Submit Fact Check
            </button>
            <button
              onClick={() => { setExpandedFactCheck(false); setFactCheckNote(''); }}
              className="px-4 py-2 bg-gray-600 rounded hover:bg-gray-700 text-sm"
            >
              Cancel
            </button>
          </div>
        </div>
      )}
    </div>
  );
}