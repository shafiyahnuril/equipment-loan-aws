"use client";

import { useCallback, useEffect, useState } from "react";
import ConfirmDialog from "@/components/ConfirmDialog";
import LoanForm from "@/components/LoanForm";
import LoanTable from "@/components/LoanTable";
import { API_URL, createLoan, deleteLoan, listLoans, updateLoan } from "@/lib/api";
import type { Loan, LoanInput, LoanStatus } from "@/lib/types";

type Notice = { type: "success" | "error"; text: string } | null;

export default function HomePage() {
  const [loans, setLoans] = useState<Loan[]>([]);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [filter, setFilter] = useState<LoanStatus | "ALL">("ALL");
  const [editing, setEditing] = useState<Loan | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [busyId, setBusyId] = useState<string | null>(null);
  const [deleteTarget, setDeleteTarget] = useState<Loan | null>(null);
  const [notice, setNotice] = useState<Notice>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setLoadError(null);
    try {
      setLoans(await listLoans(filter === "ALL" ? undefined : filter));
    } catch (error) {
      setLoadError(error instanceof Error ? error.message : "Gagal memuat data");
    } finally {
      setLoading(false);
    }
  }, [filter]);

  useEffect(() => {
    load();
  }, [load]);

  async function handleSubmit(values: LoanInput): Promise<boolean> {
    setSubmitting(true);
    setNotice(null);
    try {
      if (editing) {
        await updateLoan(editing.loanId, values);
        setNotice({ type: "success", text: "Perubahan berhasil disimpan." });
        setEditing(null);
      } else {
        await createLoan(values);
        setNotice({ type: "success", text: "Peminjaman baru berhasil dicatat." });
      }
      await load();
      return true;
    } catch (error) {
      setNotice({ type: "error", text: error instanceof Error ? error.message : "Gagal menyimpan data" });
      return false;
    } finally {
      setSubmitting(false);
    }
  }

  async function handleReturn(loan: Loan) {
    setBusyId(loan.loanId);
    setNotice(null);
    try {
      await updateLoan(loan.loanId, { status: "RETURNED" });
      setNotice({ type: "success", text: `${loan.equipmentName} ditandai sudah dikembalikan.` });
      await load();
    } catch (error) {
      setNotice({ type: "error", text: error instanceof Error ? error.message : "Gagal mengubah status" });
    } finally {
      setBusyId(null);
    }
  }

  async function handleDelete() {
    if (!deleteTarget) return;
    setBusyId(deleteTarget.loanId);
    setNotice(null);
    try {
      await deleteLoan(deleteTarget.loanId);
      setNotice({ type: "success", text: "Data peminjaman berhasil dihapus." });
      if (editing?.loanId === deleteTarget.loanId) setEditing(null);
      setDeleteTarget(null);
      await load();
    } catch (error) {
      setNotice({ type: "error", text: error instanceof Error ? error.message : "Gagal menghapus data" });
      setDeleteTarget(null);
    } finally {
      setBusyId(null);
    }
  }

  return (
    <main className="container">
      <header className="header">
        <h1>Peminjaman Alat Lab</h1>
        <p>Catat siapa meminjam alat apa, kapan harus kembali, dan alat mana yang sudah dikembalikan.</p>
      </header>

      {!API_URL && (
        <div className="notice notice-error">
          Alamat API belum diatur. Isi NEXT_PUBLIC_API_URL di file .env.production lalu build ulang.
        </div>
      )}

      {notice && <div className={`notice notice-${notice.type}`}>{notice.text}</div>}

      <LoanForm editing={editing} submitting={submitting} onSubmit={handleSubmit} onCancelEdit={() => setEditing(null)} />

      <section className="card">
        <div className="list-header">
          <h2>Daftar Peminjaman</h2>
          <div className="list-tools">
            <label className="inline">
              Status
              <select value={filter} onChange={(e) => setFilter(e.target.value as LoanStatus | "ALL")}>
                <option value="ALL">Semua</option>
                <option value="BORROWED">Dipinjam</option>
                <option value="RETURNED">Dikembalikan</option>
              </select>
            </label>
            <button type="button" className="btn btn-small" onClick={load} disabled={loading}>
              Muat ulang
            </button>
          </div>
        </div>

        {loading && <p className="state">Memuat data...</p>}
        {!loading && loadError && (
          <div className="state state-error">
            <p>{loadError}</p>
            <button type="button" className="btn btn-small" onClick={load}>
              Coba lagi
            </button>
          </div>
        )}
        {!loading && !loadError && loans.length === 0 && (
          <p className="state">Belum ada data peminjaman. Catat peminjaman pertama lewat form di atas.</p>
        )}
        {!loading && !loadError && loans.length > 0 && (
          <LoanTable
            loans={loans}
            busyId={busyId}
            onReturn={handleReturn}
            onEdit={(loan) => {
              setEditing(loan);
              window.scrollTo({ top: 0, behavior: "smooth" });
            }}
            onDelete={setDeleteTarget}
          />
        )}
      </section>

      {deleteTarget && (
        <ConfirmDialog
          title="Hapus data peminjaman?"
          message={`Data peminjaman ${deleteTarget.equipmentName} atas nama ${deleteTarget.borrowerName} akan dihapus permanen.`}
          confirmLabel="Hapus"
          busy={busyId === deleteTarget.loanId}
          onConfirm={handleDelete}
          onCancel={() => setDeleteTarget(null)}
        />
      )}
    </main>
  );
}
