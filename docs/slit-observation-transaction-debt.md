# Transaction debt

Current sequence:

1. atomic Belt A/B evidence batch commits;
2. shared observation row commits;
3. audit entries commit.

This means an observation-write failure could leave a valid A/B evidence pair without its shared observation row. The evidence itself remains complete, but the relationship ledger would be incomplete. Before relying on the ledger as a required production invariant, combine steps 1 and 2 under one transaction.
