import type { LoanStatus } from "@/lib/types";

const LABELS: Record<LoanStatus, string> = {
  BORROWED: "Dipinjam",
  RETURNED: "Dikembalikan",
};

export default function StatusBadge({ status, overdue }: { status: LoanStatus; overdue?: boolean }) {
  const className = overdue ? "badge badge-overdue" : status === "RETURNED" ? "badge badge-returned" : "badge badge-borrowed";
  return <span className={className}>{overdue ? "Terlambat" : LABELS[status]}</span>;
}
