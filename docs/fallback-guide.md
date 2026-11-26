# Panduan Rencana Cadangan

Panduan ini dipakai hanya jika di akun Sandbox ternyata **DynamoDB** atau **API Gateway** tidak bisa dipakai (muncul `AccessDenied` atau pesan bahwa layanan tidak diizinkan). Kode sudah mendukung kedua jalur, jadi tidak ada file yang perlu diubah. Yang berbeda hanya environment variable dan cara membuat resource di konsol.

| Masalah | Pengganti | Perubahan |
|---|---|---|
| DynamoDB ditolak | Bucket S3 privat untuk data | Set `STORAGE_BACKEND=s3` dan `DATA_BUCKET=<nama bucket data>` pada Lambda |
| API Gateway ditolak | Lambda Function URL | Buat Function URL di Lambda dan pakai URL itu sebagai `NEXT_PUBLIC_API_URL` |

Keduanya bisa dipakai sendiri-sendiri. Misalnya DynamoDB berhasil tetapi API Gateway ditolak, maka cukup ganti API Gateway dengan Function URL.

## A. Pengganti DynamoDB: bucket data di S3

1. Buka **S3**, klik **Create bucket**, isi nama unik misalnya `equipment-loan-data-<nim-terakhir>`, region `us-east-1`.
2. **Biarkan Block all public access tetap aktif.** Bucket ini berisi data dan tidak boleh publik.
3. Buka Lambda `equipment-loan-api`, lalu **Configuration**, **Environment variables**, **Edit**.
4. Tambahkan dua variable:
   - `STORAGE_BACKEND` dengan value `s3`
   - `DATA_BUCKET` dengan value nama bucket data tadi
5. Jalankan Test event `/health`. Hasil yang benar adalah `statusCode 200` dengan `"storage":"s3"`.

Cara kerjanya: setiap peminjaman disimpan sebagai satu file JSON di `loans/<loanId>.json`. Endpoint CRUD, status code, dan validasi tetap sama persis. Hal yang berbeda ada pada dua hal. Pertama, update dilakukan dengan membaca lalu menulis ulang file, jadi tidak seatomik DynamoDB. Kedua, daftar peminjaman dibaca file demi file, sehingga cocok untuk data dalam jumlah kecil seperti demo ini.

Bukti yang diambil sebagai pengganti tabel DynamoDB: halaman bucket data dengan folder `loans/` berisi file JSON, dan isi salah satu file setelah menambah data lewat website.

## B. Pengganti API Gateway: Lambda Function URL

1. Buka Lambda `equipment-loan-api`, tab **Configuration**, menu **Function URL**, klik **Create function URL**.
2. Auth type: **NONE**.
3. Centang **Configure cross-origin resource sharing (CORS)** lalu isi:
   - Allow origin: URL website S3 (tanpa garis miring di akhir). Tambahkan juga `http://localhost:3000` kalau ingin mencoba lokal.
   - Allow methods: `GET`, `POST`, `PUT`, `DELETE`
   - Allow headers: `content-type`
4. Klik **Save** dan salin Function URL, bentuknya `https://xxxx.lambda-url.us-east-1.on.aws`.
5. Uji dari terminal:

```bash
curl https://xxxx.lambda-url.us-east-1.on.aws/health
curl https://xxxx.lambda-url.us-east-1.on.aws/loans
```

Tidak perlu mengubah kode. Function URL memakai format event yang sama dengan HTTP API versi 2.0, jadi Mangum bisa langsung membacanya.

Jika hasilnya `403 Forbidden`, buka **Configuration**, **Permissions**, **Resource-based policy statements**, lalu pastikan ada izin `lambda:InvokeFunctionUrl` untuk principal `*` dengan auth type NONE. Jika belum ada, tambahkan lewat **Add permissions**. Beberapa akun juga meminta izin `lambda:InvokeFunction`.

Karena CORS diatur di Function URL, jangan menambahkan CORS lagi di dalam kode FastAPI.

Bukti yang diambil sebagai pengganti API Gateway: halaman Function URL dengan konfigurasi CORS, dan hasil `curl` ke URL tersebut.

## C. Frontend tetap sama

Isi `NEXT_PUBLIC_API_URL` di `frontend/.env.local` dengan Function URL (atau Invoke URL API Gateway kalau tersedia), tanpa garis miring di akhir. Lalu jalankan `npm run build` dan unggah isi folder `out` ke bucket website seperti biasa. Bucket website dan bucket data adalah dua bucket yang berbeda.
