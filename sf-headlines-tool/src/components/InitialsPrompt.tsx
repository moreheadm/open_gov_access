'use client';

import { useState } from 'react';

interface InitialsPromptProps {
  userInitials: string;
  onInitialsSet: (initials: string) => void;
}

export default function InitialsPrompt({ userInitials, onInitialsSet }: InitialsPromptProps) {
  const [inputValue, setInputValue] = useState('');
  const [showPrompt, setShowPrompt] = useState(!userInitials);

  const handleSubmit = () => {
    if (inputValue.trim()) {
      onInitialsSet(inputValue.trim().toUpperCase());
      setShowPrompt(false);
    }
  };

  const handleChange = () => {
    setInputValue('');
    setShowPrompt(true);
    onInitialsSet('');
  };

  if (userInitials && !showPrompt) {
    return (
      <div className="mt-2 text-sm text-gray-400">
        Researcher: <span className="font-bold text-blue-400">{userInitials}</span>
        <button
          onClick={handleChange}
          className="ml-2 text-xs text-cyan-400 hover:text-cyan-300"
        >
          (change)
        </button>
      </div>
    );
  }

  return (
    <div className="mt-4 max-w-md mx-auto bg-blue-900/30 border border-blue-500 rounded-lg p-4">
      <p className="text-sm mb-2">Enter your researcher initials for accountability:</p>
      <div className="flex gap-2">
        <input
          type="text"
          maxLength={3}
          placeholder="e.g., JD"
          value={inputValue}
          onChange={(e) => setInputValue(e.target.value)}
          className="flex-1 px-3 py-2 bg-gray-900 text-white rounded border border-gray-600 focus:border-blue-500 focus:outline-none uppercase"
          onKeyPress={(e) => {
            if (e.key === 'Enter') {
              handleSubmit();
            }
          }}
        />
        <button
          onClick={handleSubmit}
          className="px-4 py-2 bg-blue-600 rounded hover:bg-blue-700"
        >
          Set
        </button>
      </div>
    </div>
  );
}