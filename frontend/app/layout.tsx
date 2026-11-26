import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Peminjaman Alat Lab",
  description: "Aplikasi pencatatan peminjaman alat laboratorium berbasis AWS serverless",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="id">
      <body>{children}</body>
    </html>
  );
}
