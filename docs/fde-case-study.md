# Forward-deployed engineering case study

## 1. Discovery

I started with the operating workflow, not an assumed AI solution. Discussions
with leadership and operators narrowed a broad belt-health concept into a testable
first mission on one slitter:

- inspect both belt surfaces;
- measure width from both edges;
- tie evidence to footage position and cut length;
- keep the system observational, not in machine control; and
- work locally inside the plant environment.

That discovery changed the product shape. Target length, operator disposition,
top/bottom imaging, local storage, and network isolation became core requirements.

## 2. Technical scoping

I separated three questions that are often collapsed into “build an AI app”:

1. Can the installation produce stable, repeatable images?
2. Can measurement/detection meet agreed evaluation criteria?
3. Can operators use the evidence workflow safely and consistently?

This let the team validate the workflow before claiming a production model.

## 3. End-to-end implementation

The implemented prototype includes:

- React operator interface;
- Python/FastAPI service;
- SQLite session, event, review, and audit persistence;
- explicit domain/API contracts;
- simulated detector behind a replaceable provider boundary;
- integration tests for the primary mission workflow; and
- local container deployment.

The simulation is labeled throughout. It exercises integration and user experience;
it is not presented as trained-model performance.

## 4. Enterprise deployment reasoning

The company operates production and inventory systems on a private network. For
Phase 1, I proposed a restricted pilot segment with a stable private address,
approved clients only, no public inbound access, and no direct connection to
inventory or machine-control systems.

The longer-term design uses outbound-only encrypted event synchronization. Local
inspection continues if the internet fails, while authorized remote users receive
approved event packets rather than unrestricted plant video.

## 5. Live troubleshooting and durable improvement

During stakeholder demo setup, the backend failed to install on a Windows machine
because the virtual environment used a new Python version without a compatible
prebuilt dependency. I identified the interpreter mismatch, rebuilt the environment
on Python 3.12, installed dependencies in the correct sequence, verified FastAPI,
then brought up the React console.

The durable improvement in this repository is explicit Python-version guidance plus
containerized startup, reducing machine-specific setup risk.

## 6. Stakeholder communication

Leadership materials deliberately separate:

- what works now;
- what is simulated;
- what the controlled pilot will validate; and
- what belongs to the remote Phase 2 roadmap.

That distinction protects technical credibility while still making the future
architecture understandable to non-software stakeholders.

## 7. Next production gates

Before the system can be called production-ready, it needs hardware commissioning,
calibration/versioning, labeled data, agreed metrics, repeatability tests, failure-
mode testing, authentication/authorization, HTTPS, retention rules, observability,
and an IT-approved service deployment.

