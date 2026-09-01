# Slit atomicity review checklist

- Same-frame Belt A/B records use one batch transaction.
- Both temporal assessments are calculated before current-frame persistence.
- Single-belt `save_evidence` compatibility is retained.
- Failed second-lane persistence leaves zero records from the failed batch.
- Successful pair preserves shared frame sequence and position.
- Audit records are explicitly outside the evidence transaction.
- Pair diagnostics remain response-only.
- No physical validation claim is made.