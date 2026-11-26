// Ubah "2026-11-27" menjadi "27 Nov 2026"
export function formatDate(value: string): string {
  const date = new Date(`${value}T00:00:00`);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleDateString("id-ID", { day: "numeric", month: "short", year: "numeric" });
}

// Tanggal hari ini dalam zona waktu lokal, format YYYY-MM-DD
export function todayString(): string {
  return new Date().toLocaleDateString("sv-SE");
}
