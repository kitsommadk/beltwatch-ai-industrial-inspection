# History semantics

Observation history is append-only under the current API. A repeated attempt to persist the same session/camera/frame identity is rejected by a unique constraint rather than silently replacing prior evidence. This preserves traceability and prevents diagnostic history from being rewritten implicitly.
