# Frame sequence semantics

Belt A and Belt B retain the same captured frame sequence. The uniqueness key includes lane ID, allowing both records to coexist while preventing a duplicate record for the same lane/session/camera/frame. The rollback regression uses this constraint to prove all-or-nothing behavior.