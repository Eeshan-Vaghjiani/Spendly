# Spendly final as-built diagram pack

This pack models the implemented Flutter + Flask + PostgreSQL system. The proposal and earlier images were treated as requirements/background only; repository code, migrations, tests, configuration, mobile screens, read-only admin pages, and safe live endpoint inspection determined the final content.

| Diagram | Editable source | Vector | High-resolution raster |
|---|---|---|---|
| Use Case | `01_spendly_use_case_diagram.puml` | `01_spendly_use_case_diagram.svg` | `01_spendly_use_case_diagram.png` |
| Main decision-support Sequence | `02_spendly_sequence_diagram.puml` | `02_spendly_sequence_diagram.svg` | `02_spendly_sequence_diagram.png` |
| User-to-decision-support Activity | `03_spendly_activity_diagram.puml` | `03_spendly_activity_diagram.svg` | `03_spendly_activity_diagram.png` |
| Application Class Diagram | `04_spendly_class_diagram.puml` | `04_spendly_class_diagram.svg` | `04_spendly_class_diagram.png` |
| PostgreSQL ERD | `05_spendly_erd.puml` | `05_spendly_erd.svg` | `05_spendly_erd.png` |

See `00_spendly_as_built_findings.md` for the actor/permission matrix, feature inventory, documentation-versus-implementation decisions, consistency rules, and implementation evidence map.

## Editing and rendering

Edit any `.puml` file in PlantUML-compatible software. Run `render_all.ps1 -PlantUmlJar <path-to-plantuml.jar>` to regenerate all SVG and PNG files. SVG is the preferred print/document format; PNGs are rendered at 220 DPI.

