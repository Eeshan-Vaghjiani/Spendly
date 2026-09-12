# Spendly Chapter 4 final diagrams

This package contains 14 final black-and-white figures for the **Spendly Personal Finance Management System**. Every figure is supplied as a high-resolution PNG for insertion into the report and an editable SVG source.

## Final analytical design used in every figure

- **LSTM v1** forecasts next-week spending when at least eight complete weeks of history are available.
- A **personal weekly-average fallback** is used when fewer than eight complete weeks are available.
- **Isolation Forest v1** identifies unusual-spending review prompts. An alert is not a fraud finding.
- The **rule-based recommendation engine** produces transparent planning guidance.
- No linear-regression model is shown or implied.

## Submission order, orientation and captions

| No. | Figure | Recommended page | Ready-to-use caption |
|---:|---|---|---|
| 1 | Final use case diagram | Full landscape | **Figure 4.X: Final use case diagram for the Spendly Personal Finance Management System.** The figure separates mobile-user services from administrator-console functions and shows the analytical functions included in insight generation. |
| 2 | Add or import transaction activity diagram | Portrait | **Figure 4.X: Activity flow for manually adding or importing Spendly transactions.** Validation issues return to the relevant input step before records can be saved. |
| 3 | Generate spending insights activity diagram | Portrait | **Figure 4.X: Activity flow for generating spending insights.** LSTM forecasting or the weekly-average fallback runs in parallel with Isolation Forest analysis before rule-based recommendations are produced. |
| 4 | Generate spending insights sequence diagram | Full landscape | **Figure 4.X: Sequence of interactions used to generate spending insights.** The authenticated `POST /api/v1/analysis/run` request returns a compact error response when rejected and stores all successful analytical outputs under one analysis run. |
| 5 | UML class diagram | Full landscape | **Figure 4.X: Implementation-aligned UML class diagram for Spendly.** The model links forecasts, alerts and recommendations to `AnalysisRun` and represents category values as text. |
| 6 | Conceptual ERD | Full landscape | **Figure 4.X: Conceptual entity-relationship diagram for Spendly.** The figure presents business entities and cardinalities without duplicating physical database types or indexes. |
| 7 | Logical database schema | Full landscape | **Figure 4.X: Logical database schema for Spendly.** This is the primary data-design figure and includes user-owned data, analytical outputs, model versions, audit events and system settings. |
| 8 | System architecture | Full landscape | **Figure 4.X: Target system architecture for Spendly.** The diagram shows explicit request and response directions across the Flutter client, Flask services, analytical components and Neon PostgreSQL deployment. |
| 9 | Dashboard wireframe | Portrait | **Figure 4.X: Spendly dashboard wireframe.** The design uses one period selector and keeps forecast, spending-check and recommendation summaries distinct. |
| 10 | Add transaction wireframe | Portrait | **Figure 4.X: Spendly add-transaction and CSV-import wireframe.** The screen shows category entry, the import path and a visible validation-error state. |
| 11 | Forecast results wireframe | Portrait | **Figure 4.X: Spendly forecast-results wireframe.** Forecast readiness is expressed through available history, with the weekly-average fallback explained for fewer than eight weeks. |
| 12 | Spending check wireframe | Portrait | **Figure 4.X: Spendly unusual-spending review wireframe.** Each alert presents its date, amount and category and provides a Mark as reviewed action. |
| 13 | Budgets wireframe | Portrait | **Figure 4.X: Spendly budgets wireframe.** Total and category budgets use the same consistent limit, spent and remaining definitions. |
| 14 | Administrator dashboard wireframe | Full landscape | **Figure 4.X: Spendly administrator-dashboard wireframe.** The interface distinguishes view-only information from controlled update and delete operations. |

Replace `4.X` with the final figure number after arranging the figures in the dissertation. Keep each figure immediately after the paragraph that introduces it and follow it with a short interpretation paragraph. Do not place the full-landscape figures inside a portrait page at reduced scale.

## Important implementation-alignment check before submission

The diagrams follow the confirmed final model decision: LSTM, Isolation Forest and the rule-based recommendation engine only. The repository inspected while preparing these figures still contains three implementation differences that should be resolved before the diagrams are described as fully *as built*:

1. The current forecasting runtime still contains linear-regression paths, including a weighted LSTM/linear-regression blend and a lightweight deployment mode. Remove or disable those paths if the final implementation is LSTM-only.
2. The final schema and wireframe include `review_status`, `reviewed_at` and **Mark as reviewed**, but the inspected backend does not yet expose that alert-review update.
3. The logical schema shows the required authentication invariant, `password_hash OR google_subject`; the inspected database migration/model does not yet enforce it as a database check constraint.

The figure content is internally consistent, but these code/database differences must not be overlooked in the implementation narrative or demonstration.

## File use

- Insert the `.png` versions into the final report.
- Keep the matching `.svg` files as editable sources and AI-use evidence.
- Use `00_technical_diagrams_overview.png` and `00_wireframes_overview.png` only for review; do not submit them as Chapter 4 figures.
- Exclude the older drafts and the generic types-of-ERD image from the submitted chapter.
