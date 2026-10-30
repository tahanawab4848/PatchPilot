"""
Structured prompt templates for each agent stage.

Rules:
- All prompts request JSON output with a strict schema.
- System prompts establish the model's role and constraints.
- Content is kept concise to preserve token budget for evidence.
- The model is instructed to distinguish confirmed findings from assumptions.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional


# ── System prompts ─────────────────────────────────────────────────────────────

SYSTEM_DIAGNOSIS = """\
You are a senior software engineer performing root-cause analysis.
Your task is to analyze a bug report together with source code evidence and \
test output, then produce a structured diagnosis.

Rules:
- Only reference file paths and line numbers that appear in the provided context.
- Clearly distinguish CONFIRMED findings (backed by code or test output) from \
ASSUMPTIONS.
- Do not fabricate stack traces, variable values, or test names.
- Respond with valid JSON only — no markdown fences, no prose outside the JSON.
"""

SYSTEM_INVESTIGATION = """\
You are an autonomous debugging agent planning investigation steps.
Select which approved tools to call to gather precise evidence about the bug.
Do not guess. Only request tools from the approved tool list.
Respond with valid JSON only.
"""

SYSTEM_TEST_PLAN = """\
You are a senior software test engineer designing verification tests for a bug fix.
Identify the minimal test plan to prove the bug is resolved without introducing regressions.
Respond with valid JSON only.
"""

SYSTEM_PATCH = """\
You are a senior software engineer generating a minimal bug fix.
Your task is to produce a unified diff that repairs exactly the root cause \
identified in the diagnosis.

Rules:
- Generate the smallest change that fixes the bug.
- Do not refactor unrelated code.
- Do not delete tests.
- Do not change protected files (.env, Dockerfile, etc.).
- Every diff must be a valid unified diff that can be applied with `patch -p1`.
- Respond with valid JSON only — no markdown fences, no prose outside the JSON.
"""

SYSTEM_CRITIQUE = """\
You are an expert AI Verification Judge & Code Reviewer running NVIDIA Nemotron-70B.
You specialize in HelpSteer2 reward assessment, adversarial self-critique, and regression prevention.
Your task is to independently critique a proposed patch against the original bug description and code context.

Evaluate along HelpSteer2-aligned dimensions:
1. Correctness (1-5): Does the patch fix the exact root cause without regressions?
2. Coherence (1-5): Is the code idiomatic, clean, and minimal?
3. Safety & Security (1-5): Does the patch introduce security risks, injection vectors, or unprotected resources?

Identify any subtle side-effects, API breakage, or style regressions.
Respond with valid JSON only — no markdown fences, no prose outside the JSON.
"""

SYSTEM_VERIFICATION = """\
You are a senior software engineer interpreting test results after a patch \
has been applied.
Your task is to determine whether the repair is verified, partially verified, \
or failed.

Rules:
- Base your assessment solely on the test data provided.
- Do not claim a repair is verified if any relevant test is still failing.
- Respond with valid JSON only.
"""


# ── Diagnosis prompt ───────────────────────────────────────────────────────────

def build_diagnosis_prompt(
    bug_description: str,
    repo_summary: str,
    file_excerpts: List[Dict[str, Any]],
    baseline_output: str,
    previous_hypotheses: Optional[str] = None,
) -> str:
    """Return the user message content for root-cause diagnosis."""
    excerpts_text = "\n\n".join(
        f"=== FILE: {e['path']} (lines {e.get('start_line',1)}–{e.get('end_line','?')}) ===\n{e['content']}"
        for e in file_excerpts
    )

    previous = ""
    if previous_hypotheses:
        previous = f"\n\nPREVIOUS HYPOTHESES (rejected or inconclusive):\n{previous_hypotheses}"

    return f"""\
BUG DESCRIPTION:
{bug_description}

REPOSITORY SUMMARY:
{repo_summary}

BASELINE TEST OUTPUT:
{baseline_output}

SOURCE CODE CONTEXT:
{excerpts_text}
{previous}

Respond with this exact JSON schema (all fields required):
{{
  "problem_summary": "one sentence",
  "hypotheses": [
    {{
      "summary": "concise hypothesis",
      "evidence": ["piece of evidence from code or test output"],
      "locations": [
        {{"file_path": "src/foo.py", "start_line": 42, "end_line": 45, "snippet": "relevant code"}}
      ],
      "confidence": 0.0,
      "confidence_explanation": "why this confidence level"
    }}
  ],
  "recommended_steps": ["step 1", "step 2"],
  "relevant_files": ["src/foo.py"],
  "proposed_minimal_repair": "concise description of minimal change",
  "tests_needed_to_verify": ["test name or command"],
  "is_confirmed": false,
  "assumptions": ["assumption 1"]
}}
"""


# ── Investigation planning prompt ─────────────────────────────────────────────

def build_investigation_plan_prompt(
    bug_description: str,
    repo_summary: str,
    baseline_output: str,
    tools_available: List[Dict[str, Any]],
) -> str:
    """Return user message content for planning investigation tool calls."""
    tools_desc = "\n".join(
        f"- {t['name']}: {t['description']} (parameters: {list(t.get('parameters', {}).keys())})"
        for t in tools_available
    )
    return f"""\
BUG DESCRIPTION:
{bug_description}

REPOSITORY SUMMARY:
{repo_summary}

BASELINE TEST OUTPUT:
{baseline_output}

AVAILABLE APPROVED TOOLS:
{tools_desc}

Plan up to 5 tool calls to investigate the root cause.
Respond with this exact JSON schema:
{{
  "investigation_goal": "what to find out",
  "tool_calls": [
    {{
      "tool": "tool_name",
      "arguments": {{"param": "value"}}
    }}
  ]
}}
"""


# ── Test plan generation prompt ───────────────────────────────────────────────

def build_test_plan_prompt(
    bug_description: str,
    diagnosis_summary: str,
    patch_summary: str,
    files_modified: List[str],
) -> str:
    """Return user message content for generating verification test plans."""
    return f"""\
BUG DESCRIPTION:
{bug_description}

DIAGNOSIS:
{diagnosis_summary}

PROPOSED PATCH:
{patch_summary}
Files modified: {', '.join(files_modified)}

Design a verification test plan.
Respond with this exact JSON schema:
{{
  "target_reproduction_test": "test command or file to reproduce",
  "regression_tests": ["test_1", "test_2"],
  "validation_criteria": "what constitutes success"
}}
"""


# ── Patch generation prompt ────────────────────────────────────────────────────

def build_patch_prompt(
    bug_description: str,
    diagnosis_summary: str,
    file_excerpts: List[Dict[str, Any]],
    test_files: List[str],
    user_feedback: Optional[str] = None,
) -> str:
    """Return the user message for patch generation."""
    excerpts_text = "\n\n".join(
        f"=== FILE: {e['path']} ===\n{e['content']}"
        for e in file_excerpts
    )
    test_list = "\n".join(f"  - {t}" for t in test_files[:20])
    feedback_section = f"\n\nUSER FEEDBACK ON PREVIOUS ATTEMPT:\n{user_feedback}\nAddress this feedback directly." if user_feedback else ""

    return f"""\
BUG DESCRIPTION:
{bug_description}

ROOT-CAUSE DIAGNOSIS:
{diagnosis_summary}
{feedback_section}

SOURCE CODE TO FIX:
{excerpts_text}

TEST FILES (do NOT modify these):
{test_list}

Generate a minimal unified diff that fixes this bug. The diff must apply \
cleanly to the files shown above.

Respond with this exact JSON schema (all fields required):
{{
  "summary": "one-line description of the fix",
  "files": [
    {{
      "file_path": "src/foo.py",
      "unified_diff": "--- a/src/foo.py\\n+++ b/src/foo.py\\n@@ ... @@\\n ...",
      "change_description": "what and why",
      "evidence_references": ["diagnosis point this addresses"],
      "potential_side_effects": ["none" or list any]
    }}
  ],
  "regression_test_plan": ["test_name_1", "test_name_2"],
  "model_reasoning": "brief explanation of the approach"
}}
"""


# ── Verification interpretation prompt ────────────────────────────────────────

def build_verification_prompt(
    bug_description: str,
    diagnosis_summary: str,
    baseline_summary: Dict[str, Any],
    post_patch_summary: Dict[str, Any],
) -> str:
    """Return the user message for verification interpretation."""
    return f"""\
BUG DESCRIPTION:
{bug_description}

DIAGNOSIS:
{diagnosis_summary}

BASELINE TEST SUMMARY (before patch):
{_format_test_summary(baseline_summary)}

POST-PATCH TEST SUMMARY (after patch):
{_format_test_summary(post_patch_summary)}

Determine whether the repair is verified.

Respond with this exact JSON schema:
{{
  "outcome": "verified" | "partially_verified" | "failed" | "unable_to_verify",
  "outcome_reasoning": "explanation",
  "regression_failures": ["test_name if any regression"],
  "warnings": ["any caveats"]
}}
"""


def build_critique_prompt(
    bug_description: str,
    diagnosis_summary: str,
    patch_summary: str,
    unified_diff: str,
    file_context: Optional[str] = None,
) -> str:
    """Return user message for NVIDIA Nemotron Dual-Pass Reasoner & Critic."""
    context_str = f"\n\nRELEVANT CODE CONTEXT:\n{file_context}" if file_context else ""
    return f"""\
BUG DESCRIPTION:
{bug_description}

DIAGNOSIS SUMMARY:
{diagnosis_summary}

PROPOSED REPAIR SUMMARY:
{patch_summary}

UNIFIED DIFF:
{unified_diff}
{context_str}

Evaluate this patch using the HelpSteer2 reward rubric.
Respond with this exact JSON schema (all fields required):
{{
  "verdict": "APPROVED" | "REVISED",
  "verdict_summary": "one-line judgment summarizing the verification decision",
  "helpsteer_scores": {{
    "correctness": 5,
    "coherence": 5,
    "safety": 5
  }},
  "side_effects_analysis": "thorough analysis of any side effects, regressions, or API impacts",
  "security_audit": "analysis of security posture, input validation, and denial of service risks",
  "pass_type": "NVIDIA Nemotron Dual-Pass Reasoner & Critic",
  "recommended_refinements": ["list of optional refinements if any"]
}}
"""


def _format_test_summary(summary: Dict[str, Any]) -> str:
    passed = summary.get("passed", 0)
    failed = summary.get("failed", 0)
    errors = summary.get("errors", 0)
    total = summary.get("total", 0)
    failing_names = summary.get("failing_tests", [])
    lines = [f"total={total}, passed={passed}, failed={failed}, errors={errors}"]
    if failing_names:
        lines.append("Failing tests: " + ", ".join(failing_names[:20]))
    return "\n".join(lines)


# ── Repository summarization prompt ───────────────────────────────────────────

def build_repo_summary_prompt(
    repo_name: str,
    primary_language: Optional[str],
    frameworks: List[str],
    test_frameworks: List[str],
    file_list: List[str],
    manifest_snippets: List[Dict[str, str]],
) -> str:
    """Return a compact text summary of the repository (not sent to model — used inline)."""
    lines = [
        f"Repository: {repo_name}",
        f"Language: {primary_language or 'unknown'}",
        f"Frameworks: {', '.join(frameworks) or 'none detected'}",
        f"Test frameworks: {', '.join(test_frameworks) or 'none detected'}",
        f"Source files ({len(file_list)}): " + ", ".join(file_list[:30]),
    ]
    for m in manifest_snippets[:3]:
        lines.append(f"\n{m['kind']}:\n{m.get('raw_content','')[:400]}")
    return "\n".join(lines)
