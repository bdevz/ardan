import { Job } from './Job';
import { Proposal } from './Proposal';

export type ApplicationStatus = 'SUBMITTED' | 'VIEWED' | 'RESPONDED' | 'INTERVIEWED' | 'HIRED' | 'REJECTED';

export interface Application {
  id: string;
  job_id: string;
  proposal_id: string;
  submitted_at: string;
  upwork_application_id?: string;
  status: ApplicationStatus;
  client_response?: string;
  client_response_date?: string;
  interview_scheduled: boolean;
  hired: boolean;
  job?: Job;
  proposal?: Proposal;
}