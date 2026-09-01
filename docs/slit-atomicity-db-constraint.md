# Lane-aware uniqueness constraint

Evidence uniqueness remains `(session_id, camera_id, frame_sequence, lane_id)`. A valid slit frame therefore permits exactly one Belt A and one Belt B record for the same camera/frame. Attempting a second record with the same lane identity violates the constraint and rolls back the batch.