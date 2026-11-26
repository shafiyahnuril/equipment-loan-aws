"""Penyimpanan data di S3 (backend cadangan).

Dipakai hanya jika DynamoDB tidak tersedia di akun AWS. Setiap peminjaman disimpan
sebagai satu file JSON dengan key loans/<loanId>.json di bucket DATA_BUCKET.
"""

import json
import uuid
from datetime import datetime, timezone
from functools import lru_cache
from typing import Optional

import boto3
from botocore.exceptions import BotoCoreError, ClientError

from . import config
from .errors import StorageError

PREFIX = "loans/"
_NOT_FOUND = {"NoSuchKey", "404", "NotFound"}


@lru_cache(maxsize=1)
def _s3():
    return boto3.client("s3")


def reset_cache() -> None:
    _s3.cache_clear()


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _key(loan_id: str) -> str:
    return f"{PREFIX}{loan_id}.json"


def _bucket() -> str:
    name = config.data_bucket()
    if not name:
        raise StorageError("Environment variable DATA_BUCKET belum diisi")
    return name


def _code(error: ClientError) -> str:
    return str(error.response.get("Error", {}).get("Code", ""))


def _read(loan_id: str) -> Optional[dict]:
    try:
        response = _s3().get_object(Bucket=_bucket(), Key=_key(loan_id))
    except ClientError as error:
        if _code(error) in _NOT_FOUND:
            return None
        raise StorageError(str(error)) from error
    except BotoCoreError as error:
        raise StorageError(str(error)) from error
    return json.loads(response["Body"].read())


def _write(item: dict) -> None:
    try:
        _s3().put_object(
            Bucket=_bucket(),
            Key=_key(item["loanId"]),
            Body=json.dumps(item).encode("utf-8"),
            ContentType="application/json",
        )
    except (ClientError, BotoCoreError) as error:
        raise StorageError(str(error)) from error


def ping() -> dict:
    try:
        _s3().head_bucket(Bucket=_bucket())
    except (ClientError, BotoCoreError) as error:
        raise StorageError(str(error)) from error
    return {"storage": "s3", "bucket": _bucket()}


def create_loan(data: dict) -> dict:
    now = now_iso()
    item = {
        **data,
        "loanId": str(uuid.uuid4()),
        "status": "BORROWED",
        "createdAt": now,
        "updatedAt": now,
    }
    item = {key: value for key, value in item.items() if value is not None}
    _write(item)
    return item


def get_loan(loan_id: str) -> Optional[dict]:
    return _read(loan_id)


def list_loans(status: Optional[str] = None) -> list:
    items = []
    try:
        paginator = _s3().get_paginator("list_objects_v2")
        for page in paginator.paginate(Bucket=_bucket(), Prefix=PREFIX):
            for obj in page.get("Contents", []):
                loan_id = obj["Key"][len(PREFIX) : -len(".json")]
                item = _read(loan_id)
                if item is not None:
                    items.append(item)
    except (ClientError, BotoCoreError) as error:
        raise StorageError(str(error)) from error
    if status:
        items = [item for item in items if item.get("status") == status]
    items.sort(key=lambda item: item.get("createdAt", ""), reverse=True)
    return items


def update_loan(loan_id: str, changes: dict) -> Optional[dict]:
    """Ubah sebagian field. Nilai None berarti field tersebut dihapus dari item."""
    item = _read(loan_id)
    if item is None:
        return None
    for key, value in {**changes, "updatedAt": now_iso()}.items():
        if value is None:
            item.pop(key, None)
        else:
            item[key] = value
    _write(item)
    return item


def delete_loan(loan_id: str) -> bool:
    if _read(loan_id) is None:
        return False
    try:
        _s3().delete_object(Bucket=_bucket(), Key=_key(loan_id))
    except (ClientError, BotoCoreError) as error:
        raise StorageError(str(error)) from error
    return True
