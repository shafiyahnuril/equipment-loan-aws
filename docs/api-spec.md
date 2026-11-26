# Spesifikasi API

Base URL adalah Function URL dari Lambda (Jalur D), misalnya `https://abc123.lambda-url.us-east-1.on.aws`. Jika memakai API Gateway, base URL-nya Invoke URL, misalnya `https://abc123.execute-api.us-east-1.amazonaws.com`. Semua request dan response memakai format JSON.

Dokumentasi interaktif (Swagger UI) di `/docs` hanya terjangkau jika memakai API Gateway dan route `GET /docs` serta `GET /openapi.json` ditambahkan. Pada Function URL semua path diteruskan ke Lambda, tetapi `/docs` belum diuji di AWS.

## Ringkasan endpoint

| Operasi | Method dan path | Fungsi | Status sukses | Status gagal |
|---|---|---|---|---|
| Create | `POST /loans` | Mencatat peminjaman baru | 201 | 422 |
| Read (daftar) | `GET /loans` | Mengambil semua peminjaman, bisa difilter dengan `?status=` | 200 | 422 |
| Read (satu) | `GET /loans/{loanId}` | Mengambil satu peminjaman | 200 | 404 |
| Update | `PUT /loans/{loanId}` | Mengubah data atau menandai sudah dikembalikan | 200 | 404, 422 |
| Delete | `DELETE /loans/{loanId}` | Menghapus data peminjaman | 204 | 404 |
| Health | `GET /health` | Mengecek koneksi Lambda ke penyimpanan data (S3 atau DynamoDB) | 200 | 503 |

Seluruh endpoint bisa mengembalikan status 500 jika penyimpanan data tidak bisa diakses.

## Entity Loan

| Field | Tipe | Wajib saat create | Aturan |
|---|---|---|---|
| `loanId` | string (UUID) | tidak | Dibuat oleh server |
| `borrowerName` | string | ya | 2 sampai 100 karakter |
| `borrowerNim` | string | ya | 5 sampai 30 karakter, hanya angka, huruf, dan garis miring |
| `equipmentName` | string | ya | 2 sampai 100 karakter |
| `quantity` | integer | ya | 1 sampai 100 |
| `loanDate` | string (YYYY-MM-DD) | ya | Format tanggal ISO |
| `dueDate` | string (YYYY-MM-DD) | ya | Tidak boleh lebih awal dari `loanDate` |
| `notes` | string | tidak | Maksimal 255 karakter |
| `status` | string | tidak | `BORROWED` atau `RETURNED`. Saat create selalu `BORROWED` |
| `returnedAt` | string (ISO datetime) | tidak | Terisi otomatis saat status menjadi `RETURNED` |
| `createdAt`, `updatedAt` | string (ISO datetime) | tidak | Dibuat oleh server |

Field di luar daftar ini ditolak dengan status 422.

## Contoh request dan response

### POST /loans

Request:

```json
{
  "borrowerName": "Shafiyah Nuril Hayya",
  "borrowerNim": "24/540586/TK/60019",
  "equipmentName": "ESP32 DevKit",
  "quantity": 2,
  "loanDate": "2026-11-27",
  "dueDate": "2026-12-04",
  "notes": "Untuk praktikum IoT"
}
```

Response 201:

```json
{
  "loanId": "3f6c1d2e-8a4b-4c1f-9d57-2b7e0c9a1f10",
  "borrowerName": "Shafiyah Nuril Hayya",
  "borrowerNim": "24/540586/TK/60019",
  "equipmentName": "ESP32 DevKit",
  "quantity": 2,
  "loanDate": "2026-11-27",
  "dueDate": "2026-12-04",
  "status": "BORROWED",
  "notes": "Untuk praktikum IoT",
  "returnedAt": null,
  "createdAt": "2026-11-27T02:15:08+00:00",
  "updatedAt": "2026-11-27T02:15:08+00:00"
}
```

### GET /loans

Response 200 berupa array, diurutkan dari yang terbaru. Parameter opsional `status` bernilai `BORROWED` atau `RETURNED`.

```
GET /loans?status=BORROWED
```

### GET /loans/{loanId}

Response 200 berisi satu objek Loan seperti contoh di atas. Jika ID tidak ada, server membalas 404:

```json
{ "detail": "Data peminjaman tidak ditemukan" }
```

### PUT /loans/{loanId}

Semua field bersifat opsional, tetapi minimal satu field harus dikirim. Contoh untuk menandai alat sudah dikembalikan:

```json
{ "status": "RETURNED" }
```

Response 200 berisi objek Loan terbaru dengan `status` bernilai `RETURNED` dan `returnedAt` yang terisi. Jika status diubah kembali menjadi `BORROWED`, `returnedAt` dihapus. Untuk mengosongkan catatan, kirim `{ "notes": null }`.

### DELETE /loans/{loanId}

Response 204 tanpa body. Jika ID tidak ada, response 404.

### GET /health

Response 200 jika Lambda berhasil membaca metadata tabel:

Dengan backend S3 (Jalur D, sudah diuji di AWS):

```json
{ "status": "ok", "storage": "s3", "bucket": "equipment-loan-data-540586" }
```

Dengan backend DynamoDB (tidak bisa dipakai di Sandbox ini, hanya diuji dengan mock):

```json
{ "status": "ok", "table": "EquipmentLoans", "tableStatus": "ACTIVE" }
```

Response 503 jika tabel tidak bisa diakses:

```json
{ "status": "error", "detail": "Tidak bisa terhubung ke penyimpanan data" }
```

## Format error

| Status | Penyebab | Bentuk body |
|---|---|---|
| 404 | ID tidak ditemukan | `{"detail": "Data peminjaman tidak ditemukan"}` |
| 422 | Input tidak lolos validasi atau ID bukan UUID | `{"detail": [{"loc": ["body", "quantity"], "msg": "...", "type": "..."}]}` |
| 500 | Penyimpanan data tidak bisa diakses | `{"detail": "Terjadi kesalahan pada penyimpanan data"}` |
| 503 | Health check gagal | `{"status": "error", "detail": "..."}` |
