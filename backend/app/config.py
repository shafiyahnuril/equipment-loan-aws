"""Konfigurasi aplikasi. Semua nilai dibaca dari environment variable."""

import os


def storage_backend() -> str:
    """Pilihan penyimpanan data: "dynamodb" (default) atau "s3" (cadangan)."""
    return os.environ.get("STORAGE_BACKEND", "dynamodb").strip().lower()


def table_name() -> str:
    """Nama tabel DynamoDB. Di Lambda nilainya diatur lewat environment variable TABLE_NAME."""
    return os.environ.get("TABLE_NAME", "EquipmentLoans")


def data_bucket() -> str:
    """Nama bucket S3 untuk menyimpan data jika STORAGE_BACKEND=s3."""
    return os.environ.get("DATA_BUCKET", "")
