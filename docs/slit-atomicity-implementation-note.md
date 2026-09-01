# Implementation note

The transaction relies on the existing database context manager rather than manual `BEGIN`/`COMMIT` statements. This keeps rollback behavior consistent with the rest of BeltWatch and avoids nested transaction handling in the persistence helper.