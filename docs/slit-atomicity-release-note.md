# Pilot release note: atomic slit evidence

Two-lane replay auto-capture now writes Belt A and Belt B evidence through a shared SQLite transaction. This prevents an interrupted/invalid second-lane write from leaving a misleading one-lane record for a frame that was intended to represent two belts.

No API response-shape change is intended for successful slit capture.