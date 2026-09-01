# Slit evidence integrity contract

For automatic two-lane slit capture, Belt A and Belt B share one captured frame and one position sample. BeltWatch now treats their persisted evidence as one database unit: both lane records commit together or neither commits.

Each lane remains an independent measurement with its own target, tolerance result, geometry provenance and temporal assessment. Pair atomicity does not merge the measurements or create an aggregate slit width.

This is a software/data-integrity guarantee validated with replay/generated inputs. It does not imply physical camera accuracy or production metrology qualification.