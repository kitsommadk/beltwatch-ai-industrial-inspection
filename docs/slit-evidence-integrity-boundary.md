# Evidence integrity boundary

Atomic persistence protects against partial database representation of a shared two-lane observation. It does not prevent upstream acquisition/estimation errors; those remain handled by fail-closed capture and quality gates before persistence.

The two mechanisms complement each other: quality gates decide whether evidence is trustworthy enough to write, and the transaction ensures accepted A/B evidence is written completely.