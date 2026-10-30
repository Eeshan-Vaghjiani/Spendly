"""Synthetic normalized events only. No SMS, hosted services or real inference."""
from decimal import Decimal

import pytest
from sqlalchemy import func, select

from backend.app.extensions import db
from backend.app.models import MpesaComponent, MpesaEvent, Transaction, User
from backend.tests.conftest import register

PREFIX = "/api/v1"


def event(reference="TEST000001", **changes):
    return {"external_reference": reference, "kind": "sent", "parser_version": "mpesa-v1",
            "transaction_timestamp": "2026-10-01T13:10:00Z", "amount": "214.25",
            "transaction_cost": "8.50", "transaction_type": "expense", "category": "transfers",
            "merchant": "Fictional recipient", **changes}


def reversal(reference="REVR000001", original="TEST000001", **changes):
    return {"external_reference": reference, "original_reference": original, "kind": "reversal",
            "parser_version": "mpesa-v1", "transaction_timestamp": "2026-10-02T13:00:00Z",
            "amount": "214.25", "original_transaction_type": "expense", "fee_refund_amount": "0.00", **changes}


def enable(client, auth):
    return client.put(PREFIX + "/mpesa/settings", headers=auth, json={
        "enabled": True, "disclosure_accepted": True, "consent_version": "2026-10-22"})


def submit(client, auth, *events):
    return client.post(PREFIX + "/transactions/mpesa/import", headers=auth, json={"events": list(events)})


@pytest.fixture(autouse=True)
def sms_capability(app):
    app.config["MPESA_SMS_ENABLED"] = True


def test_defaults_separate_disclosure_and_server_gate(client, auth, app):
    data = client.get(PREFIX + "/mpesa/settings", headers=auth).json["data"]
    assert data["enabled"] is False and data["consented_at"] is None
    assert submit(client, auth, event()).status_code == 403
    assert client.put(PREFIX + "/mpesa/settings", headers=auth, json={"enabled": True}).status_code == 422
    app.config["MPESA_SMS_ENABLED"] = False
    assert enable(client, auth).status_code == 503
    assert submit(client, auth, event()).status_code == 503
    assert client.put(PREFIX + "/mpesa/settings", headers=auth, json={"enabled": False}).status_code == 200
    assert db.session.scalar(select(func.count(Transaction.id))) == 0


def test_exact_money_components_replay_and_metadata(client, auth):
    assert enable(client, auth).status_code == 200
    first = submit(client, auth, event()).json["data"]
    assert first["created"] == 2 and first["invalid"] == 0
    assert submit(client, auth, event()).json["data"]["duplicate"] == 1
    rows = list(db.session.scalars(select(Transaction).order_by(Transaction.amount)))
    assert [row.amount for row in rows] == [Decimal("8.50"), Decimal("214.25")]
    assert {row.source for row in rows} == {"mpesa_sms"}
    assert rows[0].category == "transaction_fees"
    assert db.session.scalar(select(func.count(MpesaComponent.id))) == 2
    assert rows[1].to_dict()["source"] == "mpesa_sms"


def test_source_identity_survives_edit_and_delete(client, auth):
    enable(client, auth)
    submit(client, auth, event())
    principal = db.session.scalar(select(Transaction).where(Transaction.category == "transfers"))
    payload = principal.to_dict()
    for key in ("id", "currency", "source", "is_reversed"):
        payload.pop(key)
    payload.update(amount=333.33, category="other")
    assert client.put(PREFIX + f"/transactions/{principal.id}", headers=auth, json=payload).status_code == 200
    assert submit(client, auth, event()).json["data"]["duplicate"] == 1
    assert client.delete(PREFIX + f"/transactions/{principal.id}", headers=auth).status_code == 200
    db.session.expire_all()
    assert db.session.scalar(select(MpesaComponent).where(MpesaComponent.component == "principal")).transaction_id is None
    assert submit(client, auth, event()).json["data"]["duplicate"] == 1
    assert db.session.scalar(select(func.count(Transaction.id))) == 1


def test_equivalent_decimal_and_offset_timestamp_are_one_event(client, auth):
    enable(client, auth)
    submit(client, auth, event(amount="214.2", transaction_cost="8.5"))
    result = submit(client, auth, event(amount="214.20", transaction_cost="8.50",
        transaction_timestamp="2026-10-01T16:10:00+03:00")).json["data"]
    assert result["duplicate"] == 1 and result["invalid"] == 0
    assert db.session.scalar(select(func.count(Transaction.id))) == 2


def test_existing_alert_review_signatures_survive_non_reversed_migration(client, auth):
    import hashlib
    from backend.app.services.alert_review import review_version, review_state
    enable(client, auth)
    submit(client, auth, event())
    transaction = db.session.scalar(select(Transaction).where(Transaction.category == "transfers"))
    legacy = hashlib.sha256((transaction.fingerprint + "|False").encode()).hexdigest()
    assert review_version(transaction) == legacy
    transaction.is_reversed = True
    assert review_version(transaction) != legacy
    assert review_state(transaction) == "transaction_reversed"


@pytest.mark.parametrize("pending_first", [False, True])
def test_reversal_chains_are_reviewed_without_mutating_target(client, auth, pending_first):
    enable(client, auth)
    target = reversal()
    chain = reversal(reference="REVR000002", original="REVR000001")
    for item in ([chain, target] if pending_first else [target, chain]):
        submit(client, auth, item)
    rows = {row.external_reference: row for row in db.session.scalars(select(MpesaEvent))}
    assert rows["REVR000001"].status == "pending_reversal"
    assert rows["REVR000002"].status == "needs_review"
    submit(client, auth, event())
    db.session.expire_all()
    assert rows["REVR000001"].status == "reconciled"
    assert rows["REVR000002"].status == "needs_review"


def test_admin_deletion_detaches_source_and_replay_does_not_resurrect(client, auth):
    from backend.tests.test_admin_management import sign_in, body
    enable(client, auth)
    submit(client, auth, event())
    principal = db.session.scalar(select(Transaction).where(Transaction.category == "transfers"))
    response = client.delete(PREFIX + f"/admin/users/{principal.user_id}/records/transactions/{principal.id}",
        headers=sign_in(client), json=body(confirm_id=principal.id))
    assert response.status_code == 200
    db.session.expire_all()
    assert db.session.scalar(select(MpesaComponent).where(MpesaComponent.component == "principal")).transaction_id is None
    assert submit(client, auth, event()).json["data"]["duplicate"] == 1


def test_retention_detaches_components_but_keeps_deduplication_audit(app, client, auth, monkeypatch):
    from datetime import datetime
    from backend.app import retention
    app.config["DATA_RETENTION_DAYS"] = 1
    monkeypatch.setattr(retention, "_utc_now", lambda: datetime(2026, 10, 22))
    enable(client, auth)
    submit(client, auth, event())
    runner = app.test_cli_runner()
    assert runner.invoke(args=["purge-retained-data"]).exit_code == 0
    assert db.session.scalar(select(func.count(Transaction.id))) == 2
    result = runner.invoke(args=["purge-retained-data", "--apply"])
    assert result.exit_code == 0
    db.session.expire_all()
    assert db.session.scalar(select(func.count(Transaction.id))) == 0
    assert all(row.transaction_id is None for row in db.session.scalars(select(MpesaComponent)))
    assert submit(client, auth, event()).json["data"]["duplicate"] == 1


def test_authorized_export_and_account_deletion_include_source_audit(client, auth):
    from backend.tests.test_admin_management import sign_in, body
    enable(client, auth)
    submit(client, auth, event())
    user = db.session.scalar(select(User))
    user_id, username = user.id, user.username
    headers = sign_in(client)
    base = PREFIX + f"/admin/users/{user_id}"
    exported = client.post(base + "/export", headers=headers, json=body())
    assert exported.status_code == 200
    payload = exported.json
    assert len(payload["mpesa_events"]) == 1 and len(payload["mpesa_components"]) == 2
    assert payload["user"]["mpesa_sms_import_enabled"] is True
    assert "raw_sms" not in exported.text and "balance_after" not in exported.text
    assert client.patch(base, headers=headers, json=body(is_active=False)).status_code == 200
    assert client.delete(base, headers=headers, json=body(confirm_username=username)).status_code == 200
    assert db.session.scalar(select(func.count(MpesaEvent.id))) == 0
    assert db.session.scalar(select(func.count(MpesaComponent.id))) == 0
    assert db.session.scalar(select(func.count(Transaction.id))) == 0


def test_reversal_excluded_from_cashflow_budget_actuals_and_inference(client, auth, app, monkeypatch):
    from datetime import date
    from backend.app.repositories import TransactionRepository
    from backend.app.services.feature_preparation import FeaturePreparationService
    from backend.tests.test_admin_management import sign_in
    enable(client, auth)
    submit(client, auth, event(), reversal())
    user = db.session.scalar(select(User))
    assert TransactionRepository.expense_total(user.id, date(2026, 10, 1), date(2026, 10, 2)) == (8.5, 1)
    budget = client.post(PREFIX + "/budgets", headers=auth, json={"period_start": "2026-10-01",
        "period_end": "2026-10-31", "category": "total", "amount": 100})
    assert budget.status_code == 201
    cash = client.get(PREFIX + "/analytics/cashflow?resolution=yearly", headers=auth).json["data"]
    assert cash["summary"]["expense"] == 8.5 and cash["summary"]["cash_balance"] == -8.5
    dashboard = client.get(PREFIX + "/analytics/dashboard?period=all_time", headers=auth).json["data"]
    assert dashboard["expense"] == 8.5
    admin = client.get(PREFIX + f"/admin/users/{user.id}", headers=sign_in(client)).json["data"]
    assert admin["expense"] == 8.5
    seen = []
    original = FeaturePreparationService.forecasting
    def capture(self, account, transactions, budgets, **kwargs):
        seen.extend(transactions)
        return original(self, account, transactions, budgets, **kwargs)
    monkeypatch.setattr(FeaturePreparationService, "forecasting", capture)
    response = client.post(PREFIX + "/analysis/run", headers=auth, json={})
    assert response.status_code == 200
    assert len(seen) == 1 and seen[0].category == "transaction_fees"


def test_collision_distinguished_from_replay_and_financial_fingerprint(client, auth):
    enable(client, auth)
    submit(client, auth, event())
    assert submit(client, auth, event(amount="250.00")).json["data"]["results"][0]["code"] == "REFERENCE_CONFLICT"
    # Different source identity, identical financial fingerprint is flagged.
    result = submit(client, auth, event("TEST000002")).json["data"]
    assert result["needs_review"] == 1 and result["created"] == 0
    assert submit(client, auth, event("TEST000002")).json["data"]["duplicate"] == 1
    assert db.session.scalar(select(func.count(Transaction.id))) == 2


def test_partial_batch_does_not_echo_untrusted_fields_or_create_zero_fee(client, auth):
    enable(client, auth)
    result = submit(client, auth, event(raw_sms="fixture body must never persist"),
        event("TEST000002", kind="airtime", category="airtime_and_data", transaction_cost="0.00"),
        event("TEST000003", kind="received", transaction_type="income", category="other", transaction_cost="0.00")).json["data"]
    assert result["invalid"] == 1 and result["created"] == 2
    assert "fixture body" not in str(result)
    assert db.session.scalar(select(func.count(MpesaEvent.id))) == 2


@pytest.mark.parametrize("changes", [
    {"amount": 1.1}, {"amount": "NaN"}, {"amount": "0.001"}, {"amount": "0"},
    {"amount": "-2"}, {"amount": "1000000000000.00"}, {"transaction_timestamp": "2026-01-01T12:00:00"},
    {"external_reference": "bad"}, {"transaction_type": "income"}, {"user_id": "another"},
    {"merchant": "x" * 121}, {"balance_after": "1000.00"}, {"kind": []},
])
def test_malformed_normalized_events_are_rejected(client, auth, changes):
    enable(client, auth)
    assert submit(client, auth, event(**changes)).json["data"]["invalid"] == 1
    assert db.session.scalar(select(func.count(Transaction.id))) == 0


@pytest.mark.parametrize("before", [False, True])
def test_reversal_order_and_totals_preserve_fee_and_history(client, auth, before):
    enable(client, auth)
    events = [reversal(), event()] if before else [event(), reversal()]
    for item in events:
        assert submit(client, auth, item).json["data"]["invalid"] == 0
    assert submit(client, auth, reversal()).json["data"]["duplicate"] == 1
    rows = list(db.session.scalars(select(Transaction)))
    assert len(rows) == 2
    assert next(row for row in rows if row.category == "transfers").is_reversed
    assert not next(row for row in rows if row.category == "transaction_fees").is_reversed
    data = client.get(PREFIX + "/analytics/dashboard?period=all_time", headers=auth).json["data"]
    assert data["expense"] == 8.50
    from backend.app.repositories import TransactionRepository
    assert len(TransactionRepository.chronological(rows[0].user_id)) == 1
    assert client.get(PREFIX + "/transactions", headers=auth).json["data"]["total"] == 2


@pytest.mark.parametrize("changes", [
    {"amount": "10.00"}, {"original_transaction_type": "income"}, {"fee_refund_amount": "1.00"}])
def test_ambiguous_or_partial_reversal_requires_review(client, auth, changes):
    enable(client, auth)
    submit(client, auth, event())
    assert submit(client, auth, reversal(**changes)).json["data"]["needs_review"] == 1
    assert not any(row.is_reversed for row in db.session.scalars(select(Transaction)))


def test_full_fee_refund_and_account_ownership(client, auth):
    enable(client, auth)
    submit(client, auth, event(), reversal(fee_refund_amount="8.50"))
    assert all(row.is_reversed for row in db.session.scalars(select(Transaction)))
    second = register(client, email="second-synthetic@example.invalid")
    other = {"Authorization": "Bearer " + second["access_token"]}
    assert submit(client, other, event()).status_code == 403
    enable(client, other)
    assert submit(client, other, event()).json["data"]["created"] == 2
    assert client.put(PREFIX + "/mpesa/settings", headers=auth, json={"enabled": False}).status_code == 200
    assert submit(client, auth, event("TEST000003")).status_code == 403
    assert submit(client, other, event()).json["data"]["duplicate"] == 1


def test_requires_jwt_and_rejects_unknown_batch_fields(client, auth):
    assert submit(client, {}, event()).status_code == 401
    enable(client, auth)
    assert client.post(PREFIX + "/transactions/mpesa/import", headers=auth,
                       json={"events": [event()], "user_id": "another"}).status_code == 422


def test_storage_error_does_not_log_bound_financial_details(client, auth, monkeypatch, caplog):
    from sqlalchemy.exc import OperationalError
    from backend.app.routes import mpesa
    enable(client, auth)
    def fail(*args):
        raise OperationalError("fixture sql", {"merchant": "private-fixture-diagnostic"}, Exception("fixture"))
    monkeypatch.setattr(mpesa, "import_event", fail)
    response = submit(client, auth, event())
    assert response.status_code == 503
    assert "private-fixture-diagnostic" not in response.get_data(as_text=True) + caplog.text


def test_pending_wrong_reversal_is_reported_when_original_arrives(client, auth):
    enable(client, auth)
    submit(client, auth, reversal(amount="1.00"))
    result = submit(client, auth, event()).json["data"]
    assert result["created"] == 2 and result["needs_review"] == 1
    assert not any(row.is_reversed for row in db.session.scalars(select(Transaction)))


def test_migration_roundtrip_preserves_existing_data_and_defaults(tmp_path):
    from backend.app import create_app
    from flask_migrate import downgrade, upgrade
    from sqlalchemy import inspect, text
    from alembic.autogenerate import compare_metadata
    from alembic.migration import MigrationContext
    application = create_app({"TESTING": True, "LOAD_MODELS": False,
        "SECRET_KEY": "sms-migration-fixture-only-32-bytes", "JWT_SECRET_KEY": "sms-migration-jwt-fixture-32-bytes",
        "SQLALCHEMY_DATABASE_URI": "sqlite:///" + str(tmp_path / "sms-migration.db")})
    with application.app_context():
        upgrade(directory="backend/migrations", revision="0007_sign_in_activity")
        db.session.execute(text("INSERT INTO users (id,email,display_name,username,username_normalized,created_at,is_active,model_training_opt_in) VALUES ('legacy-sms','legacy-sms@example.invalid','Legacy','legacy_sms','legacy_sms',CURRENT_TIMESTAMP,1,0)"))
        db.session.commit()
        upgrade(directory="backend/migrations")
        user = db.session.get(User, "legacy-sms")
        assert user.mpesa_sms_import_enabled is False and user.mpesa_sms_consented_at is None
        with db.engine.connect() as connection:
            assert compare_metadata(MigrationContext.configure(connection), db.metadata) == []
        db.session.remove()
        downgrade(directory="backend/migrations", revision="0007_sign_in_activity")
        assert "mpesa_events" not in inspect(db.engine).get_table_names()
        assert db.session.scalar(text("SELECT COUNT(*) FROM users WHERE id='legacy-sms'")) == 1
        db.session.commit()
        upgrade(directory="backend/migrations")
        assert db.session.get(User, "legacy-sms").mpesa_sms_import_enabled is False


def test_concurrent_requests_keep_one_source_event_and_component_pair(tmp_path):
    from concurrent.futures import ThreadPoolExecutor
    from backend.app import create_app
    application = create_app({"TESTING": True, "LOAD_MODELS": False, "MPESA_SMS_ENABLED": True,
        "SECRET_KEY": "sms-concurrent-fixture-only-32-bytes", "JWT_SECRET_KEY": "sms-concurrent-jwt-fixture-32-bytes",
        "SQLALCHEMY_DATABASE_URI": "sqlite:///" + str(tmp_path / "sms-race.db"),
        "SQLALCHEMY_ENGINE_OPTIONS": {"connect_args": {"check_same_thread": False, "timeout": 10}}})
    with application.app_context():
        db.create_all()
        with application.test_client() as test_client:
            account = register(test_client, email="sms-race@example.invalid")
            headers = {"Authorization": "Bearer " + account["access_token"]}
            enable(test_client, headers)
        def request_once(_):
            with application.test_client() as worker:
                return submit(worker, headers, event()).status_code
        with ThreadPoolExecutor(max_workers=4) as workers:
            results = list(workers.map(request_once, range(4)))
        assert all(code in (200, 503) for code in results)
        # A retry after any transient SQLite writer contention is also idempotent.
        with application.test_client() as test_client:
            assert submit(test_client, headers, event()).status_code == 200
        assert db.session.scalar(select(func.count(MpesaEvent.id))) == 1
        assert db.session.scalar(select(func.count(Transaction.id))) == 2
        assert db.session.scalar(select(func.count(MpesaComponent.id))) == 2


@pytest.mark.parametrize("disable_first", [False, True])
def test_consent_disable_and_import_have_a_serial_write_boundary(tmp_path, monkeypatch, disable_first):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Event
    from flask import request
    from backend.app import create_app
    from backend.app.routes import mpesa
    application = create_app({"TESTING": True, "LOAD_MODELS": False, "MPESA_SMS_ENABLED": True,
        "SECRET_KEY": "sms-disable-race-fixture-only-32-bytes", "JWT_SECRET_KEY": "sms-disable-race-jwt-fixture-32-bytes",
        "SQLALCHEMY_DATABASE_URI": "sqlite:///" + str(tmp_path / "sms-disable-race.db"),
        "SQLALCHEMY_ENGINE_OPTIONS": {"connect_args": {"check_same_thread": False, "timeout": 10}}})
    with application.app_context():
        db.create_all()
        with application.test_client() as setup:
            account = register(setup, email="sms-disable-race@example.invalid")
            headers = {"Authorization": "Bearer " + account["access_token"]}
            enable(setup, headers)
        acquired, release, second_started = Event(), Event(), Event()
        original = mpesa.locked_user
        first_method = "PUT" if disable_first else "POST"
        def locked():
            if request.method != first_method:
                second_started.set()
            user = original()
            if request.method == first_method:
                acquired.set()
                assert release.wait(5), "Test failed to release first writer"
            return user
        monkeypatch.setattr(mpesa, "locked_user", locked)
        def disable():
            with application.test_client() as worker:
                return worker.put(PREFIX + "/mpesa/settings", headers=headers, json={"enabled": False}).status_code
        def importing():
            with application.test_client() as worker:
                return submit(worker, headers, event()).status_code
        with ThreadPoolExecutor(max_workers=2) as pool:
            first = pool.submit(disable if disable_first else importing)
            assert acquired.wait(5)
            second = pool.submit(importing if disable_first else disable)
            assert second_started.wait(5)
            assert not second.done()
            release.set()
            assert first.result(timeout=10) == 200
            assert second.result(timeout=10) == (403 if disable_first else 200)
        with application.test_client() as worker:
            assert submit(worker, headers, event("TEST000009")).status_code == 403
        db.session.expire_all()
        assert db.session.scalar(select(func.count(Transaction.id))) == (0 if disable_first else 2)
