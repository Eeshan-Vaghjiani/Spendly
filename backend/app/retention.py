"""Explicit, configurable retention maintenance for financial records."""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

import click
from flask import Flask, current_app
from sqlalchemy import select

from .extensions import db
from .models import AnalysisRun, Budget, Transaction


def _utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def register_retention_command(app: Flask) -> None:
    @app.cli.command("purge-retained-data")
    @click.option(
        "--apply",
        is_flag=True,
        help="Commit the deletion. Without this flag the command is a dry run.",
    )
    def purge_retained_data(apply: bool) -> None:
        """Remove financial records older than DATA_RETENTION_DAYS."""

        retention_days = int(current_app.config["DATA_RETENTION_DAYS"])
        if retention_days <= 0:
            click.echo(
                "Retention purge is disabled because DATA_RETENTION_DAYS is 0."
            )
            return

        timestamp_cutoff = _utc_now() - timedelta(days=retention_days)
        date_cutoff = date.today() - timedelta(days=retention_days)
        records = {
            "analysis runs": list(
                db.session.scalars(
                    select(AnalysisRun).where(
                        AnalysisRun.generated_at < timestamp_cutoff
                    )
                )
            ),
            "transactions": list(
                db.session.scalars(
                    select(Transaction).where(
                        Transaction.transaction_timestamp < timestamp_cutoff
                    )
                )
            ),
            "budgets": list(
                db.session.scalars(
                    select(Budget).where(Budget.period_end < date_cutoff)
                )
            ),
        }
        summary = ", ".join(
            f"{len(items)} {label}" for label, items in records.items()
        )
        if not apply:
            click.echo(
                f"Dry run: would delete {summary}. Add --apply to commit."
            )
            return

        for items in records.values():
            for record in items:
                db.session.delete(record)
        db.session.commit()
        click.echo(f"Retention purge committed: deleted {summary}.")
