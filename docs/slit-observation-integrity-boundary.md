# Integrity boundary

The existing Belt A/B evidence batch remains atomic. The shared observation row is currently inserted immediately after that evidence batch commits, in a separate transaction. Therefore this feature must not yet be described as one atomic evidence-plus-observation transaction.

A later hardening step can move the observation insert into the same transaction if that stronger guarantee is required before physical pilot deployment.
