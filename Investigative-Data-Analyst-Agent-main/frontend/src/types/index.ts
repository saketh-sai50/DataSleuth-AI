export interface Dataset {
  id: number;
  filename: string;
  stored_filename: string;
  file_type: string;
  row_count: number | null;
  column_count: number | null;
  schema_info: Record<string, string> | null;
  file_size_bytes: number | null;
  upload_timestamp: string;
}

export interface DatasetListResponse {
  datasets: Dataset[];
  total: number;
}

export interface Hypothesis {
  id: string;
  title: string;
  description: string;
  prior_probability: "LOW" | "MEDIUM" | "HIGH";
  validation_data_needed: string[];
  is_validated: boolean;
  evidence: string | null;
  confidence_score: number | null;
}

export interface HypothesisValidation {
  hypothesis_id: string;
  can_validate: "YES" | "PARTIAL" | "NO";
  validation_status: string;
  missing_dataset: string | null;
  missing_columns: string[];
  follow_up_question: string | null;
  evidence_found: string | null;
}

export interface MissingDataResult {
  validations: HypothesisValidation[];
  overall_investigation_status: "CAN_PROCEED" | "NEEDS_DATA" | "BLOCKED";
  summary: string;
  missing_datasets: string[];
  follow_up_questions: string[];
}

export interface ExecutionPlan {
  question_type: string;
  plan_steps: Array<{
    step: number;
    action: string;
    requires: string[];
  }>;
  required_datasets: string[];
  available_datasets: string[];
  missing_datasets: string[];
  can_proceed: boolean;
}

export interface DataAnalysisResult {
  summary_stats: Record<string, any>;
  column_types: Record<string, string>;
  null_counts: Record<string, number>;
  kpis: Record<string, any>;
  chart_json: string | null;
  insights: string[];
  row_count: number;
  column_count: number;
}

export interface Investigation {
  id: number;
  question: string;
  status: "initiated" | "analyzing" | "waiting_for_data" | "generating_report" | "completed" | "failed";
  hypotheses: Hypothesis[];
  missing_datasets: string[];
  follow_up_questions: string[];
  dataset_ids: number[];
  created_at: string;
  updated_at: string;
}

export interface RootCauseEntry {
  cause: string;
  confidence: number;
  evidence: string;
  hypothesis_id: string;
}

export interface Report {
  id: number;
  investigation_id: number;
  executive_summary: string;
  root_causes: RootCauseEntry[];
  evidence: string[];
  limitations: string[];
  recommendations: string[];
  missing_info: string[];
  next_steps: string[];
  charts: Array<Record<string, any>> | null;
  overall_confidence: number;
  created_at: string;
}

export interface ChatResponse {
  response: string;
  investigation_id: number | null;
  suggested_actions: string[];
}
