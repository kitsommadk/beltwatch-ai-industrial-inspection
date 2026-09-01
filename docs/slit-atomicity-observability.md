# Observability boundary

The existing audit log records successful committed lane captures. Failed database batches currently rely on application/server logging rather than a durable audit record, because writing a durable failure audit through the same failing storage path may itself be impossible. Operational logging/health telemetry remains a later reliability-hardening area.