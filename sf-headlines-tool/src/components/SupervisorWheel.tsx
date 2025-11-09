'use client';

import { useState } from 'react';
import { Supervisor, HeadlinesData } from '@/types';

interface SupervisorWheelProps {
  supervisors: Supervisor[];
  headlines: HeadlinesData;
  selectedSupervisor: string | null;
  onSupervisorSelect: (supervisorId: string) => void;
  onBackToMeetings: () => void;
}

export default function SupervisorWheel({ 
  supervisors, 
  headlines, 
  selectedSupervisor, 
  onSupervisorSelect,
  onBackToMeetings 
}: SupervisorWheelProps) {
  const [hoveredSupervisor, setHoveredSupervisor] = useState<string | null>(null);
  const [rotation, setRotation] = useState(0);

  const handleWheel = (e: React.WheelEvent) => {
    e.preventDefault();
    setRotation(prev => prev + (e.deltaY > 0 ? 10 : -10));
  };

  return (
    <div className="w-full lg:w-1/2 flex flex-col items-center">
      <h2 className="text-2xl font-bold mb-4">Select a Supervisor</h2>
      <p className="text-sm text-gray-400 mb-6">Hover and click to view headlines • Scroll to rotate</p>
      
      <div 
        className="relative w-[500px] h-[500px]"
        onWheel={handleWheel}
      >
        {/* Center circle with Mayor */}
        <div 
          className="absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 w-40 h-40 rounded-full bg-gradient-to-br from-amber-500 to-orange-600 flex flex-col items-center justify-center shadow-2xl z-10 border-4 border-yellow-300 cursor-pointer transition-transform hover:scale-110"
          onMouseEnter={() => setHoveredSupervisor('mayor')}
          onMouseLeave={() => setHoveredSupervisor(null)}
        >
          <span className="text-xl font-bold text-center">🏛️</span>
          <span className="text-sm font-bold text-center mt-1">Mayor</span>
          <span className="text-xs text-center">Daniel Lurie</span>
          
          {hoveredSupervisor === 'mayor' && (
            <div className="absolute top-full mt-4 left-1/2 transform -translate-x-1/2 bg-gray-900 border-2 border-amber-500 rounded-lg p-4 w-56 shadow-2xl z-50">
              <p className="font-bold text-lg">Daniel Lurie</p>
              <p className="text-sm text-amber-400">Mayor of San Francisco</p>
              <div className="mt-2 pt-2 border-t border-gray-700">
                <p className="text-xs text-gray-300">
                  Elected November 2024
                </p>
              </div>
            </div>
          )}
        </div>

        {/* Supervisor circles */}
        {supervisors.map((sup, index) => {
          const angle = (index * (360 / supervisors.length) + rotation) * (Math.PI / 180);
          const radius = 180;
          const x = Math.cos(angle) * radius;
          const y = Math.sin(angle) * radius;
          const isHovered = hoveredSupervisor === sup.id;
          const isSelected = selectedSupervisor === sup.id;
          
          return (
            <div
              key={sup.id}
              className="absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 transition-all duration-200"
              style={{
                transform: `translate(calc(-50% + ${x}px), calc(-50% + ${y}px)) scale(${isHovered ? 1.2 : isSelected ? 1.15 : 1})`,
                zIndex: isHovered ? 100 : 1
              }}
              onMouseEnter={() => setHoveredSupervisor(sup.id)}
              onMouseLeave={() => setHoveredSupervisor(null)}
              onClick={() => onSupervisorSelect(sup.id)}
            >
              <div
                className={`w-24 h-24 rounded-full flex items-center justify-center cursor-pointer shadow-xl transition-all ${
                  isSelected ? 'ring-4 ring-white' : ''
                }`}
                style={{ backgroundColor: sup.color }}
              >
                <span className="text-xs font-bold text-center text-white px-2">
                  {sup.name.split(' ')[0]}<br/>{sup.name.split(' ')[1]}
                </span>
              </div>
              
              {isHovered && (
                <div className="absolute top-full mt-4 left-1/2 transform -translate-x-1/2 bg-gray-900 border-2 border-blue-500 rounded-lg p-4 w-56 shadow-2xl">
                  <p className="font-bold text-lg">{sup.name}</p>
                  <p className="text-sm text-blue-400">{sup.handle}</p>
                  <div className="mt-2 pt-2 border-t border-gray-700">
                    <p className="text-xs text-gray-300">
                      {headlines[sup.id]?.length || 0} headline(s) generated
                    </p>
                  </div>
                </div>
              )}
            </div>
          );
        })}
      </div>

      <button
        onClick={onBackToMeetings}
        className="mt-8 px-6 py-3 bg-gray-700 rounded-lg hover:bg-gray-600 transition-colors"
      >
        Select Different Meeting
      </button>
    </div>
  );
}