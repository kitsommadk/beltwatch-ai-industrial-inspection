# Next persistence step

After the atomic lane-pair path is validated, the next persistence candidate is same-frame pair diagnostics (gap, lane centers, center distance and occupied span). Those values should be attached to a shared observation identity rather than duplicated independently on Belt A and Belt B.

That schema work should preserve the current rule that pair diagnostics are observations, not root-cause classifications.