# Spendly - final plain diagrams and wireframes

This replacement set follows the supplied examples' academic visual style: white backgrounds, thin outlines, plain text and minimal wireframe placeholders. All content describes **Spendly**, not the reference project. Only the system architecture uses colour and technology logos.

Revised on 7 September 2026: architecture content shortened and body text increased from 23 to 32 units; sequence message text increased from 23 to 30 units with adjusted spacing. The schema now uses ten independent routes, matching R1–R10 endpoint labels, a relationship key and explicit bridge marks at crossings. Two essential mobile wireframes were added: Budgets and Spending Check.

## The 13 final images

| No. | Image | Scope |
| --- | --- | --- |
| 01 | [Database schema](png/01_Database_Schema.png) | All 11 application tables, 97 fields, PK/FK/UQ markers, SQL types, nullable fields and declared relationships. |
| 02 | [Entity relationship diagram](png/02_Entity_Relationship_Diagram.png) | Named relationships, cardinalities and selected entity attributes. |
| 03 | [Use-case diagram](png/03_Use_Case_Diagram.png) | Registered-user and administrator capabilities within Spendly's system boundary. |
| 04 | [Activity diagram](png/04_Activity_Diagram.png) | Sign-in, transaction entry/import, validation, forecasting, anomaly scoring and result display. |
| 05 | [Sequence diagram](png/05_Sequence_Diagram.png) | Requesting fresh spending insights through the mobile client and backend. |
| 06 | [Class diagram](png/06_Class_Diagram.png) | Core implemented domain/service classes, selected attributes, methods and associations. |
| 07 | [System architecture](png/07_System_Architecture.png) | Flutter mobile client, browser administration, Flask/Python, internal analysis modules and PostgreSQL. |
| 08 | [Mobile dashboard wireframe](png/08_Wireframe_Dashboard.png) | Financial overview and core navigation. |
| 09 | [Add transaction wireframe](png/09_Wireframe_Add_Transaction.png) | The core financial-data input screen. |
| 10 | [Forecast results wireframe](png/10_Wireframe_Forecast_Results.png) | Estimated spending, learning progress, accuracy state and guidance. |
| 11 | [Administrator dashboard wireframe](png/11_Wireframe_Admin_Dashboard.png) | Account/record management, stored insights, audit and system controls. |
| 12 | [Budgets wireframe](png/12_Wireframe_Budgets.png) | Budget limits, spending progress, available amount and budget actions. |
| 13 | [Spending Check wireframe](png/13_Wireframe_Spending_Check.png) | Unusual-spending explanations and review guidance. |

The six wireframes cover overview, transaction input, forecasting, budgets, anomaly results and administration. The five user wireframes are portrait mobile layouts; the administrator wireframe is a browser layout because Spendly's administrator console is web-based. They are low-fidelity design drawings, not app screenshots. Bracketed values and the LOGO box are placeholders, not measured results. Budgets and Spending Check were selected because they cover core features absent from the initial four screens; their content was checked against the Flutter screen implementations.

## Which files to use

- **png/**: the 13 high-resolution final images for reports and presentations. Technical diagrams and the admin wireframe are 4,000 pixels wide; the five portrait wireframes are 1,800 pixels wide.
- **svg/**: scalable, editable equivalents with live diagram text. Architecture logos are embedded so the files remain self-contained.
- **Preview_All_Images.png**: a thumbnail index only. Use the individual PNGs for submission.
- **Database_Data_Dictionary.md**: every field, key, index and delete rule, exported from the ORM.
- **source/**: reproducible drawing/export scripts, schema metadata, a documentation-only SQL reference, and the verification report.
- **assets/**: official technology artwork, provenance and content hashes.

## Accuracy and implementation boundaries

Checked against branch `agent/spendly-live-deployment`, commit `b0a0f8550d6673bb04d7b18a27a0e734893c1dfb`, on 31 August 2026. The application, APK, database and deployed service were not changed by this documentation task. Previous image packs were preserved.

- The database schema is generated from `backend/app/models/entities.py`: **11 application tables, 97 columns and 10 foreign-key constraints**. Alembic's own migration-bookkeeping table is excluded.
- The schema contains three-column table boxes (key, field, type). The separate ERD emphasizes named associations and cardinalities. Its attribute lists are deliberately selective; the complete schema and data dictionary remain authoritative.
- Each schema relationship has an independent continuous route labelled R1–R10 at both ends. Curved bridge marks mean crossing without connection. The relationship key names the exact referenced primary key and referencing foreign key; parent endpoints distributed around a table are table-level connection ports. `source/schema_routes.json` records these ten routes.
- Identifiers are VARCHAR(36), amounts are NUMERIC(14,2), and timestamps are stored without timezone information while application code uses UTC. The image abbreviates TIMESTAMP WITHOUT TIME ZONE to TIMESTAMP.
- A run has zero or one forecast at database level because `forecasts.analysis_run_id` is unique. A successful run normally creates one. An alert may reference zero or one transaction; deleting that transaction sets the reference to null.
- `model_versions` is not linked by declared foreign keys from result-version strings. Audit target identifiers are not foreign keys either. No fictional relationships or extra feedback/category/schedule tables were added.
- Administrator credentials are configured outside the users table. Administration is implemented through protected Flask route handlers, not a fabricated `Admin` subclass or a database `role` field. The class diagram focuses on the implemented analysis flow; account and administration use cases are shown separately.
- The documented live configuration is **lightweight v1**: multiple linear regression after sufficient history, a weekly-average baseline for early history, Isolation Forest anomaly scoring, and transparent recommendation rules. The research V2 models are not presented as deployed. See `docs/model_integration_readiness_v2.md` for the integration gate.
- Feature preparation and model execution are internal Python modules within the Flask backend process, not separate network microservices. Model artifacts load from backend files; requesting insights does not retrain models.
- Administrators can manage users and correct transactions/budgets. Historical forecasts, alerts and recommendations are inspected rather than edited. Pausing analysis affects fresh analysis requests, not existing history.
- The activity diagram is an end-to-end transaction-to-insight example. The sequence diagram focuses on a successful insight request with the early-history/model alternative; it is not a full catalogue of every API error path.

The supplied images informed visual style only. UML checks used standard activity decisions/merges, actor associations, multiplicities and include/dependency arrow direction; see [IBM's include-relationship guidance](https://www.ibm.com/docs/en/dma?topic=diagrams-include-relationships) and [dependency guidance](https://www.ibm.com/docs/en/dma?topic=diagrams-dependency-relationships). No separate university marking rubric was supplied, so this pack does not claim rubric-specific approval.

## Technology artwork credits

Official artwork identifies the technologies used; it is not Spendly branding and does not imply endorsement. Original downloads are preserved in `assets/`; exact download URLs and SHA-256 hashes are recorded in [assets/sources.json](assets/sources.json). Proportional PNG renderings remove only transparent renderer padding, without changing the logo artwork.

- Flutter: [Flutter brand resources](https://flutter.dev/brand).
- Python: [Python logo resources](https://www.python.org/community/logos/).
- Flask: [Flask documentation](https://flask.palletsprojects.com/en/stable/).
- scikit-learn: [scikit-learn project](https://scikit-learn.org/stable/).
- PostgreSQL: [PostgreSQL press resources](https://www.postgresql.org/about/press/).

## Rebuilding

Run from this repository, with Python/Pillow, the backend's dependencies, Node and Sharp available:

```powershell
python output/Spendly_Final_Images_Plain/source/export_schema.py
node output/Spendly_Final_Images_Plain/source/prepare_logos.cjs
python output/Spendly_Final_Images_Plain/source/build_images.py
node output/Spendly_Final_Images_Plain/source/render_images.cjs
python output/Spendly_Final_Images_Plain/source/verify_and_package.py
```

The current scripts use Windows Arial fonts and the installed Sharp location. Set `SPENDLY_SHARP_PATH` to your Sharp installation if needed. `fetch_logos.py` is optional because the original assets are included. `schema_reference.sql` is documentation only; it is not a replacement for migrations and was not executed against any database.
