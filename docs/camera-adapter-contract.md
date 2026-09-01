# BeltWatch AI — Camera Adapter Contract

## Purpose
The camera boundary must behave predictably before BeltWatch is allowed to treat live frames as inspection evidence. A provider is responsible for more than returning images: it must expose identity, timestamps, health, failure state, and stale-feed behavior.

## Current hardware research
The selected/considered e-con Systems See3CAM_24CUG is documented by the manufacturer as a UVC-compatible USB 3.1 Gen 1 global-shutter camera with Windows and Linux support. The manufacturer's current product page lists uncompressed UYVY and compressed MJPEG outputs and advertises HD at up to 120 fps and Full HD at up to 60 fps. Exact modes must be enumerated and benchmarked on the BeltWatch edge PC rather than assumed from marketing specifications.

The manufacturer also publishes OpenCV/Python integration guidance for See3CAM-family USB cameras. BeltWatch should still keep OpenCV behind an adapter so the core domain, API, and tests do not require camera drivers.

## Required provider behavior
Every production camera adapter must:

- expose a stable `camera_id`
- produce monotonically increasing frame sequence numbers per process
- timestamp frames as close to acquisition as the runtime permits
- expose frame width/height and an evidence payload reference
- report connected/disconnected state
- report stale state using a configured threshold
- count capture/read failures
- recover explicitly after transient read errors where safe
- never fabricate a frame when a live source is unavailable

## Stale-feed semantics
A camera is `stale` when it is connected, has previously produced a frame, and the age of the most recent frame exceeds the configured stale threshold. Disconnected cameras are reported as disconnected rather than stale.

The current simulated provider defaults to a 2-second threshold. Production thresholds should be derived from the configured frame rate and pilot observations. A 30–60 fps stream would normally require a much tighter detection window, but BeltWatch should benchmark USB scheduling, inference load, and operator workflow before fixing a production value.

## Planned UVC/OpenCV adapter
The first hardware adapter should remain deliberately small:

1. open a configured device index/path
2. request resolution, pixel format, and FPS
3. verify the negotiated mode
4. read frames and timestamp them
5. convert successful reads into `FramePacket`
6. increment failure counters on unsuccessful reads
7. close/reopen after a bounded sequence of failures
8. expose health without blocking the inspection API

OpenCV should be an optional CV dependency rather than part of the lightweight base API requirements.

## Hardware validation checklist
Before `BELTWATCH_INSPECTION_MODE=pilot` is enabled:

- enumerate both physical cameras on the actual edge PC
- confirm stable top/bottom identity across reboot
- verify negotiated resolution/FPS/pixel format
- run both cameras concurrently for an extended soak test
- measure dropped/read failures and reconnect behavior
- verify USB bandwidth and cable-length stability
- test controlled-lighting exposure settings
- verify timestamp/position synchronization
- capture calibration imagery from both physical mounting positions

## Safety rule
A failed or stale live camera must be visible to the operator and inspection runtime. BeltWatch must not silently substitute simulated frames for unavailable live hardware.
