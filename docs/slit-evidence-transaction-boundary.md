# Slit evidence transaction boundary

The atomic guarantee applies to the persisted inspection evidence pair and its evidence child tables. Audit-log writes occur in a subsequent transaction after the evidence pair commits. A later audit failure therefore does not roll back already committed evidence.

This boundary is intentional for the current pilot and should not be described as an atomic evidence-plus-audit transaction.