# Performance note

Batching the two slit lane records into one SQLite transaction should reduce transaction overhead relative to opening and committing separate evidence transactions. No performance claim is made until edge-PC benchmarking is run on the selected hardware.