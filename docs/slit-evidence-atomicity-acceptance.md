# Acceptance criteria

The atomic slit persistence change is acceptable when:

- existing single-belt persistence behavior still passes,
- a valid same-frame A/B pair persists both lanes,
- first-frame A/B temporal history is independently insufficient,
- a forced second-record uniqueness failure rolls back the first record,
- the successful slit API response remains compatible,
- repository CI is green.