# Batch persistence compatibility

The public single-record `save_evidence` function remains unchanged at its call boundary. Internally it delegates to `save_evidence_batch` with one `EvidenceWrite`. This avoids duplicating insert logic and keeps existing single-belt persistence tests meaningful while enabling all-or-nothing multi-lane writes.