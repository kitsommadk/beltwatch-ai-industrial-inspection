# Test matrix

| Case | Expected result |
| --- | --- |
| single evidence save | existing behavior preserved |
| valid same-frame A/B batch | two committed lane rows |
| invalid second lane ID | zero committed rows |
| duplicate second lane identity | SQLite error and zero committed rows |
| first A/B temporal assessment | both insufficient-history |
| slit API success | two records sharing frame and position |

All cases are software/replay validation.