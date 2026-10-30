"""
Patch and diagnosis schemas.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class CodeLocation(BaseModel):
    file_path: str
    start_line: Optional[int] = None
    end_line: Optional[int] = None
    snippet: Optional[str] = None


class RootCauseHypothesis(BaseModel):
    summary: str
    evidence: List[str] = []
    locations: List[CodeLocation] = []
    confidence: float = Field(..., ge=0.0, le=1.0)
    confidence_explanation: str = ""


class DiagnosisResult(BaseModel):
    problem_summary: str
    hypotheses: List[RootCauseHypothesis] = []
    recommended_steps: List[str] = []
    relevant_files: List[str] = []
    proposed_minimal_repair: Optional[str] = None
    tests_needed_to_verify: List[str] = []
    is_confirmed: bool = False
    assumptions: List[str] = []


class FilePatch(BaseModel):
    file_path: str
    unified_diff: str
    change_description: str
    evidence_references: List[str] = []
    potential_side_effects: List[str] = []


class HelpSteerScores(BaseModel):
    correctness: int = Field(5, ge=1, le=5)
    coherence: int = Field(5, ge=1, le=5)
    safety: int = Field(5, ge=1, le=5)


class NemotronCritique(BaseModel):
    verdict: str = "APPROVED"  # "APPROVED" | "REVISED" | "REJECTED"
    verdict_summary: str
    helpsteer_scores: HelpSteerScores = Field(default_factory=HelpSteerScores)
    side_effects_analysis: str = "No unintended side effects detected."
    security_audit: str = "Clean: no vulnerabilities or arbitrary execution detected."
    pass_type: str = "NVIDIA Nemotron Dual-Pass Reasoner & Critic"
    recommended_refinements: List[str] = []


class NebiusTelemetry(BaseModel):
    provider: str = "Nebius Token Factory"
    model_id: str = "nvidia/Llama-3.1-Nemotron-70B-Instruct-HF"
    accelerator: str = "NVIDIA HGX H100 (FP8 Tensor Cores)"
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    duration_seconds: float = 0.0
    tokens_per_second: float = 0.0
    time_to_first_token_ms: float = 0.0
    kv_cache_acceleration: str = "vLLM PagedAttention Active"


class ProposedPatch(BaseModel):
    patch_id: str
    job_id: str
    summary: str
    files: List[FilePatch] = []
    regression_test_plan: List[str] = []
    model_reasoning: str = ""
    is_valid: bool = False
    validation_errors: List[str] = []
    critique: Optional[NemotronCritique] = None


class PatchValidationResult(BaseModel):
    is_valid: bool
    errors: List[str] = []
    warnings: List[str] = []


class EvaluationMetrics(BaseModel):
    bug_reproduced: bool = False
    valid_diagnosis_produced: bool = False
    patch_applied_successfully: bool = False
    original_failing_tests_passed: bool = False
    regression_tests_passed: bool = True
    repair_iterations: int = 0
    model_failures: int = 0
    sandbox_failures: int = 0
    total_duration_seconds: float = 0.0


class RepairReport(BaseModel):
    job_id: str
    outcome: str  # VerificationOutcome value
    bug_description: str
    diagnosis_summary: str
    patch_summary: str
    modified_files: List[str] = []
    baseline_test_summary: Optional[Dict[str, Any]] = None
    post_patch_test_summary: Optional[Dict[str, Any]] = None
    regression_failures: List[str] = []
    commands_executed: List[str] = []
    repair_iterations: int = 0
    total_duration_seconds: float = 0.0
    metrics: Optional[EvaluationMetrics] = None
    warnings: List[str] = []
    limitations: List[str] = []
