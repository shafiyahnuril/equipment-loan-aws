"""Error yang dipakai bersama oleh semua backend penyimpanan."""


class StorageError(Exception):
    """Dilempar saat penyimpanan data tidak bisa diakses atau mengembalikan error tak terduga."""
