"""Check an output CSV against the rules in problem_statement.md.

Usage (from repo root):
    python code/validate_output.py sample_output
    python code/validate_output.py final
"""
import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
DATASET = ROOT / "dataset"

# Operation order exactly as listed in the "Allowed Operations" table.
OPERATION_ORDER = [
    "REPORT_REMAINING_RECORD", "REPORT_EXPOSED_PII", "REPORT_ACTIVE_DATA_FLOW",
    "REPORT_RESTORE_RISK", "DISABLE_DATA_FLOW", "BLOCK_RESTORE", "DELETE_RECORD",
    "REDACT_RECORD", "ANONYMIZE_RECORD", "VERIFY_RECORD_ABSENT",
    "VERIFY_RECORD_PRESENT", "VERIFY_RECORD_REDACTED", "VERIFY_RECORD_ANONYMIZED",
    "VERIFY_DATA_FLOW_DISABLED", "VERIFY_RESTORE_BLOCKED",
]
PHASE_OF = {
    **{op: "FINDING" for op in OPERATION_ORDER[0:4]},
    **{op: "REMEDIATION" for op in OPERATION_ORDER[4:9]},
    **{op: "VERIFICATION" for op in OPERATION_ORDER[9:]},
}
STATE_OF = {
    "REPORT_REMAINING_RECORD": "PRESENT", "REPORT_EXPOSED_PII": "PRESENT",
    "REPORT_ACTIVE_DATA_FLOW": "ACTIVE", "REPORT_RESTORE_RISK": "ACTIVE",
    "DISABLE_DATA_FLOW": "DISABLED", "BLOCK_RESTORE": "BLOCKED",
    "DELETE_RECORD": "ABSENT", "REDACT_RECORD": "REDACTED",
    "ANONYMIZE_RECORD": "ANONYMIZED", "VERIFY_RECORD_ABSENT": "ABSENT",
    "VERIFY_RECORD_PRESENT": "PRESENT", "VERIFY_RECORD_REDACTED": "REDACTED",
    "VERIFY_RECORD_ANONYMIZED": "ANONYMIZED", "VERIFY_DATA_FLOW_DISABLED": "DISABLED",
    "VERIFY_RESTORE_BLOCKED": "BLOCKED",
}
PHASES = ["FINDING", "REMEDIATION", "VERIFICATION"]
FIELDS = {"step_no", "phase", "system_id", "resource_id", "operation", "state", "evidence_id"}
STATUSES = {"COMPLETE", "INCOMPLETE", "NOT_APPLICABLE"}


def sort_key(step):
    return (PHASES.index(step["phase"]), OPERATION_ORDER.index(step["operation"]),
            step["system_id"], step["resource_id"])


def check_row(case_id, status, steps_text):
    """Return a list of problem strings for one output row."""
    problems = []
    if status not in STATUSES:
        problems.append(f"bad deletion_status {status!r}")
    try:
        steps = json.loads(steps_text)
    except (TypeError, ValueError):
        return problems + ["steps_json is not valid JSON"]
    if not isinstance(steps, list):
        return problems + ["steps_json is not a JSON array"]
    if status == "NOT_APPLICABLE" and steps:
        problems.append("NOT_APPLICABLE must have []")
    if status in ("COMPLETE", "INCOMPLETE") and not steps:
        problems.append(f"{status} should not have an empty step list")

    for i, s in enumerate(steps, start=1):
        if set(s) != FIELDS:
            problems.append(f"step {i}: wrong fields {sorted(s)}")
            continue
        if s["step_no"] != i:
            problems.append(f"step {i}: step_no is {s['step_no']}")
        if s["operation"] not in PHASE_OF:
            problems.append(f"step {i}: unknown operation {s['operation']!r}")
            continue
        if PHASE_OF[s["operation"]] != s["phase"]:
            problems.append(f"step {i}: {s['operation']} does not belong to phase {s['phase']}")
        if STATE_OF[s["operation"]] != s["state"]:
            problems.append(f"step {i}: state {s['state']} wrong for {s['operation']}")
        if s["phase"] == "REMEDIATION" and s["evidence_id"] != "":
            problems.append(f"step {i}: remediation must have empty evidence_id")
        if status == "COMPLETE" and s["phase"] != "VERIFICATION":
            problems.append(f"step {i}: COMPLETE may contain only VERIFICATION steps")
        if status == "COMPLETE" and s["evidence_id"] == "":
            problems.append(f"step {i}: COMPLETE verification must cite evidence")
    if not problems and steps != sorted(steps, key=sort_key):
        problems.append("steps are not in the required order")
    return problems


def validate(output_path, requests_path):
    out = pd.read_csv(output_path, dtype=str, keep_default_na=False)
    req = pd.read_csv(requests_path, dtype=str)
    errors = []
    if list(out.columns) != ["case_id", "deletion_status", "steps_json"]:
        errors.append(f"header is {list(out.columns)}")
    if len(out) != len(req):
        errors.append(f"expected {len(req)} rows, found {len(out)}")
    if set(out.case_id) != set(req.case_id):
        errors.append("case_id set differs from the requests file")
    if out.case_id.duplicated().any():
        errors.append("duplicate case_id values")
    if list(out.case_id) != sorted(out.case_id):
        errors.append("rows are not sorted by case_id (plain string sort)")
    for _, row in out.iterrows():
        for p in check_row(row.case_id, row.deletion_status, row.steps_json):
            errors.append(f"{row.case_id}: {p}")
    return errors


if __name__ == "__main__":
    which = sys.argv[1] if len(sys.argv) > 1 else "final"
    if which == "sample_output":
        output, requests = DATASET / "sample_output.csv", DATASET / "sample_deletion_requests.csv"
    else:
        output, requests = ROOT / "output.csv", DATASET / "deletion_requests.csv"
    problems = validate(output, requests)
    if problems:
        print(f"{len(problems)} problem(s) found:")
        for p in problems[:50]:
            print("  -", p)
        sys.exit(1)
    print(f"OK: {output.name} passes all checks.")