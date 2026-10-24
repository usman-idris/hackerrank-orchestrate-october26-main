"""Hand-trace one sample case: python code/trace_case.py case_05"""
import json
import sys
from pathlib import Path

import pandas as pd

DATASET = Path(__file__).resolve().parent.parent / "dataset"
case_id = sys.argv[1] if len(sys.argv) > 1 else "case_05"

requests = pd.read_csv(DATASET / "sample_deletion_requests.csv")
answers = pd.read_csv(DATASET / "sample_output.csv")
users = pd.read_csv(DATASET / "user_identities.csv")
audit = pd.read_csv(DATASET / "user_audit_log.csv")
activity = pd.read_csv(DATASET / "system_activity.csv")
evidence = pd.read_csv(DATASET / "evidence_files.csv")

req = requests[requests.case_id == case_id].iloc[0]
print("REQUEST:", req.email, "| reported:", req.reported_status, "| audit_at:", req.audit_at)
print("TEXT   :", req.request_text)

# 1. email -> user
user = users[users.email == req.email]
print("\n1. CURRENT IDENTITY:")
print(user.to_string(index=False))
user_id = user.user_id.iloc[0] if len(user) else None

# 2. old identifiers
print("\n2. HISTORY (audit log):")
print(audit[audit.user_id == user_id].to_string(index=False))

# 3. the expected answer
ans = answers[answers.case_id == case_id].iloc[0]
print("\n3. EXPECTED STATUS:", ans.deletion_status)
for step in json.loads(ans.steps_json):
    print("  ", step["step_no"], step["phase"], step["operation"],
          step["system_id"], step["resource_id"], step["evidence_id"] or "(none)")

# 4. activity mentioning any resource used in the answer
resources = {s["resource_id"] for s in json.loads(ans.steps_json)}
hits = activity[activity.resource_id.isin(resources)]
print("\n4. SYSTEM ACTIVITY ABOUT THOSE RESOURCES:")
print(hits.to_string(index=False, max_colwidth=90))

# 5. evidence files cited
cited = {s["evidence_id"] for s in json.loads(ans.steps_json) if s["evidence_id"]}
print("\n5. EVIDENCE CITED:")
print(evidence[evidence.file_id.isin(cited)].to_string(index=False))