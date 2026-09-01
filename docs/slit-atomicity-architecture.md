# Architecture impact

The change is intentionally localized:

`capture_two_lane_inspection_auto` → two lane evidence objects → two scoped temporal assessments → `save_evidence_batch` → SQLite commit/rollback → API response.

No detector/provider interface or frontend API parsing needs to change.