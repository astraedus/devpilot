export interface ReviewIssue {
  file: string;
  line: number;
  severity: 'error' | 'warning' | 'info';
  comment: string;
}

export interface PRReview {
  summary: string;
  issues: ReviewIssue[];
  overall: 'approve' | 'request_changes' | 'comment';
}

export interface ReviewJob {
  id: number | null;
  repo: string;
  pr_number: number;
  status: 'pending' | 'running' | 'done' | 'error';
  created_at: string | null;
  result_json: string | null;
  hcs_url: string | null;
}

export interface IncidentReport {
  root_cause: string;
  affected_files: string[];
  suggested_fix: string;
  severity: 'critical' | 'high' | 'medium';
}

export interface IncidentJob {
  id: number | null;
  repo: string;
  run_id: number;
  status: 'pending' | 'running' | 'done' | 'error';
  created_at: string | null;
  result_json: string | null;
  hcs_url: string | null;
}
