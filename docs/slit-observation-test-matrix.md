# Test matrix

| Case | Expected |
| --- | --- |
| valid replay slit capture | one observation referencing exact A/B evidence |
| mismatched frame sequence | reject before insert |
| wrong lane identity | reject before insert |
| duplicate shared frame | SQLite uniqueness rejection |
| new current session | prior observation not listed |
| single-belt capture | no slit observation |
| initialized schema | foreign-key check clean |
