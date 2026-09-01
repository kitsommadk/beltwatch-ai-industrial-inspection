# Slit pair persistence review

The pair writer is deliberately generic enough for related evidence records but the API currently uses it specifically for expected two-lane slit capture. Exact lane-count/identity validation remains upstream in the multi-lane capture pipeline and session model.

This keeps persistence focused on transaction integrity rather than duplicating run-layout business rules.