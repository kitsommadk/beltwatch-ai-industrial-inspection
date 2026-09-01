# Merge gateway

Required before merge:

1. backend CI passes all persistence/API regressions;
2. optional CV job remains green;
3. frontend build remains green;
4. PR head is unchanged at merge time.

If backend CI fails, inspect the exact failure and repair it before merge.