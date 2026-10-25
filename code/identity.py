"""Identity resolution: turn a request email into every identifier the user has ever had.

Run as a script to test all 518 requests:   python code/identity.py
Import from other code:                     from identity import IdentityBook
"""
import hashlib
from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd

DATASET = Path(__file__).resolve().parent.parent / "dataset"


def email_hash(email: str) -> str:
    """The dataset's email_hash is the SHA-256 of the lower-cased email."""
    return hashlib.sha256(email.strip().lower().encode("utf-8")).hexdigest()


@dataclass
class Identity:
    user_id: str
    name: str
    emails: set = field(default_factory=set)    # all lower-cased emails, past and present
    phones: set = field(default_factory=set)
    hashes: set = field(default_factory=set)
    current_email: str = ""

    def all_identifiers(self):
        """Everything we should search for in the evidence files."""
        return self.emails | self.phones | self.hashes


class IdentityBook:
    def __init__(self, dataset_dir: Path = DATASET):
        users = pd.read_csv(dataset_dir / "user_identities.csv", dtype=str, keep_default_na=False)
        audit = pd.read_csv(dataset_dir / "user_audit_log.csv", dtype=str, keep_default_na=False)
        self.by_user = {}
        self.email_to_user = {}

        for row in users.itertuples():
            ident = Identity(user_id=row.user_id, name=row.name, current_email=row.email.lower())
            ident.emails.add(row.email.lower())
            ident.phones.add(row.phone)
            ident.hashes.add(row.email_hash)
            self.by_user[row.user_id] = ident

        # Historical values: add BOTH sides of every change, so chains (A -> B -> C) are covered.
        for row in audit.itertuples():
            ident = self.by_user.get(row.user_id)
            if ident is None:
                continue
            for value in (row.old_value, row.new_value):
                if row.field_name == "email":
                    ident.emails.add(value.lower())
                elif row.field_name == "phone":
                    ident.phones.add(value)
                elif row.field_name == "email_hash":
                    ident.hashes.add(value)

        # Every email we know can be hashed, so add those hashes too.
        for ident in self.by_user.values():
            ident.hashes |= {email_hash(e) for e in ident.emails}
            for e in ident.emails:
                self.email_to_user[e] = ident.user_id

    def resolve(self, email: str):
        """Return the Identity for a request email (any case, current or old), or None."""
        user_id = self.email_to_user.get(email.strip().lower())
        return self.by_user.get(user_id) if user_id else None


if __name__ == "__main__":
    book = IdentityBook()
    requests = pd.read_csv(DATASET / "deletion_requests.csv", dtype=str)
    found = [book.resolve(e) for e in requests.email]
    print("Requests resolved:", sum(f is not None for f in found), "of", len(requests))
    chains = [f for f in found if f and len(f.emails) > 2]
    print("Users with 3+ emails (a chain of changes):", sorted({c.user_id for c in chains}))
    example = book.resolve("leila.haddad@yahoo.com")
    print("\nExample:", example.user_id, example.name)
    print("  emails :", sorted(example.emails))
    print("  phones :", sorted(example.phones))
    print("  hashes :", len(example.hashes))