# Test truthfulness

The rollback test proves SQLite transaction semantics for the application code path. It does not simulate abrupt process termination, OS crash, storage-device failure or power loss. Those should be described separately if/when edge-PC reliability testing is performed.