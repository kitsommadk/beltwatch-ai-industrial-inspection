# Atomic slit evidence validation note

The regression suite covers both the successful same-frame Belt A/B batch and rollback behavior when the second lane conflicts with the first lane's unique evidence identity. The rollback assertion verifies that no orphan Belt A record remains after SQLite rejects Belt B.

This test exercises database transaction integrity using replay/generated evidence. It is not a physical-camera validation.