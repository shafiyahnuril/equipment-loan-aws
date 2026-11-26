# Equipment Loan on AWS

Aplikasi web untuk mencatat peminjaman alat laboratorium, dibangun dengan arsitektur serverless di AWS Academy Sandbox. Proyek ini adalah tugas individu mata kuliah Komputasi Awan (TKIF262401), DTETI UGM.

Pengguna bisa mencatat siapa meminjam alat apa, melihat daftar peminjaman, menandai alat yang sudah dikembalikan, mengubah data, dan menghapus catatan yang salah.

## Use case dan track

| Item | Pilihan |
|---|---|
| Use case | Peminjaman alat laboratorium (equipment loan) |
| Track | Track C, Serverless |
| Entity | `Loan` (satu file JSON per peminjaman) |
| Operasi | Create, Read, Update, dan Delete lewat REST API |

Pencatatan peminjaman alat lab sering dilakukan manual di buku atau spreadsheet, sehingga sulit melacak alat yang belum kembali. Aplikasi ini menyimpan semuanya di satu tempat dan menandai peminjaman yang melewati jatuh tempo. Track C dipilih karena tidak ada server yang perlu dikelola, biayanya mengikuti pemakaian, dan cocok dengan kredit Sandbox yang terbatas.

## Arsitektur yang dipakai (Jalur D)

Rancangan awal memakai API Gateway dan DynamoDB. Saat diuji di akun Sandbox pada 26 November 2026, dua layanan itu ditolak:

| Layanan | Perintah yang dicoba | Pesan error |
|---|---|---|
| DynamoDB | `dynamodb create-table` | `not authorized to perform: dynamodb:CreateTable ... because no identity-based policy allows the dynamodb:CreateTable action` |
| API Gateway | `apigatewayv2 create-api` | `not authorized to perform: apigateway:POST on resource: arn:aws:apigateway:us-east-1::/apis because no identity-based policy allows the apigateway:POST action` |

Penolakan itu tidak disiasati. Keduanya diganti dengan alternatif yang sah dan tetap serverless:

| Komponen | Peran |
|---|---|
| Amazon S3 (bucket data privat) | Pengganti DynamoDB. Setiap peminjaman disimpan sebagai file `loans/<loanId>.json`. Block Public Access tetap aktif |
| AWS Lambda Function URL | Pengganti API Gateway. Pintu masuk HTTPS ke Lambda dengan auth type NONE, CORS diatur di Function URL |
| AWS Lambda | Menjalankan FastAPI (dibungkus Mangum) dengan Python 3.12, role `LabRole` |
| Amazon CloudWatch Logs | Menyimpan log request dari Lambda |
| Amazon S3 (website) | Rencana untuk menyajikan frontend Next.js. Belum dikerjakan |

Alur request: browser memanggil Function URL lewat HTTPS, Lambda membaca atau menulis file JSON di bucket data, lalu mengirim jawabannya kembali ke browser.

Catatan penting soal diagram: `docs/architecture.png` dan `docs/architecture.drawio` **masih menggambar rancangan awal** (API Gateway dan DynamoDB). Diagram Jalur D belum dibuat, jadi dua file itu belum sesuai dengan kondisi yang berjalan.

Konsekuensi dari Jalur D:

- Update dilakukan dengan membaca lalu menulis ulang file, jadi tidak seatomik DynamoDB.
- Daftar peminjaman dibaca file demi file, cocok untuk data kecil seperti demo ini.
- Function URL tidak punya throttling seperti API Gateway.

## Teknologi

| Lapisan | Teknologi |
|---|---|
| Frontend | Next.js (App Router), React, TypeScript, static export |
| Backend | Python 3.12, FastAPI, Mangum, Pydantic, boto3 |
| Penyimpanan | S3 (Jalur D). Kode juga mendukung DynamoDB lewat `STORAGE_BACKEND` |
| Testing | pytest, moto (mock DynamoDB dan S3), smoke test untuk API yang sudah di-deploy |

## Struktur repository

```
equipment-loan-aws/
├── backend/
│   ├── app/                  kode FastAPI (main, routes, schemas, repository DynamoDB dan S3, config)
│   ├── tests/                unit test (pytest + moto) dan smoke_test.py
│   ├── build_package.py      membuat dist/lambda.zip untuk Lambda
│   └── requirements.txt
├── frontend/                 aplikasi Next.js (static export ke S3)
├── infra/
│   └── test-event-health.json  event uji untuk Lambda
├── scripts/                  backup dan restore Sandbox (lihat bagian di bawah)
├── docs/
│   ├── architecture.png      diagram arsitektur rancangan awal
│   ├── architecture.drawio   diagram arsitektur rancangan awal (bisa diedit di draw.io)
│   ├── api-spec.md           spesifikasi API
│   ├── deployment-guide.md   panduan deployment
│   ├── fallback-guide.md     rencana cadangan (Jalur D)
│   └── evidence/             screenshot bukti AWS
└── tests/
    └── sample-loan.json      contoh body untuk curl
```

## API

| Operasi | Endpoint |
|---|---|
| Create | `POST /loans` |
| Read | `GET /loans` dan `GET /loans/{loanId}` |
| Update | `PUT /loans/{loanId}` |
| Delete | `DELETE /loans/{loanId}` |
| Health | `GET /health` |

Detail request, response, dan aturan validasi ada di [docs/api-spec.md](docs/api-spec.md).

## Menjalankan test secara lokal

Test backend tidak membutuhkan akun AWS karena DynamoDB dan S3 di-mock dengan moto. Setiap test dijalankan untuk kedua backend penyimpanan.

```
cd backend
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt
pytest
```

Untuk menjalankan frontend secara lokal dan menghubungkannya ke API yang sudah di-deploy:

```
cd frontend
cp .env.example .env.local       # Windows: copy .env.example .env.local
# isi NEXT_PUBLIC_API_URL di .env.local dengan Function URL
npm install
npm run dev
```

Alamat `http://localhost:3000` harus sudah terdaftar di pengaturan CORS Function URL.

## Rencana deployment

Deployment Jalur D dilakukan dengan AWS CLI di Sandbox. Langkahnya ada di [docs/deployment-guide.md](docs/deployment-guide.md) dan [docs/fallback-guide.md](docs/fallback-guide.md).

| Fase | Isi | Hasil |
|---|---|---|
| 1. Persiapan (Week 12) | Buat bucket data, Lambda, dan Function URL, lalu uji dengan `/health` dan smoke test | Koneksi AWS terverifikasi |
| 2. Frontend (Week 12 sampai 13) | Build Next.js, unggah ke S3, atur CORS | Belum dikerjakan |
| 3. Penguatan (Week 13 sampai 14) | Rapikan IAM, tambah alarm CloudWatch, uji persistence dan skenario failure | Belum dikerjakan |
| 4. Penutupan (Week 14) | Perbarui diagram menjadi as-built, rekam demo, lakukan cleanup | Belum dikerjakan |

## Backup dan restore Sandbox

Sandbox menghapus semua resource saat sesi habis. Dua script di folder `scripts/` membantu menyimpan progres dan membuat ulang backend:

- `python scripts/sandbox_backup.py` menyimpan snapshot konfigurasi, data peminjaman, dan zip Lambda ke `.local/` (tidak masuk Git). Script ini hanya membaca.
- `python scripts/sandbox_restore.py` membuat ulang bucket data, Lambda, Function URL, dan izinnya. Opsi `--restore-data`, `--seed`, `--dry-run`, dan `--frontend` tersedia.

Status pengujian yang jujur: backup dan restore sudah dicoba terhadap resource yang **sudah ada** (idempotent, tidak ada yang berubah, verifikasi lulus). **Pembuatan dari nol belum teruji**, begitu juga `--restore-data`, `--seed`, dan `--frontend`. Panduan pemakaian ada di [scripts/README_restore.md](scripts/README_restore.md).

## Keamanan

- Lambda memakai `LabRole` karena Sandbox tidak mengizinkan pembuatan IAM role baru. Rencana lanjutan adalah mendokumentasikan izin minimum yang dibutuhkan, yaitu akses ke satu bucket data dan penulisan log.
- Tidak ada secret di kode maupun Git. Nama bucket dibaca dari environment variable, dan `.gitignore` mengecualikan file `.env`, key, serta folder `.aws`.
- Bucket data tidak publik (Block Public Access aktif).
- Input divalidasi di server dengan Pydantic dan di browser lewat form.
- CORS dibatasi ke origin website dan `localhost:3000`, bukan semua origin. CORS diatur di Function URL.
- Function URL memakai auth type NONE dan tidak ada throttling. Siapa pun yang tahu URL-nya bisa memanggil API, dan belum ada autentikasi. Hal ini diterima untuk tahap proyek ini dan menjadi bahan pengembangan berikutnya.

## Troubleshooting

| Gejala | Penyebab | Solusi |
|---|---|---|
| Function URL membalas `403 Forbidden` dengan pesan tentang `lambda:InvokeFunctionUrl` dan `lambda:InvokeFunction` | Hanya izin `lambda:InvokeFunctionUrl` yang terpasang | Tambahkan juga izin `lambda:InvokeFunction` untuk principal `*` dengan opsi `--invoked-via-function-url`. Setelah itu respons menjadi 200. Ini yang terjadi saat deployment pertama |
| `AccessDeniedException` saat membuat tabel DynamoDB atau API Gateway | Layanan tidak diizinkan di Sandbox | Pakai Jalur D (bucket data S3 dan Function URL) |
| Perintah `aws logs` gagal dengan `Member must satisfy regular expression pattern` di Git Bash | Git Bash mengubah `/aws/...` menjadi path Windows | Jalankan `export MSYS_NO_PATHCONV=1` sebelum perintah |

## Cleanup

Sandbox membersihkan semua resource secara otomatis saat sesi berakhir. Jika ingin membersihkan lebih awal, hanya hapus resource yang dibuat sendiri:

1. Lambda: hapus Function URL, lalu function `equipment-loan-api`.
2. CloudWatch: hapus log group `/aws/lambda/equipment-loan-api`.
3. S3: kosongkan lalu hapus bucket data (dan bucket website jika ada).
4. Hapus file credential lokal dan pastikan tidak ada yang ikut ter-commit.

## Status pengerjaan Week 12

Dicentang hanya untuk item yang sudah terbukti dari output nyata.

- [x] Use case dan track dipilih
- [x] Diagram arsitektur rancangan awal dibuat (belum diperbarui ke Jalur D)
- [x] Design brief disusun (belum diperbarui ke Jalur D)
- [x] Starter code backend dan frontend, beserta unit test (48 test lulus dengan mock)
- [x] Script build, smoke test, dan panduan deployment
- [x] Bucket data S3 dibuat di Sandbox (pengganti tabel DynamoDB, yang ditolak)
- [x] Lambda dan Function URL dibuat, `/health` mengembalikan status 200 dengan `storage: s3` (pengganti API Gateway, yang ditolak)
- [x] Smoke test lulus terhadap API di AWS (8 dari 8)
- [ ] Bukti screenshot AWS terkumpul di `docs/evidence/`
- [ ] Diagram dan Design Brief diperbarui ke Jalur D
- [ ] Frontend diunggah ke S3 (bonus Week 12)
