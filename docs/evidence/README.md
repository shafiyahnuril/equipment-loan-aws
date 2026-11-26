# Folder Bukti AWS

Folder ini menyimpan screenshot dan output pengujian untuk deliverable "AWS evidence". Simpan file dengan nama sesuai tabel di bawah supaya mudah ditelusuri dari design brief dan README.

Sebelum mengunggah, pastikan tidak ada credential yang terlihat di screenshot. Tutup bagian **AWS Details** di halaman Learner Lab, dan jangan memotret isi file `~/.aws/credentials`.

| Kode | Nama file | Isi yang harus terlihat | Panduan |
|---|---|---|---|
| E01 | `E01-console-region.png` | Console AWS dengan region di pojok kanan atas | Langkah 0 |
| E02 | `E02-dynamodb-table.png` | Tabel `EquipmentLoans`, partition key `loanId`, on-demand, status Active | Langkah 1 |
| E03 | `E03-lambda-overview.png` | Function `equipment-loan-api`, runtime Python 3.12, handler, role LabRole | Langkah 3 |
| E04 | `E04-lambda-env.png` | Environment variable `TABLE_NAME` | Langkah 3 |
| E05 | `E05-lambda-test-health.png` | Hasil Test event `/health` dengan statusCode 200 | Langkah 3 |
| E06 | `E06-apigw-routes.png` | Enam route dan Invoke URL | Langkah 4 |
| E07 | `E07-apigw-cors.png` | Pengaturan CORS | Langkah 4 |
| E08 | `E08-smoke-test.png` | Output terminal `smoke_test.py` dengan ringkasan 8 dari 8 lulus | Langkah 5 |
| E09 | `E09-curl-post.png` | Output curl `POST /loans` dengan status 201 | Langkah 6 |
| E10 | `E10-dynamodb-items.png` | Item yang tersimpan di tabel | Langkah 6 |
| E11 | `E11-cloudwatch-logs.png` | Log stream Lambda berisi log request | Langkah 7 |
| E12 | `E12-s3-website.png` | Static website hosting aktif beserta endpoint (bonus) | Langkah 8 |
| E13 | `E13-website.png` | Website yang menampilkan data peminjaman (bonus) | Langkah 8 |
| E14 | `E14-github-commits.png` | Riwayat commit di GitHub | Langkah 9 |

E12 dan E13 hanya diambil jika tahap frontend sudah selesai. Jika belum, hapus kedua slot tersebut dari lampiran PDF.
