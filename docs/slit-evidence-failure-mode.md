# Eliminated partial-pair failure mode

Before this change, the slit API called single-record persistence once for Belt A and then once for Belt B. If Belt A committed and Belt B failed, BeltWatch could retain an orphan lane record from a frame that was supposed to represent both products.

The batch transaction removes that database failure mode. It does not make camera capture transactional; a frame may still be acquired and then rejected before persistence.