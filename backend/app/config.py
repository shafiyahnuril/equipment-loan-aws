"""Konfigurasi aplikasi. Semua nilai dibaca dari environment variable."""

import os


def table_name() -> str:
    """Nama tabel DynamoDB. Di Lambda nilainya diatur lewat environment variable TABLE_NAME."""
    return os.environ.get("TABLE_NAME", "EquipmentLoans")
