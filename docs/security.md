# Secure deployment notes

This is a portfolio build, not a production security certification.

## Phase 1 network boundary

- Place the edge PC on an IT-approved restricted VLAN or pilot segment.
- Permit console access only from approved private-network devices.
- Do not forward API ports through the company firewall.
- Give the edge PC no unnecessary route to inventory, production, or control systems.
- Prefer direct USB cameras; isolate network cameras if introduced later.
- Run the API under a restricted operating-system account as a managed service.
- Encrypt the disk and define backup/retention responsibilities.

## Application hardening before real data

- Put the API behind an internal HTTPS reverse proxy.
- Require individual accounts and role-based authorization.
- Disable or restrict interactive API documentation.
- Use an allowlist for frontend origins and client networks.
- Move secrets out of source and rotate them through an approved process.
- Add structured security and application logs with clock synchronization.
- Validate uploads and cap request sizes.
- Define evidence retention and secure deletion.

## Camera and privacy boundary

Position cameras for the belt inspection purpose and avoid capturing identifiable
people where possible. Before real plant imagery is stored or transmitted, confirm
customer authorization, employee/visitor notice requirements, ownership, access,
retention, and allowed secondary uses.

## Phase 2 remote access

Use outbound-only encrypted synchronization from the edge node to a cloud service.
Require MFA, per-customer/plant authorization, audit logs, revocation, and tenant
isolation. Prefer event snapshots and clips over continuous raw-video upload.

