// types/legislation.ts

export interface Sponsor {
  name: string;
  is_mayor: boolean;
}

export interface Committee {
  name: string;
  members: string[];
}

export interface Dates {
  introduced: string;
  final_action: string;
}

export interface Votes {
  [supervisorName: string]: 'aye' | 'no' | 'absent' | 'abstain';
}

export interface Legislation {
  id: number;
  legislation_number: string;
  title: string;
  description: string;
  type: string;
  category: string;
  status: string;
  dates: Dates;
  sponsors: Sponsor[];
  committee: Committee;
  legislation_url: string;
  votes: Votes;
}

export interface Supervisor {
  name: string;
  district: number;
  initials: string;
}

export interface LegislationResponse {
  legislation: Legislation[];
  supervisors: Supervisor[];
}