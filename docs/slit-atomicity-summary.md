# Atomic slit persistence summary

This change strengthens the evidence layer without changing the CV measurement model or frontend response contract. It introduces a reusable batch writer, routes slit auto-capture through it, computes both lane temporal assessments before persistence, and adds rollback/success regression coverage.

The intended invariant is simple: one shared slit frame produces two persisted lane records, or zero.