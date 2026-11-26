import type { Loan, LoanInput, LoanStatus, LoanUpdate } from "./types";

// Nilai ini ditanam saat build (npm run build) dari file .env.production
export const API_URL = (process.env.NEXT_PUBLIC_API_URL ?? "").replace(/\/+$/, "");

export class ApiError extends Error {
  status: number;

  constructor(message: string, status: number) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

function readMessage(body: unknown, status: number): string {
  if (body && typeof body === "object" && "detail" in body) {
    const detail = (body as { detail: unknown }).detail;
    if (typeof detail === "string") return detail;
    if (Array.isArray(detail)) {
      // Format error validasi dari FastAPI
      return detail
        .map((item) => {
          const field = Array.isArray(item?.loc) ? item.loc.slice(1).join(".") : "";
          return field ? `${field}: ${item?.msg}` : String(item?.msg ?? "Data tidak valid");
        })
        .join(", ");
    }
  }
  return `Permintaan gagal (status ${status})`;
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  if (!API_URL) {
    throw new ApiError("NEXT_PUBLIC_API_URL belum diisi. Lihat README bagian konfigurasi frontend.", 0);
  }

  const headers: Record<string, string> = {};
  // Header Content-Type hanya dikirim jika ada body, supaya request GET tidak memicu preflight
  if (options.body) headers["Content-Type"] = "application/json";

  let response: Response;
  try {
    response = await fetch(`${API_URL}${path}`, { ...options, headers });
  } catch {
    throw new ApiError("Tidak bisa terhubung ke server. Periksa koneksi internet dan pengaturan CORS di API Gateway.", 0);
  }

  if (response.status === 204) return undefined as T;

  const body = await response.json().catch(() => null);
  if (!response.ok) throw new ApiError(readMessage(body, response.status), response.status);
  return body as T;
}

export function listLoans(status?: LoanStatus): Promise<Loan[]> {
  const query = status ? `?status=${status}` : "";
  return request<Loan[]>(`/loans${query}`);
}

export function createLoan(input: LoanInput): Promise<Loan> {
  return request<Loan>("/loans", { method: "POST", body: JSON.stringify(input) });
}

export function updateLoan(loanId: string, changes: LoanUpdate): Promise<Loan> {
  return request<Loan>(`/loans/${loanId}`, { method: "PUT", body: JSON.stringify(changes) });
}

export function deleteLoan(loanId: string): Promise<void> {
  return request<void>(`/loans/${loanId}`, { method: "DELETE" });
}
