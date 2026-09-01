# Data integrity improvement

The core improvement is not a new measurement; it is stronger evidence semantics. A database reader can treat a successful automatic slit observation as a complete A/B pair rather than wondering whether one lane was lost because the second write failed after the first committed.