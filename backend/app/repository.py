"""Pintu masuk ke penyimpanan data.

Backend dipilih lewat environment variable STORAGE_BACKEND. Nilai default adalah
"dynamodb". Nilai "s3" dipakai sebagai cadangan jika DynamoDB tidak tersedia.
"""

from typing import Optional

from . import config, repository_dynamodb, repository_s3
from .errors import StorageError  # noqa: F401  (diekspor untuk modul lain)


def _impl():
    return repository_s3 if config.storage_backend() == "s3" else repository_dynamodb


def reset_cache() -> None:
    """Dipakai oleh test agar client boto3 dibuat ulang."""
    repository_dynamodb.reset_cache()
    repository_s3.reset_cache()


def now_iso() -> str:
    return _impl().now_iso()


def ping() -> dict:
    return _impl().ping()


def create_loan(data: dict) -> dict:
    return _impl().create_loan(data)


def get_loan(loan_id: str) -> Optional[dict]:
    return _impl().get_loan(loan_id)


def list_loans(status: Optional[str] = None) -> list:
    return _impl().list_loans(status)


def update_loan(loan_id: str, changes: dict) -> Optional[dict]:
    return _impl().update_loan(loan_id, changes)


def delete_loan(loan_id: str) -> bool:
    return _impl().delete_loan(loan_id)
