export interface DigestSummary {
  run_id: string;
  research_interest: string | null;
  date_from: string | null;
  date_to: string | null;
  generated_at: string | null;
  top_paper_title: string | null;
}

export interface Candidate {
  paper_id: string;
  title: string;
  score: number;
  rationale: string;
}

export interface PaperSection {
  paper_id: string;
  summary: string;
}

export interface DigestDetail {
  run_id: string;
  research_interest: string | null;
  date_from: string | null;
  date_to: string | null;
  generated_at: string | null;
  digest: string;
  candidates: Candidate[];
  sections: PaperSection[];
}
