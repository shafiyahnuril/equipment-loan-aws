# Equipment Loan on AWS

Aplikasi web untuk mencatat peminjaman alat laboratorium, dibangun dengan arsitektur serverless di AWS Learner Lab. Proyek ini adalah tugas individu mata kuliah Komputasi Awan (TKIF262401), DTETI UGM.

Pengguna bisa mencatat siapa meminjam alat apa, melihat daftar peminjaman, menandai alat yang sudah dikembalikan, mengubah data, dan menghapus catatan yang salah.

## Use case dan track

| Item | Pilihan |
|---|---|
| Use case | Peminjaman alat laboratorium (equipment loan) |
| Track | Track C, Serverless |
| Entity | `Loan` (satu tabel DynamoDB) |
| Operasi | Create, Read, Update, dan Delete lewat REST API |

Pencatatan peminjaman alat lab sering dilakukan manual di buku atau spreadsheet, sehingga sulit melacak alat yang belum kembali. Aplikasi ini menyimpan semuanya di satu tempat dan menandai peminjaman yang melewati jatuh tempo. Track C dipilih karena tidak ada server yang perlu dikelola, biayanya mengikuti pemakaian, dan cocok dengan kredit Learner Lab yang tidak bisa di-reset.

## Arsitektur

![Diagram arsitektur](docs/architecture.png)

| Komponen | Peran |
|---|---|
| Amazon S3 | Menyajikan website Next.js hasil static export |
| Amazon API Gateway (HTTP API) | Pintu masuk REST API, mengatur CORS dan throttling |
| AWS Lambda | Menjalankan FastAPI (dibungkus Mangum) dengan Python 3.12 |
| Amazon DynamoDB | Menyimpan data peminjaman pada tabel `EquipmentLoans` |
| Amazon CloudWatch Logs | Menyimpan log request dan error dari Lambda |
| IAM Role `LabRole` | Execution role Lambda untuk mengakses DynamoDB dan CloudWatch Logs |

Alur request secara singkat: browser memuat halaman dari S3, lalu JavaScript di browser memanggil API Gateway lewat HTTPS. API Gateway meneruskan request ke Lambda, dan Lambda membaca atau menulis data di DynamoDB lalu mengirim jawabannya kembali ke browser.

## Teknologi

| Lapisan | Teknologi |
|---|---|
| Frontend | Next.js (App Router), React, TypeScript, static export |
| Backend | Python 3.12, FastAPI, Mangum, Pydantic, boto3 |
| Database | DynamoDB mode on-demand |
| Testing | pytest, moto (mock DynamoDB), smoke test untuk API yang sudah di-deploy |

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
│   └── test-event-health.json  event uji untuk Lambda di console
├── docs/
│   ├── architecture.png      diagram arsitektur (gambar)
│   ├── architecture.drawio   diagram arsitektur (bisa diedit di draw.io)
│   ├── api-spec.md           spesifikasi API
│   ├── deployment-guide.md   panduan deployment langkah demi langkah
│   ├── fallback-guide.md     rencana cadangan jika DynamoDB atau API Gateway tidak tersedia
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
# isi NEXT_PUBLIC_API_URL di .env.local dengan Invoke URL API Gateway
npm install
npm run dev
```

Alamat `http://localhost:3000` harus sudah terdaftar di pengaturan CORS API Gateway.

## Rencana deployment

Deployment dilakukan manual lewat console AWS Academy Sandbox. Panduan lengkapnya ada di [docs/deployment-guide.md](docs/deployment-guide.md). Jika DynamoDB atau API Gateway ternyata tidak diizinkan di akun, backend mendukung S3 sebagai penyimpanan dan Lambda Function URL sebagai pintu masuk API. Caranya ada di [docs/fallback-guide.md](docs/fallback-guide.md).

| Fase | Isi | Hasil |
|---|---|---|
| 1. Persiapan (Week 12) | Buat tabel DynamoDB, Lambda, dan HTTP API, lalu uji koneksi dengan `/health` dan smoke test | Koneksi AWS terverifikasi |
| 2. Frontend (Week 12 sampai 13) | Build Next.js, unggah ke S3, atur CORS | Website terhubung ke API |
| 3. Penguatan (Week 13 sampai 14) | Rapikan IAM, tambah alarm CloudWatch, uji persistence dan skenario failure | Aplikasi siap demo |
| 4. Penutupan (Week 14) | Perbarui diagram menjadi as-built, rekam demo, lakukan cleanup | Paket pengumpulan final |

## Keamanan

- Lambda memakai `LabRole` karena Learner Lab tidak mengizinkan pembuatan IAM role baru. Rencana lanjutan adalah mendokumentasikan izin minimum yang dibutuhkan, yaitu aksi DynamoDB pada satu tabel dan penulisan log.
- Tidak ada secret di kode maupun Git. Nama tabel dibaca dari environment variable, dan `.gitignore` mengecualikan file `.env`, key, serta folder `.aws`.
- Input divalidasi di server dengan Pydantic dan di browser lewat form.
- CORS dibatasi ke origin website dan `localhost:3000`, bukan semua origin.
- API Gateway memakai throttling untuk membatasi penyalahgunaan.
- Keterbatasan saat ini adalah API belum memakai autentikasi, sehingga siapa pun yang tahu URL-nya bisa memanggil API. Hal ini diterima untuk tahap proyek ini dan menjadi bahan pengembangan berikutnya.

## Cleanup

Lakukan di akhir proyek supaya tidak ada resource yang tersisa. Urutannya:

1. S3: kosongkan bucket website (**Empty**), lalu hapus bucketnya (**Delete**).
2. API Gateway: hapus API `equipment-loan-http-api`.
3. Lambda: hapus function `equipment-loan-api`.
4. CloudWatch: hapus log group `/aws/lambda/equipment-loan-api`.
5. DynamoDB: hapus tabel `EquipmentLoans`.
6. Cek halaman Learner Lab untuk memastikan budget tidak berkurang lagi.
7. Hapus file credential lokal dan pastikan tidak ada yang ikut ter-commit.

## Status pengerjaan Week 12

- [x] Use case dan track dipilih
- [x] Diagram arsitektur dibuat
- [x] Design brief disusun
- [x] Starter code backend dan frontend, beserta unit test
- [x] Script build, smoke test, dan panduan deployment
- [ ] Tabel DynamoDB dibuat di Learner Lab
- [ ] Lambda dan API Gateway dibuat, `/health` mengembalikan status 200
- [ ] Smoke test lulus terhadap API di AWS
- [ ] Bukti AWS terkumpul di `docs/evidence/`
- [ ] Frontend diunggah ke S3 (bonus Week 12)
