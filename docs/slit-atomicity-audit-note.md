# Audit semantics

A successful slit batch is followed by per-lane `evidence.captured` audit entries and one `evidence.multilane_captured` entry. These describe committed evidence but are not transactionally coupled to it. Future production hardening may move evidence and audit writes under a shared transaction if that guarantee becomes a requirement.