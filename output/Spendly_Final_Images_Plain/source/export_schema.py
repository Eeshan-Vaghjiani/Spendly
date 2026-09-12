"""Read Spendly's SQLAlchemy metadata; export documentation without connecting to a DB."""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
DEST = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from backend.app.extensions import db  # noqa: E402
from backend.app import models  # noqa: E402,F401
from sqlalchemy import UniqueConstraint  # noqa: E402
from sqlalchemy.dialects import postgresql  # noqa: E402
from sqlalchemy.schema import CreateIndex, CreateTable  # noqa: E402


def main():
    dialect = postgresql.dialect()
    tables = []
    for table in db.metadata.sorted_tables:
        unique_sets = [list(c.columns.keys()) for c in table.constraints if isinstance(c, UniqueConstraint)]
        unique_sets += [list(i.columns.keys()) for i in table.indexes if i.unique]
        columns = []
        for col in table.columns:
            columns.append({
                "name": col.name,
                "type": str(col.type.compile(dialect=dialect)),
                "nullable": col.nullable,
                "pk": col.primary_key,
                "unique": [col.name] in unique_sets,
                "foreign_keys": [{"target": f.target_fullname, "ondelete": f.ondelete} for f in col.foreign_keys],
            })
        tables.append({"name": table.name, "columns": columns, "unique_sets": unique_sets,
                       "indexes": [{"name": i.name, "columns": list(i.columns.keys()), "unique": i.unique}
                                   for i in sorted(table.indexes, key=lambda i: i.name)]})
    source_path = ROOT / "backend/app/models/entities.py"
    result = {"source": "backend/app/models/entities.py", "source_sha256": hashlib.sha256(source_path.read_bytes()).hexdigest(),
              "release": "1.2.0", "date": "2026-08-31", "tables": tables}
    (DEST / "schema.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    lines = ["# Spendly v1.2.0 - complete data dictionary", "", "Generated from SQLAlchemy metadata. No database connection or mutation was performed.", "",
             "11 application tables. The Alembic migration bookkeeping table is not included.", "",
             "UUID identifiers are stored as VARCHAR(36), not as the native PostgreSQL UUID type. Timestamps are stored without a timezone; application code uses UTC. Defaults and API validation are defined in the application, not inferred from this diagram.", ""]
    for table in tables:
        lines += ["## " + table["name"], "", "| Column | PostgreSQL type | Key | Nullable | Reference / delete action |",
                  "| --- | --- | --- | --- | --- |"]
        for c in table["columns"]:
            key = ", ".join(k for k, yes in [("PK", c["pk"]), ("FK", bool(c["foreign_keys"])), ("UQ", c["unique"])] if yes)
            refs = "; ".join(f["target"] + " / " + str(f["ondelete"]) for f in c["foreign_keys"])
            lines.append(f"| {c['name']} | {c['type']} | {key} | {'Yes' if c['nullable'] else 'No'} | {refs} |")
        lines += [""]
        for keys in table["unique_sets"]:
            lines += ["- Unique: (" + ", ".join(keys) + ")"]
        for idx in table["indexes"]:
            lines += [f"- Index `{idx['name']}`: ({', '.join(idx['columns'])})" + ("; unique" if idx["unique"] else "")]
        lines += [""]
    lines += ["## Important implementation boundaries", "",
              "- Admin credentials are configured outside the users table. There is no database admin role column.",
              "- Model version strings on results are not foreign keys to model_versions.",
              "- admin_audit.target_id is deliberately not a foreign key, so an audit record can survive deletion of its target.",
              "- system_settings currently stores the analysis_enabled switch.",
              "- categories and recurring flags are transaction attributes, not separate category or schedule tables.",
              "- A run can have zero or one forecast at database level; a successfully completed analysis normally creates one.", ""]
    (DEST.parent / "Database_Data_Dictionary.md").write_text("\n".join(lines), encoding="utf-8")
    ddl = ["-- Documentation only: compiled from the ORM. Do not use instead of Alembic migrations.", "-- This file was not executed against a database."]
    for table in db.metadata.sorted_tables:
        ddl.append(str(CreateTable(table).compile(dialect=dialect)).strip() + ";")
        ddl.extend(str(CreateIndex(i).compile(dialect=dialect)).strip() + ";" for i in sorted(table.indexes, key=lambda i: i.name))
    (DEST / "schema_reference.sql").write_text("\n\n".join(ddl) + "\n", encoding="utf-8")
    print(f"Exported {len(tables)} tables, {sum(len(t['columns']) for t in tables)} columns and "
          f"{sum(len(c['foreign_keys']) for t in tables for c in t['columns'])} foreign keys.")


if __name__ == "__main__":
    main()
