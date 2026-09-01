# Recovery behavior

If a slit evidence batch fails, the operator may capture another frame after the underlying error is resolved. The failed batch leaves no partial A/B evidence rows to clean up. Camera/replay sequence numbers may advance because acquisition occurs before persistence; BeltWatch should not fabricate replacement sequence numbers to hide that fact.