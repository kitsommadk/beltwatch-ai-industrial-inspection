# Transaction definition

A database transaction is a group of changes treated as one unit. For BeltWatch slit evidence, that means SQLite either commits both lane records and their child data, or rolls the attempted group back. This is the software mechanism behind the all-or-nothing evidence guarantee.