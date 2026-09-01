# Design decision

Use a generic evidence batch transaction now instead of introducing a shared-observation schema immediately. This solves the concrete partial-persistence risk with minimal schema disruption. Normalize shared observation metadata later when pair diagnostics are persisted historically.