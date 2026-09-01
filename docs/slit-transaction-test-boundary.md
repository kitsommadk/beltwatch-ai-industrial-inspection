# Transaction test boundary

The rollback regression deliberately creates a duplicate lane identity for the same session/camera/frame so SQLite rejects the second record under the existing unique constraint. The assertion then confirms the first insert was rolled back as part of the same transaction.

This is a deterministic way to prove transaction behavior without needing to simulate storage hardware failure.