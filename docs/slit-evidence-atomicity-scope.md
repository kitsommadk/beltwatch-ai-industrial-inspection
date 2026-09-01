# Atomicity scope

Included in the single SQLite transaction:

- Belt A inspection evidence
- Belt B inspection evidence
- each lane's geometry provenance
- each lane's frame-quality record
- each lane's temporal-quality record

Outside that transaction:

- audit-log entries
- response-time pair diagnostics
- camera acquisition itself

The distinction prevents the pilot from claiming a broader transactional guarantee than the code provides.