# Backup dan Restore Sandbox

Sandbox AWS Academy menghapus semua resource saat sesi habis. Dua script ini menyimpan progres dan menghidupkan kembali backend Jalur D (bucket data S3, Lambda, dan Function URL) pada Start Lab berikutnya.

Semua pengaturan ada di `scripts/sandbox_config.json` (tanpa rahasia). Semua perintah dijalankan dari root repo. Hasil backup disimpan di `.local/`, yang tidak masuk Git. Data peminjaman berisi nama dan NIM, jadi jangan dibagikan.

## Sebelum sesi habis

```
python scripts/sandbox_backup.py
```

Script hanya membaca dari AWS. Hasilnya adalah snapshot di `.local/snapshot/`, data peminjaman di `.local/backup/data/`, dan zip Lambda di `.local/backup/`.

## Pada Start Lab berikutnya

1. Tekan Start Lab, buka AWS Details, lalu salin blok kredensial AWS CLI ke `~/.aws/credentials` (di luar repo). Pastikan `~/.aws/config` berisi `region = us-east-1`.
2. Cek rencana tanpa mengubah apa pun:

```
python scripts/sandbox_restore.py --dry-run
```

3. Jalankan restore dan pulihkan data lama:

```
python scripts/sandbox_restore.py --restore-data
```

Atau, kalau tidak ingin memulihkan data lama, isi data contoh:

```
python scripts/sandbox_restore.py --seed
```

Opsi `--restore-data` dan `--seed` tidak boleh dipakai bersamaan. Opsi `--frontend` membangun dan mengunggah website, tetapi jalur ini belum pernah dicoba.

4. Hasil akhirnya Function URL baru, ditulis juga ke `.local/last_deploy.json`.

## Setelah restore

Function URL pasti berbeda setiap Start Lab. Perbarui hal berikut:

- `frontend/.env.production` (jika frontend dipakai), lalu build ulang.
- Dokumen atau catatan yang menyebut URL lama.
- `corsOrigins` di `sandbox_config.json` jika URL website berubah.

## Catatan

- Script aman dijalankan berulang. Resource yang sudah ada tidak dibuat ulang atau dihapus.
- Jika kredensial kedaluwarsa, script berhenti dengan pesan yang jelas. Salin ulang kredensial lalu ulangi.
- Script tidak pernah mencetak atau menyimpan kredensial, tidak membuat IAM role, dan hanya memakai us-east-1.
