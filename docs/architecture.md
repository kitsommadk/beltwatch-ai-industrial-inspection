# Architecture decision record

## Context

The first BeltWatch deployment is a controlled quality-assurance pilot on an
industrial belt slitter. The environment has physical mounting constraints, top
and bottom imaging requirements, a private production network, and a need to avoid
interfering with machine control. The longer-term product adds remote belt-health
inspection across multiple plants.

## Decision

Use a local edge computer as the inspection authority for Phase 1.

- USB cameras and controlled lighting connect to the edge computer.
- The Python service owns measurement/detection adapters and workflow state.
- FastAPI provides a narrow contract to the React operator console.
- Inspection sessions, event metadata, reviews, and audit records persist locally.
- The pilot has no write access to the slitter, inventory system, or production database.

## Why this shape

| Constraint | Design response |
|---|---|
| Inspection cannot depend on internet | Local compute, storage, and UI |
| Existing systems are sensitive | No Phase 1 integration; manual work-order fields |
| Model is not yet production-validated | Provider interface with explicit simulation |
| Operators need evidence | Footage position, measurement, source, confidence, disposition |
| False positives are expected during tuning | First-class false-positive review state |
| Future remote viewing is required | Preserve a clean event contract for outbound sync |

## Runtime data flow

1. Operator creates a session with roll and cut specifications.
2. Frame adapter attaches camera, time, and footage-position metadata.
3. Measurement/detection provider emits a candidate event.
4. API persists evidence metadata and presents it in the console.
5. Operator acknowledges or rejects the event.
6. Disposition and note are recorded in the audit trail.
7. In Phase 2, approved event packets can synchronize outward.

## Detection provider seam

`backend/app/detection.py` defines the interface between the workflow system and
the detection implementation. The public repository uses `SimulatedDetector`.
A production implementation would accept calibrated frames and return the same
domain object after inference and thresholding.

This prevents a camera/model experiment from becoming entangled with session,
review, reporting, or UI code.

## Phase 2 boundary

The edge service should initiate an encrypted outbound connection. It may send:

- camera and service health;
- inspection progress and measurements;
- event metadata;
- selected snapshots or short evidence clips; and
- an on-demand lower-resolution stream when the customer allows it.

It should not expose FastAPI directly to the public internet. Full-resolution
continuous video remains local by default.

## Known tradeoffs

- SQLite is appropriate for one edge node and a controlled pilot, not a shared
  multi-plant service.
- The portfolio uses a simple latest-session model; production needs explicit
  session identifiers and retention rules.
- Authentication is intentionally not represented as complete. Production needs
  identity, roles, session expiration, and revocation.
- Real footage-position synchronization needs encoder or machine telemetry input.

