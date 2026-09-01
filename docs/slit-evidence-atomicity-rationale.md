# Why slit evidence is atomic

A two-lane slit capture is one observation containing two independently measured products. Persisting Belt A and Belt B in separate transactions creates a failure mode where the database can contain half of a shared observation.

`save_evidence_batch` removes that failure mode by using the existing `connect()` transaction boundary for the entire related write set. The existing single-evidence API is retained as a one-item batch wrapper, keeping backward compatibility while giving slit capture a stronger integrity contract.