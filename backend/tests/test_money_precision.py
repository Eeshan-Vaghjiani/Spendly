"""Public write paths must not silently round invalid money or overflow SQL cents."""
import io

import pytest

from .test_transactions import TRANSACTION


BUDGET = {
    "period_start": "2026-10-01",
    "period_end": "2026-10-31",
    "category": "food",
    "amount": 100,
}


@pytest.mark.parametrize("amount", [0.001, 1.001, 1e12])
@pytest.mark.parametrize("resource,payload", [("transactions", TRANSACTION), ("budgets", BUDGET)])
def test_invalid_money_never_creates_or_changes_records(client, auth, amount, resource, payload):
    created = client.post(f"/api/v1/{resource}", headers=auth, json=payload)
    assert created.status_code == 201
    original = created.get_json()["data"]
    invalid = {**payload, "amount": amount}
    for method, path in [
        (client.post, f"/api/v1/{resource}"),
        (client.put, f"/api/v1/{resource}/{original['id']}"),
    ]:
        response = method(path, headers=auth, json=invalid)
        assert response.status_code == 422, response.get_json()
        assert "amount" in response.get_json()["error"]["details"]
    listing = client.get(f"/api/v1/{resource}", headers=auth).get_json()["data"]
    items = listing["items"] if resource == "transactions" else listing
    assert len(items) == 1
    assert items[0]["amount"] == original["amount"]


def test_csv_money_errors_keep_existing_partial_import_contract(client, auth):
    rows = ["transaction_timestamp,amount,category,transaction_type,merchant,is_recurring"]
    for day, amount in enumerate(["0.001", "1.001", "1000000000000", "0.01", "123.45"], 1):
        rows.append(f"2026-10-{day:02d}T08:00:00Z,{amount},food,expense,Synthetic,false")
    response = client.post(
        "/api/v1/transactions/upload",
        headers={"Authorization": auth["Authorization"]},
        data={"file": (io.BytesIO("\n".join(rows).encode()), "synthetic.csv")},
    )
    assert response.status_code == 200
    result = response.get_json()["data"]
    assert result["created_rows"] == 2
    assert result["invalid_rows"] == 3
    assert [error["row"] for error in result["errors"]] == [2, 3, 4]
    items = client.get("/api/v1/transactions", headers=auth).get_json()["data"]["items"]
    assert sorted(item["amount"] for item in items) == [0.01, 123.45]


@pytest.mark.parametrize("amount", [0.01, 123.45, 999999999999.99])
def test_exact_cent_amounts_remain_valid(client, auth, amount):
    for resource, payload in [("transactions", TRANSACTION), ("budgets", BUDGET)]:
        response = client.post(f"/api/v1/{resource}", headers=auth, json={**payload, "amount": amount})
        assert response.status_code == 201, response.get_json()
        assert response.get_json()["data"]["amount"] == amount
