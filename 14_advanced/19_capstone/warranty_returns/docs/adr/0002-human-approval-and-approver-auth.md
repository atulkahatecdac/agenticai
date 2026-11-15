# ADR 0002 – A human approves high-value refunds, and only approvers can approve

- **Status:** accepted (approver authentication added in Part 2)
- **Date:** 2026-11

## Context
Refunds above Rs. 5,000, every rejection and repeat claimants go to a human (LangGraph `interrupt`).
The Part 2 security audit (`19_12_security_audit.py`) found that `POST /tickets/{id}/approve` and
`GET /approvals` had no authentication: anyone who could reach the API could approve a Rs. 65,000 refund.

## Decision
Both endpoints require an `X-Approver-Key` header (`CAPSTONE_APPROVER_KEY`, default only for the classroom).
Ticket messages are limited to 4,000 characters.

## Consequences
- The audit now passes the access-control check; integration tests (19_10) assert 401 without the key.
- A shared key is a stop-gap: production should put the approver UI behind company SSO (OAuth/OIDC) and
  record *who* approved each refund.
