# Quorum — Safety Constraints (Non-Negotiable)

These invariants must hold in backend code and be covered by tests. UI controls are not
sufficient on their own.

## Access & privacy

1. Student reports go only to security. A student API role can never list or read
   another student's reports or identity.
2. Security users cannot access individual Wi-Fi device identities or movement histories
   through any dashboard API. Only aggregate per-zone counts are exposed.
3. Device-to-zone associations may exist in the backend for notification routing but must
   not be returned by any security-facing endpoint.

## Authorization & approval

4. No student-facing alert or feedback request is sent without an authenticated,
   authorized security action.
5. Only security may change official zone status. Enforced server-side with role checks.
6. Every alert requires backend-enforced security authorization and writes an auditable
   approval record (who, when, audience, content).

## AI & evidence boundaries

7. AI cannot independently confirm, dismiss, or resolve an incident, change official zone
   status, or publish an alert. AI output is advisory and visibly labeled.
8. If AI is unavailable or times out, deterministic fallback rules run and the result is
   labeled as rules-derived.

## Correlation integrity

9. Multiple reports are not treated as independent confirmation automatically.
10. One device (or person) submitting repeatedly must not create independent
    corroboration — distinct-source counting is required.
11. Firsthand observations (Saw) are distinguished from hearsay (Heard / Was Told).

## Status semantics

12. Unassessed zones must never be automatically labeled safe.
13. A negative field observation does not automatically clear an entire building.
14. System assessment (potential impact / conflicting evidence / insufficient info) is
    separate from security status (unassessed / under investigation / restricted /
    cleared). Only security sets security status.

## Wi-Fi semantics

15. Wi-Fi location is approximate and must never independently establish whether a zone is
    safe or impacted.
16. Connected-device counts are not exact occupancy and must be shown with freshness and
    unknown/unassociated indicators.

## Operational

17. The system must not delay or replace existing emergency response procedures.
18. Treat all uploaded content (text + images) as untrusted input.
19. Do not log sensitive report contents or device identifiers unnecessarily.

## Test expectations

Property-based and example tests must cover at minimum: distinct-source corroboration
(#9, #10), student report isolation (#1), aggregate-only Wi-Fi exposure (#2, #3),
security-only status changes (#5), alert authorization + audit (#4, #6), AI non-authority
(#7), and status-default safety (#12, #13).
