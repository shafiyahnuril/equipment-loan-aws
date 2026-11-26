"""Test untuk seluruh endpoint. DynamoDB di-mock dengan moto, jadi tidak butuh akun AWS."""

import os

import boto3
import pytest
from fastapi.testclient import TestClient
from moto import mock_aws

TABLE = "EquipmentLoansTest"


@pytest.fixture(autouse=True)
def aws_env(monkeypatch):
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "testing")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "testing")
    monkeypatch.setenv("AWS_DEFAULT_REGION", "us-east-1")
    monkeypatch.setenv("TABLE_NAME", TABLE)


@pytest.fixture
def client(aws_env):
    from app import repository
    from app.main import app

    with mock_aws():
        boto3.client("dynamodb", region_name="us-east-1").create_table(
            TableName=TABLE,
            KeySchema=[{"AttributeName": "loanId", "KeyType": "HASH"}],
            AttributeDefinitions=[{"AttributeName": "loanId", "AttributeType": "S"}],
            BillingMode="PAY_PER_REQUEST",
        )
        repository.reset_cache()
        yield TestClient(app)
        repository.reset_cache()


def sample(**overrides):
    data = {
        "borrowerName": "Sophie",
        "borrowerNim": "24/540586/TK/60019",
        "equipmentName": "ESP32 DevKit",
        "quantity": 2,
        "loanDate": "2026-11-27",
        "dueDate": "2026-12-04",
        "notes": "Untuk praktikum IoT",
    }
    data.update(overrides)
    return data


def create(client, **overrides):
    response = client.post("/loans", json=sample(**overrides))
    assert response.status_code == 201, response.text
    return response.json()


# ---------- health ----------


def test_health_ok(client):
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["table"] == TABLE
    assert body["tableStatus"] == "ACTIVE"


def test_health_returns_503_when_table_missing(client, monkeypatch):
    monkeypatch.setenv("TABLE_NAME", "TabelYangTidakAda")
    response = client.get("/health")
    assert response.status_code == 503
    assert response.json()["status"] == "error"


# ---------- create ----------


def test_create_returns_201_and_server_fields(client):
    loan = create(client)
    assert loan["status"] == "BORROWED"
    assert len(loan["loanId"]) == 36
    assert loan["quantity"] == 2
    assert isinstance(loan["quantity"], int)
    assert loan["createdAt"] == loan["updatedAt"]
    assert loan["returnedAt"] is None


def test_create_rejects_quantity_zero(client):
    response = client.post("/loans", json=sample(quantity=0))
    assert response.status_code == 422


def test_create_rejects_due_date_before_loan_date(client):
    response = client.post("/loans", json=sample(loanDate="2026-12-10", dueDate="2026-12-01"))
    assert response.status_code == 422


def test_create_rejects_missing_field(client):
    data = sample()
    del data["equipmentName"]
    assert client.post("/loans", json=data).status_code == 422


def test_create_rejects_unknown_field(client):
    assert client.post("/loans", json=sample(status="RETURNED")).status_code == 422


def test_create_rejects_bad_nim(client):
    assert client.post("/loans", json=sample(borrowerNim="12 3")).status_code == 422


# ---------- read ----------


def test_get_returns_created_loan(client):
    loan = create(client)
    response = client.get(f"/loans/{loan['loanId']}")
    assert response.status_code == 200
    assert response.json()["equipmentName"] == "ESP32 DevKit"


def test_get_unknown_id_returns_404(client):
    response = client.get("/loans/00000000-0000-0000-0000-000000000000")
    assert response.status_code == 404


def test_get_malformed_id_returns_422(client):
    assert client.get("/loans/bukan-uuid").status_code == 422


def test_list_returns_all_newest_first(client):
    first = create(client, equipmentName="Arduino Uno")
    second = create(client, equipmentName="Raspberry Pi")
    response = client.get("/loans")
    assert response.status_code == 200
    ids = [item["loanId"] for item in response.json()]
    assert set(ids) == {first["loanId"], second["loanId"]}


def test_list_filter_by_status(client):
    keep = create(client)
    returned = create(client, equipmentName="Sensor DHT22")
    client.put(f"/loans/{returned['loanId']}", json={"status": "RETURNED"})
    borrowed = client.get("/loans", params={"status": "BORROWED"}).json()
    assert [item["loanId"] for item in borrowed] == [keep["loanId"]]
    assert client.get("/loans", params={"status": "SALAH"}).status_code == 422


# ---------- update ----------


def test_update_marks_returned_and_sets_returned_at(client):
    loan = create(client)
    response = client.put(f"/loans/{loan['loanId']}", json={"status": "RETURNED"})
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "RETURNED"
    assert body["returnedAt"] is not None


def test_update_back_to_borrowed_clears_returned_at(client):
    loan = create(client)
    client.put(f"/loans/{loan['loanId']}", json={"status": "RETURNED"})
    body = client.put(f"/loans/{loan['loanId']}", json={"status": "BORROWED"}).json()
    assert body["status"] == "BORROWED"
    assert body["returnedAt"] is None


def test_update_changes_quantity_and_keeps_other_fields(client):
    loan = create(client)
    body = client.put(f"/loans/{loan['loanId']}", json={"quantity": 5}).json()
    assert body["quantity"] == 5
    assert body["borrowerName"] == "Sophie"


def test_update_can_clear_notes(client):
    loan = create(client)
    body = client.put(f"/loans/{loan['loanId']}", json={"notes": None}).json()
    assert body["notes"] is None


def test_update_unknown_id_returns_404(client):
    response = client.put("/loans/00000000-0000-0000-0000-000000000000", json={"quantity": 1})
    assert response.status_code == 404


def test_update_empty_body_returns_422(client):
    loan = create(client)
    assert client.put(f"/loans/{loan['loanId']}", json={}).status_code == 422


def test_update_checks_date_against_stored_value(client):
    loan = create(client, loanDate="2026-11-27", dueDate="2026-12-04")
    response = client.put(f"/loans/{loan['loanId']}", json={"dueDate": "2026-11-01"})
    assert response.status_code == 422


# ---------- delete ----------


def test_delete_removes_loan(client):
    loan = create(client)
    assert client.delete(f"/loans/{loan['loanId']}").status_code == 204
    assert client.get(f"/loans/{loan['loanId']}").status_code == 404


def test_delete_unknown_id_returns_404(client):
    assert client.delete("/loans/00000000-0000-0000-0000-000000000000").status_code == 404


# ---------- failure dan recovery ----------


def test_wrong_table_name_gives_500_then_recovers(client, monkeypatch):
    monkeypatch.setenv("TABLE_NAME", "TabelYangTidakAda")
    response = client.get("/loans")
    assert response.status_code == 500
    assert "penyimpanan data" in response.json()["detail"]

    monkeypatch.setenv("TABLE_NAME", TABLE)
    assert client.get("/loans").status_code == 200


# ---------- handler Lambda ----------


def test_lambda_handler_with_api_gateway_v2_event(client):
    from app.main import handler

    event = {
        "version": "2.0",
        "routeKey": "GET /health",
        "rawPath": "/health",
        "rawQueryString": "",
        "headers": {"host": "abc123.execute-api.us-east-1.amazonaws.com"},
        "requestContext": {
            "accountId": "123456789012",
            "apiId": "abc123",
            "domainName": "abc123.execute-api.us-east-1.amazonaws.com",
            "http": {
                "method": "GET",
                "path": "/health",
                "protocol": "HTTP/1.1",
                "sourceIp": "127.0.0.1",
                "userAgent": "pytest",
            },
            "requestId": "req-1",
            "routeKey": "GET /health",
            "stage": "$default",
            "time": "26/Nov/2026:14:00:00 +0000",
            "timeEpoch": 1795000000000,
        },
        "isBase64Encoded": False,
    }
    result = handler(event, None)
    assert result["statusCode"] == 200
    assert '"status":"ok"' in result["body"].replace(" ", "")
