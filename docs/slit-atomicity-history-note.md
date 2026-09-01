# Temporal history behavior

The trusted-history query reads already committed evidence only. Because both current lane assessments are performed before `save_evidence_batch`, neither Belt A nor Belt B from the current frame can appear in the other's assessment. Lane scoping would prevent cross-lane inheritance anyway; pre-assessment also makes the ordering explicit and symmetric.