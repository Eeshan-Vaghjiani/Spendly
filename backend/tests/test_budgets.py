from __future__ import annotations


def test_create_list_update_and_delete_budget(client, auth) -> None:
    payload = {
        "period_start": "2026-03-02",
        "period_end": "2026-03-08",
        "category": "total",
        "amount": 10_000,
    }
    created = client.post("/api/v1/budgets", json=payload, headers=auth)
    assert created.status_code == 201, created.get_json()
    budget = created.get_json()["data"]
    listed = client.get("/api/v1/budgets", headers=auth)
    assert listed.status_code == 200
    assert len(listed.get_json()["data"]) == 1
    payload["amount"] = 12_000
    updated = client.put(
        f"/api/v1/budgets/{budget['id']}", json=payload, headers=auth
    )
    assert updated.status_code == 200
    assert updated.get_json()["data"]["amount"] == 12_000
    deleted = client.delete(
        f"/api/v1/budgets/{budget['id']}", headers=auth
    )
    assert deleted.status_code == 200
    assert client.get("/api/v1/budgets", headers=auth).get_json()["data"] == []


def test_budget_date_validation(client, auth) -> None:
    response = client.post(
        "/api/v1/budgets",
        json={
            "period_start": "2026-03-08",
            "period_end": "2026-03-02",
            "category": "total",
            "amount": 10_000,
        },
        headers=auth,
    )
    assert response.status_code == 422
    assert response.get_json()["error"]["code"] == "VALIDATION_ERROR"
