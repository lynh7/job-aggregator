export type Job = {
  id: number;
  provider: string;
  api_version: string;
  source_record_id: string;
  raw_job_id: number | null;
  external_id: string;
  title: string;
  company: string | null;
  location: string | null;
  description: string | null;
  employment_type: string | null;
  salary_text: string | null;
  url: string;
  posted_at: string | null;
  rule_version: string;
  normalization_status: string;
  created_at: string;
  updated_at: string;
  last_seen_at: string;
};

export type RawJob = {
  id: number;
  provider: string;
  api_version: string;
  source_record_id: string;
  rule_version: string;
  payload: Record<string, unknown>;
  fetched_at: string;
};

export type Candidate = {
  id: number;
  full_name: string | null;
  email: string | null;
  phone: string | null;
  location: string | null;
  status: string;
  latest_profile_version: string | null;
  created_at: string;
  updated_at: string;
};

export type CandidateProfile = {
  id: number;
  candidate_id: number;
  profile_version: string;
  summary: string | null;
  years_experience: number | null;
  preferred_roles: string[];
  skills: string[];
  languages: string[];
  raw_profile: Record<string, unknown>;
  created_at: string;
};

export type CandidateTask = {
  id: number;
  task_type: string;
  status: string;
  candidate_id: number | null;
  payload: Record<string, unknown>;
  attempts: number;
  max_attempts: number;
  locked_by: string | null;
  last_error: string | null;
  available_at: string;
  created_at: string;
  updated_at: string;
};

export type CandidateMatch = {
  id: number;
  candidate_id: number;
  job_key: string;
  provider: string;
  api_version: string;
  job_source_record_id: string;
  title: string;
  company: string | null;
  location: string | null;
  job_url: string | null;
  match_score: number;
  score_breakdown: Record<string, unknown>;
  matched_skills: string[];
  missing_skills: string[];
  rule_version: string;
  created_at: string;
};

export type CandidateApplication = {
  id: number;
  candidate_id: number;
  match_id: number;
  document_id: number | null;
  provider: string;
  api_version: string;
  job_source_record_id: string;
  status: string;
  external_application_id: string | null;
  request_payload: Record<string, unknown>;
  response_payload: Record<string, unknown>;
  last_error: string | null;
  applied_at: string | null;
  created_at: string;
  updated_at: string;
};

export type CandidateDetail = {
  candidate: Candidate;
  latest_profile: CandidateProfile | null;
  tasks: CandidateTask[];
};

export type CandidateCreateResponse = {
  candidate_id: number;
  document_id: number;
  task_id: number;
  status: string;
};

export type CandidateApplyResponse = {
  queued: number;
  task_ids: number[];
};
