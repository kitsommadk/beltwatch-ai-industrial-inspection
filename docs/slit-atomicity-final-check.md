# Final software check before merge

CI must execute the batch success and rollback tests under the repository's normal Python/SQLite environment. If those tests expose assumptions about dataclass replacement, unique constraints or replay sequence behavior, fix the implementation/tests rather than weakening the all-or-nothing invariant.