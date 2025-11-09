import { Supervisor } from '@/types';

export const supervisors: Supervisor[] = [
  { id: 'alcaraz', name: 'Beya Alcaraz', handle: '@SFSupAlcaraz', color: '#3B82F6' },
  { id: 'mahmood', name: 'Bilal Mahmood', handle: '@SFSupMahmood', color: '#A855F7' },
  { id: 'chen', name: 'Chyanne Chen', handle: '@SFSupChen', color: '#10B981' },
  { id: 'chan', name: 'Connie Chan', handle: '@SFSupChan', color: '#F59E0B' },
  { id: 'sauter', name: 'Danny Sauter', handle: '@SFSupSauter', color: '#EF4444' },
  { id: 'fielder', name: 'Jackie Fielder', handle: '@SFSupFielder', color: '#6366F1' },
  { id: 'dorsey', name: 'Matt Dorsey', handle: '@SFSupDorsey', color: '#EC4899' },
  { id: 'melgar', name: 'Myrna Melgar', handle: '@SFSupMelgar', color: '#14B8A6' },
  { id: 'mandelman', name: 'Rafael Mandelman', handle: '@SFSupMandelman', color: '#F97316' },
  { id: 'walton', name: 'Shamann Walton', handle: '@SFSupWalton', color: '#8B5CF6' },
  { id: 'sherrill', name: 'Stephen Sherrill', handle: '@SFSupSherrill', color: '#06B6D4' },
];

export const mayor: Supervisor = {
  id: 'mayor',
  name: 'Daniel Lurie',
  handle: '@SFMayor',
  color: '#F59E0B' // Amber/gold color for mayor
};

// Helper function to get supervisor ID from full name
export function getSupervisorIdFromName(fullName: string): string | null {
  const supervisor = supervisors.find(
    s => s.name.toLowerCase() === fullName.toLowerCase()
  );
  return supervisor?.id || null;
}

// Helper function to get official ID (supervisor or mayor) from full name
export function getOfficialIdFromName(fullName: string): string | null {
  // Check if it's the mayor
  if (fullName.toLowerCase().includes('lurie') || fullName.toLowerCase().includes('mayor')) {
    return 'mayor';
  }

  // Otherwise check supervisors
  return getSupervisorIdFromName(fullName);
}