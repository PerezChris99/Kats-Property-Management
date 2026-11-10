# Tenancy disputes and preventive maintenance — operator workflows

## Rental disputes

Tenants can open a dispute against their current or previous lease, select
RENT, DEPOSIT, REPAIR, SERVICE, NOTICE or OTHER, and add chronological written
responses. Only the linked tenant can read the case; the owner/manager/
authorized finance staff have business-level view. Owners, managers and
super-admins record documented internal decisions or reopen a closed case.

**A case status is NOT a court judgment, legal eviction, delivered statutory
notice, payment refund, or approval to withhold funds.** This module only
preserves a consistent record for staff and tenant review.

Key endpoints: \`GET/POST /api/v1/disputes\`,
\`GET /api/v1/disputes/eligible-leases\`,
\`GET /api/v1/disputes/<id>/events\`,
\`POST /api/v1/disputes/<id>/comments\`,
\`POST /api/v1/disputes/<id>/decision\`.

## Preventive maintenance

Owners/managers/super-admins register room-specific recurring plans with
a description, priority, first due date and cadence of 1–366 days.
Caretakers can see only plans assigned to their rooms.
An automated scheduled Celery task creates a normal OPEN maintenance
request for each due plan and records a unique occurrence. Retry protection
and database row locks avoid a second maintenance request for the same date.

A paused plan does not generate new requests. A retired plan cannot silently
be reactivated. Resuming a plan already overdue will generate its next due
request on the next daily run, then advance the schedule beyond today.

Key endpoints: \`GET/POST /api/v1/maintenance/plans\`,
\`POST /api/v1/maintenance/plans/<id>/status\`,
\`GET /api/v1/maintenance/plans/<id>/occurrences\`.

**Not implemented:** vendor procurement, service provider invoices, job
completion evidence, statutory fire/lift/water/electrical certification,
formal escalation deadlines, asset-level maintenance history and contract
signature. Tenant personal information must not be included in contractor
tickets without approved access and privacy safeguards.

## Acceptance

Verify actual Celery schedule and worker restarts, concurrent worker
generation, scheduled due dates in Africa/Kampala, tenant IDOR/cross-lease
blocking, caretaker assignment isolation, real inspection evidence and
actual landlord dispute procedures.
