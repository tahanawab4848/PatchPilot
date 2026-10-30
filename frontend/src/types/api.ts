/**
 * TypeScript types mirroring the backend Pydantic schemas.
 * Keep in sync with backend/app/schemas/*.py
 */

export type JobStatus =
  | "queued"
  | "analyzing"
  | "reproducing"
  | "diagnosing"
  | "patch_proposed"
  | "awaiting_approval"
  | "applying_patch"
  | "verifying"
  | "completed"
  | "failed"
  | "cancelled";

export type VerificationOutcome =
  | "verified"
  | "partially_verified"
  | "failed"
  | "unable_to_verify";

export type PatchApproval = "approved" | "rejected" | "revised" | "cancelled";

export interface CodeLocation {
  file_path: string;
  start_line?: number | null;
  end_line?: number | null;
  snippet?: string | null;
}

export interface RootCauseHypothesis {
  summary: string;
  evidence: string[];
  locations: CodeLocation[];
  confidence: number;
  confidence_explanation: string;
}

export interface DiagnosisResult {
  problem_summary: string;
  hypotheses: RootCauseHypothesis[];
  recommended_steps: string[];
  relevant_files: string[];
  proposed_minimal_repair?: string | null;
  tests_needed_to_verify?: string[];
  is_confirmed: boolean;
  assumptions: string[];
}

export interface EvaluationMetrics {
  bug_reproduced: boolean;
  valid_diagnosis_produced: boolean;
  patch_applied_successfully: boolean;
  original_failing_tests_passed: boolean;
  regression_tests_passed: boolean;
  repair_iterations: number;
  model_failures: number;
  sandbox_failures: number;
  total_duration_seconds: number;
}

export interface JobEvent {
  id: string;
  job_id: string;
  created_at: string;
  stage: string;
  status: string;
  details?: Record<string, unknown> | null;
  message?: string | null;
}

export interface JobSummary {
  id: string;
  created_at: string;
  updated_at: string;
  repo_name: string;
  repo_source: string;
  bug_description: string;
  status: JobStatus;
  repair_iterations: number;
}

export interface HelpSteerScores {
  correctness: number;
  coherence: number;
  safety: number;
}

export interface NemotronCritique {
  verdict: string;
  verdict_summary: string;
  helpsteer_scores: HelpSteerScores;
  side_effects_analysis: string;
  security_audit: string;
  pass_type: string;
  recommended_refinements?: string[];
}

export interface NebiusTelemetry {
  provider: string;
  model_id: string;
  accelerator: string;
  prompt_tokens: number;
  completion_tokens: number;
  total_tokens: number;
  duration_seconds: number;
  tokens_per_second: number;
  time_to_first_token_ms: number;
  kv_cache_acceleration: string;
}

export interface JobDetail extends JobSummary {
  project_metadata?: ProjectMetadata | null;
  proposed_patch?: string | null;
  nemotron_critique?: NemotronCritique | null;
  nebius_telemetry?: NebiusTelemetry | null;
  reasoning_log?: string | null;
  patch_approval?: PatchApproval | null;
  patch_feedback?: string | null;
  repair_report?: RepairReport | null;
  error_message?: string | null;
  events: JobEvent[];
}

export interface TestSummary {
  passed?: number;
  failed?: number;
  errors?: number;
  skipped?: number;
  total?: number;
  duration_seconds?: number;
  failing_tests?: string[];
  [key: string]: unknown;
}

export interface RepairReport {
  job_id: string;
  outcome: VerificationOutcome;
  bug_description: string;
  diagnosis_summary: string;
  patch_summary: string;
  modified_files: string[];
  baseline_test_summary?: TestSummary | null;
  post_patch_test_summary?: TestSummary | null;
  regression_failures: string[];
  commands_executed: string[];
  repair_iterations: number;
  total_duration_seconds: number;
  metrics?: EvaluationMetrics | null;
  warnings: string[];
  limitations: string[];
}

export interface UploadResponse {
  archive_path: string;
  original_filename: string;
  size_bytes: number;
  message: string;
}

export interface CreateJobRequest {
  repo_name: string;
  repo_source: "upload" | "demo";
  archive_path?: string;
  bug_description: string;
}

export interface PatchApprovalRequest {
  decision: PatchApproval;
  notes?: string;
}

export interface FileEntry {
  path: string;
  size_bytes: number;
  is_binary: boolean;
  language?: string | null;
}

export interface ProjectMetadata {
  detected_languages: string[];
  primary_language?: string | null;
  frameworks: string[];
  test_frameworks: TestFrameworkInfo[];
  entry_points: string[];
  lockfiles?: string[];
  configuration_and_build_scripts?: string[];
  sensitive_files?: string[];
  dangerous_configurations?: string[];
  total_files: number;
  source_files: number;
  test_files: number;
}

export interface TestFrameworkInfo {
  name: string;
  config_file?: string | null;
  test_command?: string | null;
  test_dirs: string[];
}

export interface RepositoryIndex {
  files: FileEntry[];
  relevant_files: string[];
  test_files: string[];
  metadata: ProjectMetadata;
}

export interface HealthResponse {
  status: string;
  database: { ok: boolean; error?: string | null };
  nebius: { configured: boolean; model_id: string; base_url: string };
  sandbox: { enabled: boolean; available: boolean };
}

export interface DemoProject {
  id: string;
  name: string;
  description: string;
  path: string;
}

export interface FileContentResponse {
  path: string;
  content: string;
  total_lines: number;
  start_line: number;
  end_line: number;
  language?: string | null;
}

export interface ApiError {
  error: { code: string; message: string; field?: string | null };
  request_id?: string | null;
}
