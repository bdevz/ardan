export type ProposalStatus = 'DRAFT' | 'SUBMITTED' | 'ACCEPTED' | 'REJECTED';

export interface Proposal {
  id: string;
  job_id: string;
  content: string;
  bid_amount: number;
  attachments: string[];
  google_doc_url: string;
  generated_at: string;
  submitted_at?: string;
  status: ProposalStatus;
}