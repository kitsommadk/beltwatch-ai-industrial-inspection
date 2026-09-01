# Data model

A slit observation is shared context, not a third belt measurement. It references two independent evidence rows (`belt-a` and `belt-b`) and stores only relationship-level values that belong to the shared frame.

This avoids duplicating pair diagnostics onto each lane and gives future temporal pair analysis one canonical history row per accepted frame.
