# Atomic slit persistence gateway

Merge only after backend, optional-CV and frontend CI jobs pass. The critical backend checks are the existing evidence-store suite plus new same-frame success, first-frame temporal and rollback regressions.

A green CI result validates software behavior in the repository environment only; physical qualification remains a later gateway.