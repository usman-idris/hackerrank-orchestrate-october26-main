"""Step 1 exploration: print a quick summary of every CSV in dataset/."""
from pathlib import Path
import pandas as pd

# Folder layout: <repo root>/code/explore_data.py  ->  <repo root>/dataset
DATASET = Path(__file__).resolve().parent.parent / "dataset"

FILES = [
    "deletion_requests.csv",
    "sample_deletion_requests.csv",
    "sample_output.csv",
    "user_identities.csv",
    "user_audit_log.csv",
    "system_activity.csv",
    "deletion_rules.csv",
    "evidence_files.csv",
]

for name in FILES:
    df = pd.read_csv(DATASET / name)
    print("=" * 70)
    print(f"{name}: {len(df)} rows, columns = {list(df.columns)}")
    print(df.head(2).to_string(max_colwidth=50))

print("=" * 70)
print("Evidence files on disk by folder:")
for folder in sorted((DATASET / "evidence").iterdir()):
    print(f"  {folder.name}: {len(list(folder.iterdir()))} files")