# Spendly revised Chapter 4 figures

This folder is the corrected, source-style replacement set for the six files identified during review. It intentionally preserves the visual language of the original accepted work: white backgrounds, black UML notation, rounded activity boxes, clean table compartments, large Arial labels and the existing architecture logos/blue accents.

## Final files

| Figure | Submission orientation | Main corrections |
|---|---|---|
| `01_Database_Schema_Final` | Full landscape page | Preserves the original table UI; includes `ANALYSIS_RUNS`, model/admin/system tables, alert review fields, the authentication check, text categories and externally configured administrator identity. |
| `02_Final_Use_Case_Diagram` | Full landscape page | Splits Register and Sign in; aligns administrator actions to the implemented console; retains implemented export; shows LSTM, Isolation Forest and rule-based analytical functions without crossing labels or use cases. |
| `03_Activity_Add_Import_Transaction_Final` | Portrait page | Adds a decision after duplicate/category checks. Manual and CSV problems return to their exact originating input paths before records can be saved. |
| `04_Activity_Generate_Spending_Insights_Final` | Portrait page | Preserves the accepted activity layout and labels the guards as eight or more complete weeks and fewer than eight complete weeks. Uses LSTM, Isolation Forest and the rule-based recommendation engine. |
| `05_Sequence_Generate_Spending_Insights_Final` | Full landscape page | Uses `POST /api/v1/analysis/run` with Bearer JWT, includes a compact rejected-request alternative, identifies the model service/artefact loader, uses LSTM and the weekly-average fallback, and retains Isolation Forest plus rule-based recommendations. |
| `06_System_Architecture_Final` | Full landscape page | Preserves the original logos, blue-accented component cards and arrow layout. Removes regression, identifies LSTM, Isolation Forest and the rule-based engine, and retains Render/Neon deployment wording. |

Each figure is supplied as an editable `.svg` and a high-resolution `.png`. Use the PNG in the report and retain the SVG as the editable master.

## Consistent analytical design

- LSTM: next-week spending forecast when at least eight complete weeks are available.
- Personal weekly-average fallback: used only when fewer than eight complete weeks are available.
- Isolation Forest: unusual-spending review prompts, not fraud findings.
- Rule-based recommendation engine: transparent planning guidance.
- Linear regression is not included anywhere in the final figures.

The existing class diagram and ERD images were not restyled or replaced in this set. Their accepted visual treatment was used as a reference for the revised database schema and other technical figures.

## Implementation-alignment note

The database schema shows `review_status`, `reviewed_at` and the `password_hash OR google_subject` check because they are required by the review feedback. The inspected backend still needs those changes before the figure can be described as fully implemented. The inspected runtime also still contains regression paths that must be removed or disabled if the final deployed system is LSTM-only.
