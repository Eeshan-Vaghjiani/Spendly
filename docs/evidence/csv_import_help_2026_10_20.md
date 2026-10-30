# CSV import guidance — 20 October 2026

Issue #80. The upload page now has an expandable, selectable six-column CSV
example with synthetic data and an explicit Nairobi timezone. It explains UTF-8,
positive KES amounts, the two-decimal rule, types and recurring flags.

Upload results keep the received/created/duplicate/invalid counts and display up
to 20 rejected row numbers and reasons. Each message is capped at 500 characters;
larger reports explain the limit. Missing details have a format-check fallback.
The page explains that the header is row 1 and identical saved records are skipped
when corrected rows are imported again. No automatic write retry is introduced.

Verification: **142 offline Flutter tests passed, one opt-in live test skipped**;
the analyzer found no issues (26.1 seconds).
Five new tests cover the example, row reasons, missing details, bounded long errors
and expanded help on a 320x640 viewport at 200% text. Initial test interaction
failures were corrected by scrolling/pumping the intended controls before taps;
the final complete suite passed. The API/picker are fake in these widget tests.

The physical session-recovery run also rendered/scrolled the collapsed upload
page with this exact presentation source at 200% text. It did not expand the new
help or perform a new picker/import interaction. Earlier actual native CSV
acceptance remains separate evidence; no new backend parsing claim is made.

No API contract, backend validation, dependency or model change is included.
