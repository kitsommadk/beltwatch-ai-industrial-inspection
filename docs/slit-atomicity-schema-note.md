# Schema note

Atomic pair persistence does not require an evidence schema-version bump. It changes how existing lane-aware v9 tables are written, not their structure. A future shared-observation/pair-diagnostics table would require explicit schema migration and versioning.