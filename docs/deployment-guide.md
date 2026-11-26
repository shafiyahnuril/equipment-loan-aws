# Panduan Deployment di AWS Learner Lab

Panduan ini dipakai untuk membangun semua resource lewat AWS Management Console, langkah demi langkah. Urutannya dibuat supaya setiap langkah menghasilkan bukti (screenshot) yang dibutuhkan untuk deliverable Week 12. Nama file bukti mengikuti daftar di `docs/evidence/README.md`.

Beberapa detail Learner Lab (nama menu, region, ketersediaan layanan) bisa sedikit berbeda di akun masing-masing. Jika tampilan di console tidak sama persis, ikuti tujuan langkahnya.

## 0. Persiapan

Perangkat yang dibutuhkan di komputer:

- Python 3.9 atau lebih baru (untuk menjalankan `build_package.py` dan smoke test)
- Node.js 20 atau lebih baru (hanya untuk frontend)
- Git

Langkah awal di AWS:

1. Buka course AWS Academy Learner Lab, masuk ke Learner Lab, lalu klik **Start Lab**.
2. Tunggu sampai indikator di samping tulisan AWS berubah menjadi hijau, kemudian klik **AWS** untuk membuka console.
3. Lihat pojok kanan atas console dan catat **region** yang aktif. Biasanya N. Virginia (`us-east-1`). Pakai region yang sama untuk semua resource.
4. Catat sisa budget yang tampil di halaman Learner Lab. Cek lagi setiap selesai satu tahap besar.

Bukti yang diambil: screenshot console yang memperlihatkan region di pojok kanan atas (`E01`).

## 1. Buat tabel DynamoDB

1. Di kolom pencarian console, ketik **DynamoDB** lalu buka layanannya.
2. Pilih **Tables**, lalu klik **Create table**.
3. Isi **Table name** dengan `EquipmentLoans`.
4. Isi **Partition key** dengan `loanId` dan pilih tipe **String**. Biarkan sort key kosong.
5. Di bagian **Table settings**, pilih **Customize settings**. Pada **Read/write capacity settings**, pilih **On-demand**.
6. Klik **Create table** dan tunggu status berubah menjadi **Active**.

Bukti yang diambil: halaman detail tabel yang memperlihatkan nama tabel, partition key, capacity mode on-demand, dan status Active (`E02`).

## 2. Buat paket Lambda

Jalankan di terminal dari folder root repository:

```
cd backend
python build_package.py
```

Script ini menghasilkan `backend/dist/lambda.zip`. Dependency diunduh dalam versi Linux x86_64 untuk Python 3.12 walaupun kamu memakai Windows atau macOS. Pastikan di akhir muncul tulisan `Selesai` beserta ukuran file.

## 3. Buat function Lambda

1. Buka layanan **Lambda**, lalu klik **Create function**.
2. Pilih **Author from scratch**.
3. Isi **Function name** dengan `equipment-loan-api`.
4. Pilih **Runtime** `Python 3.12` dan **Architecture** `x86_64`.
5. Buka bagian **Change default execution role**, pilih **Use an existing role**, lalu pilih **LabRole**. Learner Lab biasanya tidak mengizinkan pembuatan IAM role baru, jadi LabRole yang dipakai.
6. Klik **Create function**.
7. Di tab **Code**, klik **Upload from**, pilih **.zip file**, unggah `backend/dist/lambda.zip`, lalu **Save**.
8. Masih di tab **Code**, cari **Runtime settings**, klik **Edit**, isi **Handler** dengan `app.main.handler`, lalu simpan.
9. Buka tab **Configuration**, pilih **General configuration**, klik **Edit**. Atur **Memory** ke `256` MB dan **Timeout** ke `10` detik.
10. Masih di **Configuration**, pilih **Environment variables**, klik **Edit**, tambahkan key `TABLE_NAME` dengan value `EquipmentLoans`.

Uji function langsung dari console:

1. Buka tab **Test**, pilih **Create new event**, beri nama `health-test`.
2. Buka file `infra/test-event-health.json` di repository, salin seluruh isinya ke kotak **Event JSON**, lalu simpan.
3. Klik **Test**. Hasil yang benar menampilkan `"statusCode": 200` dan body berisi `"status":"ok"`.

Bukti yang diambil: halaman overview function dengan runtime, handler, dan role (`E03`), tab Environment variables yang memperlihatkan `TABLE_NAME` (`E04`), dan hasil Test yang berhasil (`E05`).

## 4. Buat API Gateway (HTTP API)

1. Buka layanan **API Gateway**, klik **Create API**, lalu pada kartu **HTTP API** klik **Build**.
2. Klik **Add integration**, pilih **Lambda**, lalu pilih function `equipment-loan-api`.
3. Isi **API name** dengan `equipment-loan-http-api`, lalu klik **Next**.
4. Di halaman **Configure routes**, buat enam route berikut. Semuanya memakai integration Lambda yang sama.

   | Method | Resource path |
   |---|---|
   | GET | /health |
   | GET | /loans |
   | POST | /loans |
   | GET | /loans/{loanId} |
   | PUT | /loans/{loanId} |
   | DELETE | /loans/{loanId} |

   Opsional, supaya Swagger UI bisa dibuka: tambahkan juga `GET /docs` dan `GET /openapi.json`.
5. Klik **Next**. Di halaman **Define stages**, biarkan stage `$default` dengan **Auto-deploy** aktif, lalu **Next** dan **Create**.
6. Setelah API dibuat, salin **Invoke URL** dari halaman detail API. Bentuknya seperti `https://abc123.execute-api.us-east-1.amazonaws.com`.

Atur CORS:

1. Di menu kiri API, buka **CORS**, lalu klik **Configure**.
2. **Access-Control-Allow-Origin**: isi `http://localhost:3000` dulu. Alamat website S3 ditambahkan nanti pada tahap 8.
3. **Access-Control-Allow-Methods**: `GET`, `POST`, `PUT`, `DELETE`, `OPTIONS`.
4. **Access-Control-Allow-Headers**: `content-type`.
5. **Access-Control-Max-Age**: `300`. Simpan.

Atur throttling (opsional tetapi disarankan):

1. Buka menu **Stages**, pilih `$default`, lalu klik **Edit** pada bagian **Default route throttling**.
2. Isi **Rate** `10` dan **Burst** `20`, lalu simpan.

Cek cepat dari browser: buka `Invoke URL` ditambah `/health`. Hasil yang benar adalah JSON dengan `"status":"ok"`.

Bukti yang diambil: daftar route beserta Invoke URL (`E06`) dan halaman pengaturan CORS (`E07`).

## 5. Jalankan smoke test

Dari root repository:

```
python backend/tests/smoke_test.py https://ISI-DENGAN-INVOKE-URL
```

Script menjalankan delapan pengujian berurutan (health, create, read satu, read daftar, update, input tidak valid, delete, dan data terhapus). Hasil yang benar adalah `Ringkasan: 8 dari 8 pengujian lulus`.

Bukti yang diambil: screenshot seluruh output terminal (`E08`).

## 6. Buktikan data benar-benar tersimpan di DynamoDB

Smoke test menghapus data ujinya di akhir, jadi buat satu data yang dibiarkan tersimpan. Dari root repository:

```
curl -X POST https://ISI-DENGAN-INVOKE-URL/loans -H "Content-Type: application/json" -d @tests/sample-loan.json
```

Di Windows PowerShell, tulis `curl.exe` sebagai pengganti `curl`. Setelah itu:

1. Buka DynamoDB, pilih tabel `EquipmentLoans`, lalu klik **Explore table items**.
2. Pastikan satu item muncul dengan nilai yang sama seperti yang dikirim.

Bukti yang diambil: output curl (`E09`) dan halaman item tabel di DynamoDB (`E10`).

## 7. Cek log di CloudWatch

1. Buka function Lambda, masuk ke tab **Monitor**, lalu klik **View CloudWatch logs**.
2. Buka log stream terbaru dan pastikan ada baris JSON berisi `"event": "request"`.

Bukti yang diambil: halaman log stream (`E11`).

## 8. Frontend di S3 (bonus untuk Week 12, wajib untuk Week 14)

Buat bucket:

1. Buka layanan **S3**, klik **Create bucket**.
2. Isi **Bucket name** dengan nama unik, misalnya `equipment-loan-web-540586`. Region sama dengan resource lain.
3. Pada **Block Public Access settings**, hilangkan centang **Block all public access** dan centang pernyataan konfirmasi di bawahnya. Klik **Create bucket**.
4. Jika opsi ini tidak bisa diubah di akunmu, lewati tahap ini dan jalankan frontend secara lokal dengan `npm run dev`.

Aktifkan static website hosting:

1. Buka bucket, tab **Properties**, gulir ke **Static website hosting**, klik **Edit**.
2. Pilih **Enable**, isi **Index document** dengan `index.html` dan **Error document** dengan `404.html`. Simpan.
3. Catat **Bucket website endpoint** yang muncul, misalnya `http://equipment-loan-web-540586.s3-website-us-east-1.amazonaws.com`.

Izinkan pengunjung membaca file website. Buka tab **Permissions**, bagian **Bucket policy**, klik **Edit**, lalu tempel kebijakan berikut dengan nama bucket yang sesuai:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "PublicReadForWebsite",
      "Effect": "Allow",
      "Principal": "*",
      "Action": "s3:GetObject",
      "Resource": "arn:aws:s3:::NAMA-BUCKET-KAMU/*"
    }
  ]
}
```

Build dan unggah frontend:

```
cd frontend
copy .env.example .env.production     (Windows)
cp .env.example .env.production       (macOS atau Linux)
```

Buka `.env.production`, isi `NEXT_PUBLIC_API_URL` dengan Invoke URL tanpa garis miring di akhir. Lalu:

```
npm install
npm run build
```

Build menghasilkan folder `frontend/out`. Di bucket S3 klik **Upload**, lalu seret **isi** folder `out` (file `index.html`, `404.html`, dan folder `_next`), bukan folder `out` itu sendiri.

Terakhir, tambahkan alamat website ke CORS. Kembali ke API Gateway, buka **CORS**, lalu tambahkan origin website S3 persis seperti endpoint tadi tanpa garis miring di akhir, misalnya `http://equipment-loan-web-540586.s3-website-us-east-1.amazonaws.com`. Biarkan `http://localhost:3000` tetap ada.

Buka alamat website di browser. Tambahkan satu peminjaman lewat form dan pastikan tabelnya terisi.

Bukti yang diambil: halaman static website hosting (`E12`) dan tampilan website yang menampilkan data (`E13`).

## 9. Push ke GitHub

1. Buat repository kosong di GitHub, misalnya `equipment-loan-aws`.
2. Dari root repository:

   ```
   git remote add origin https://github.com/USERNAME-KAMU/equipment-loan-aws.git
   git push -u origin main
   ```
3. Pastikan repository bisa dibuka oleh dosen, baik dengan mengatur visibility menjadi public atau menambahkan akses sesuai arahan dosen.
4. Sebelum push, cek bahwa tidak ada credential di repository. File `~/.aws/credentials` dan `.env.production` tidak boleh ikut ter-commit. Keduanya sudah masuk `.gitignore`.

Bukti yang diambil: halaman GitHub yang menampilkan daftar commit (`E14`).

## 10. Menghemat kredit

- Layanan yang dipakai proyek ini dibayar sesuai pemakaian dan tidak punya biaya saat idle, jadi risiko kredit habis kecil. Tetap cek budget secara berkala.
- Jangan membuat EC2, RDS, NAT Gateway, atau load balancer untuk proyek ini karena ketiganya bisa menghabiskan kredit meskipun tidak dipakai.
- Klik **End Lab** saat selesai bekerja. Cek di sesi berikutnya apakah resource masih ada, karena perilaku ini bisa berbeda antar akun.
- Langkah penghapusan resource ada di bagian Cleanup pada `README.md`.

## Troubleshooting

| Gejala | Penyebab yang paling sering | Solusi |
|---|---|---|
| `Unable to import module 'app.main'` | Struktur zip salah atau handler keliru | Pastikan handler `app.main.handler` dan folder `app` berada di root zip. Buat ulang dengan `build_package.py` |
| Error saat import `pydantic_core` | Zip dibuat dengan platform yang salah | Buat ulang dengan `build_package.py` dan pastikan architecture Lambda `x86_64` |
| API membalas `{"message":"Not Found"}` | Route atau method belum dibuat | Cek daftar route di API Gateway |
| API membalas 500 dengan detail penyimpanan data | `TABLE_NAME` salah atau LabRole tidak punya akses | Cek environment variable dan buka CloudWatch Logs |
| Browser menampilkan error CORS | Origin belum didaftarkan atau ada garis miring di akhir | Samakan origin dengan alamat di address bar, lengkap dengan `http://` |
| S3 membalas `403 Forbidden` | Bucket policy belum dipasang atau Block Public Access masih aktif | Periksa kedua pengaturan tersebut |
| Halaman S3 kosong atau 404 | Yang terunggah adalah folder `out`, bukan isinya | Unggah ulang isi folder `out` ke root bucket |
| Website menampilkan "Alamat API belum diatur" | Build dilakukan tanpa `.env.production` | Isi `NEXT_PUBLIC_API_URL`, lalu jalankan `npm run build` dan unggah ulang |
