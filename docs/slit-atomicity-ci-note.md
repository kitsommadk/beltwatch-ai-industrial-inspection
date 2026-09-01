# CI note

This branch intentionally changes backend persistence internals and adds backend regressions while leaving the frontend contract unchanged. Frontend CI should still remain green because successful slit auto-capture keeps the same wrapper and record fields introduced previously.