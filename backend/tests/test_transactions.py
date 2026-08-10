from __future__ import annotations

import io

from .conftest import register


TRANSACTION = {
    "transaction_timestamp": "2026-01-05T08:30:00+03:00",
    "amount": 450.0,
    "category": "Dining",
    "transaction_type": "expense",
    "merchant": "Campus Cafe",
    "is_recurring": False,
}


def test_create_list_and_delete_transaction(client, auth) -> None:
    created = client.post(
        "/api/v1/transactions", json=TRANSACTION, headers=auth
    )
    assert created.status_code == 201, created.get_json()
    item = created.get_json()["data"]
    assert item["currency"] == "KES"
    assert item["category"] == "food"
    listed = client.get("/api/v1/transactions", headers=auth)
    assert listed.status_code == 200
    assert listed.get_json()["data"]["total"] == 1
    deleted = client.delete(
        f"/api/v1/transactions/{item['id']}", headers=auth
    )
    assert deleted.status_code == 200


def test_update_transaction_revalidates_and_persists_changes(client, auth) -> None:
    item = client.post(
        "/api/v1/transactions", json=TRANSACTION, headers=auth
    ).get_json()["data"]
    changed = {
        **TRANSACTION,
        "amount": 725.5,
        "category": "Transport",
        "merchant": "City Bus",
    }
    response = client.put(
        f"/api/v1/transactions/{item['id']}", json=changed, headers=auth
    )
    assert response.status_code == 200, response.get_json()
    assert response.get_json()["data"]["amount"] == 725.5
    assert response.get_json()["data"]["category"] == "transport"


def test_duplicate_transaction_is_rejected(client, auth) -> None:
    assert (
        client.post("/api/v1/transactions", json=TRANSACTION, headers=auth).status_code
        == 201
    )
    duplicate = client.post(
        "/api/v1/transactions", json=TRANSACTION, headers=auth
    )
    assert duplicate.status_code == 409
    assert duplicate.get_json()["error"]["code"] == "DUPLICATE_TRANSACTION"


def test_user_cannot_delete_another_users_transaction(client, auth) -> None:
    first = client.post(
        "/api/v1/transactions", json=TRANSACTION, headers=auth
    ).get_json()["data"]
    second = register(client, email="second@example.com", display_name="Second")
    second_headers = {
        "Authorization": f"Bearer {second['access_token']}"
    }
    response = client.delete(
        f"/api/v1/transactions/{first['id']}", headers=second_headers
    )
    assert response.status_code == 404


def test_csv_upload_reports_created_duplicate_and_invalid_rows(client, auth) -> None:
    csv_text = "\n".join(
        [
            "transaction_timestamp,amount,category,transaction_type,merchant,is_recurring",
            "2026-01-05T08:30:00Z,450,food,expense,Cafe,false",
            "2026-01-05T08:30:00Z,450,food,expense,Cafe,false",
            "2026-01-06T08:30:00Z,-5,transport,expense,Bus,false",
        ]
    )
    response = client.post(
        "/api/v1/transactions/upload",
        data={"file": (io.BytesIO(csv_text.encode()), "transactions.csv")},
        headers={"Authorization": auth["Authorization"]},
        content_type="multipart/form-data",
    )
    assert response.status_code == 200, response.get_json()
    summary = response.get_json()["data"]
    assert summary == {
        "received_rows": 3,
        "created_rows": 1,
        "duplicate_rows": 1,
        "invalid_rows": 1,
        "errors": summary["errors"],
    }
    assert summary["errors"][0]["row"] == 4


def test_csv_upload_rejects_missing_headers(client, auth) -> None:
    response = client.post(
        "/api/v1/transactions/upload",
        data={"file": (io.BytesIO(b"amount,category\n1,food"), "bad.csv")},
        headers={"Authorization": auth["Authorization"]},
        content_type="multipart/form-data",
    )
    assert response.status_code == 422
    assert response.get_json()["error"]["code"] == "INVALID_CSV_HEADERS"
