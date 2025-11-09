export interface Supervisor {
  id: string;
  name: string;
  handle: string;
  color: string;
}

export interface Meeting {
  id: string;
  date: string;
  title: string;
  month: string;
}

export interface Headline {
  id: string;
  text: string;
  factChecks: number;
  isActive: boolean;
  checkedBy: string[];
  sentiment: number | null;
  loadingSentiment: boolean;
}

export interface HeadlinesData {
  [supervisorId: string]: Headline[];
}