# Slit auto-capture persistence sequence

1. Capture one frame.
2. Estimate Belt A/B geometry from that frame.
3. Sample one position.
4. Build independent A/B width evidence.
5. Assess temporal quality for A and B against prior scoped history.
6. Persist both evidence records and child provenance in one transaction.
7. Write audit entries after the evidence commit.
8. Return lane records plus response-time pair diagnostics.

This ordering prevents either current lane from contaminating the other's temporal history and prevents partial pair persistence.