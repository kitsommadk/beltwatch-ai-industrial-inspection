# Calibration context

The v1 shared observation stores pair geometry in image pixels and references lane evidence that carries calibration profile/version. The shared row does not yet duplicate or assert a pair-level calibration identity. Temporal pair analysis must account for this before comparing observations across calibration changes.
