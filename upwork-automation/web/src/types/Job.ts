export type JobStatus = 'DISCOVERED' | 'FILTERED' | 'QUEUED' | 'APPLIED' | 'REJECTED';
export type JobType = 'FIXED' | 'HOURLY';

export interface Job {
  id: string;
  title: string;
  description: string;
  budget_min?: number;
  budget_max?: number;
  hourly_rate?: number;
  client_rating: number;
  client_payment_verified: boolean;
  client_hire_rate: number;
  posted_date: string;
  deadline?: string;
  skills_required: string[];
  job_type: JobType;
  location?: string;
  status: JobStatus;
  match_score: number;
  created_at: string;
  updated_at: string;
}