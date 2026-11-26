"""Lapisan akses data. Semua pemanggilan ke DynamoDB dikumpulkan di file ini."""

import uuid
from datetime import datetime, timezone
from decimal import Decimal
from functools import lru_cache
from typing import Optional

import boto3
from botocore.exceptions import BotoCoreError, ClientError

from . import config


class StorageError(Exception):
    """Dilempar saat DynamoDB tidak bisa diakses atau mengembalikan error tak terduga."""


@lru_cache(maxsize=1)
def _dynamodb():
    return boto3.resource("dynamodb")


def reset_cache() -> None:
    """Dipakai oleh test agar resource boto3 dibuat ulang."""
    _dynamodb.cache_clear()


def _table():
    return _dynamodb().Table(config.table_name())


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _clean(item: dict) -> dict:
    """boto3 mengembalikan angka sebagai Decimal. Ubah ke int supaya bisa jadi JSON."""
    result = {}
    for key, value in item.items():
        if isinstance(value, Decimal):
            result[key] = int(value) if value == value.to_integral_value() else float(value)
        else:
            result[key] = value
    return result


def _is_condition_failed(error: ClientError) -> bool:
    return error.response.get("Error", {}).get("Code") == "ConditionalCheckFailedException"


def ping() -> dict:
    """Cek koneksi ke DynamoDB dengan membaca metadata tabel."""
    try:
        description = _dynamodb().meta.client.describe_table(TableName=config.table_name())
    except (ClientError, BotoCoreError) as error:
        raise StorageError(str(error)) from error
    table = description["Table"]
    return {"table": table["TableName"], "tableStatus": table["TableStatus"]}


def create_loan(data: dict) -> dict:
    now = now_iso()
    item = {
        **data,
        "loanId": str(uuid.uuid4()),
        "status": "BORROWED",
        "createdAt": now,
        "updatedAt": now,
    }
    # Field opsional yang kosong tidak perlu disimpan
    item = {key: value for key, value in item.items() if value is not None}
    try:
        _table().put_item(Item=item, ConditionExpression="attribute_not_exists(loanId)")
    except (ClientError, BotoCoreError) as error:
        raise StorageError(str(error)) from error
    return _clean(item)


def get_loan(loan_id: str) -> Optional[dict]:
    try:
        response = _table().get_item(Key={"loanId": loan_id})
    except (ClientError, BotoCoreError) as error:
        raise StorageError(str(error)) from error
    item = response.get("Item")
    return _clean(item) if item else None


def list_loans(status: Optional[str] = None) -> list:
    items = []
    kwargs = {}
    try:
        table = _table()
        while True:
            response = table.scan(**kwargs)
            items.extend(response.get("Items", []))
            last_key = response.get("LastEvaluatedKey")
            if not last_key:
                break
            kwargs["ExclusiveStartKey"] = last_key
    except (ClientError, BotoCoreError) as error:
        raise StorageError(str(error)) from error
    cleaned = [_clean(item) for item in items]
    if status:
        cleaned = [item for item in cleaned if item.get("status") == status]
    cleaned.sort(key=lambda item: item.get("createdAt", ""), reverse=True)
    return cleaned


def update_loan(loan_id: str, changes: dict) -> Optional[dict]:
    """Ubah sebagian field. Nilai None berarti field tersebut dihapus dari item."""
    changes = {**changes, "updatedAt": now_iso()}

    set_parts, remove_parts = [], []
    names, values = {}, {}
    for index, (key, value) in enumerate(changes.items()):
        # Pakai placeholder karena beberapa nama (misalnya status) adalah reserved word di DynamoDB
        names[f"#f{index}"] = key
        if value is None:
            remove_parts.append(f"#f{index}")
        else:
            values[f":v{index}"] = value
            set_parts.append(f"#f{index} = :v{index}")

    expression = ""
    if set_parts:
        expression += "SET " + ", ".join(set_parts)
    if remove_parts:
        expression += " REMOVE " + ", ".join(remove_parts)

    kwargs = {
        "Key": {"loanId": loan_id},
        "UpdateExpression": expression.strip(),
        "ConditionExpression": "attribute_exists(loanId)",
        "ExpressionAttributeNames": names,
        "ReturnValues": "ALL_NEW",
    }
    if values:
        kwargs["ExpressionAttributeValues"] = values

    try:
        response = _table().update_item(**kwargs)
    except ClientError as error:
        if _is_condition_failed(error):
            return None
        raise StorageError(str(error)) from error
    except BotoCoreError as error:
        raise StorageError(str(error)) from error
    return _clean(response["Attributes"])


def delete_loan(loan_id: str) -> bool:
    try:
        _table().delete_item(
            Key={"loanId": loan_id},
            ConditionExpression="attribute_exists(loanId)",
        )
    except ClientError as error:
        if _is_condition_failed(error):
            return False
        raise StorageError(str(error)) from error
    except BotoCoreError as error:
        raise StorageError(str(error)) from error
    return True
