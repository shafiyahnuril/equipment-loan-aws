import { formatDate, todayString } from "@/lib/format";
import type { Loan } from "@/lib/types";
import StatusBadge from "./StatusBadge";

interface Props {
  loans: Loan[];
  busyId: string | null;
  onReturn: (loan: Loan) => void;
  onEdit: (loan: Loan) => void;
  onDelete: (loan: Loan) => void;
}

export default function LoanTable({ loans, busyId, onReturn, onEdit, onDelete }: Props) {
  const today = todayString();

  return (
    <div className="table-wrap">
      <table>
        <thead>
          <tr>
            <th>Alat</th>
            <th>Jumlah</th>
            <th>Peminjam</th>
            <th>Tanggal pinjam</th>
            <th>Jatuh tempo</th>
            <th>Status</th>
            <th>Aksi</th>
          </tr>
        </thead>
        <tbody>
          {loans.map((loan) => {
            const overdue = loan.status === "BORROWED" && loan.dueDate < today;
            const busy = busyId === loan.loanId;
            return (
              <tr key={loan.loanId}>
                <td>
                  <strong>{loan.equipmentName}</strong>
                  {loan.notes && <div className="muted">{loan.notes}</div>}
                </td>
                <td>{loan.quantity}</td>
                <td>
                  {loan.borrowerName}
                  <div className="muted">{loan.borrowerNim}</div>
                </td>
                <td>{formatDate(loan.loanDate)}</td>
                <td>{formatDate(loan.dueDate)}</td>
                <td>
                  <StatusBadge status={loan.status} overdue={overdue} />
                  {loan.returnedAt && <div className="muted">{formatDate(loan.returnedAt.slice(0, 10))}</div>}
                </td>
                <td>
                  <div className="row-actions">
                    {loan.status === "BORROWED" && (
                      <button type="button" className="btn btn-small btn-primary" onClick={() => onReturn(loan)} disabled={busy}>
                        Tandai dikembalikan
                      </button>
                    )}
                    <button type="button" className="btn btn-small" onClick={() => onEdit(loan)} disabled={busy}>
                      Ubah
                    </button>
                    <button type="button" className="btn btn-small btn-danger" onClick={() => onDelete(loan)} disabled={busy}>
                      Hapus
                    </button>
                  </div>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
