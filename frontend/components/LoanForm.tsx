"use client";

import { FormEvent, useEffect, useState } from "react";
import { todayString } from "@/lib/format";
import type { Loan, LoanInput } from "@/lib/types";

interface Props {
  editing: Loan | null;
  submitting: boolean;
  onSubmit: (values: LoanInput) => Promise<boolean>;
  onCancelEdit: () => void;
}

interface FormState {
  borrowerName: string;
  borrowerNim: string;
  equipmentName: string;
  quantity: string;
  loanDate: string;
  dueDate: string;
  notes: string;
}

const EMPTY: FormState = {
  borrowerName: "",
  borrowerNim: "",
  equipmentName: "",
  quantity: "1",
  loanDate: "",
  dueDate: "",
  notes: "",
};

function fromLoan(loan: Loan): FormState {
  return {
    borrowerName: loan.borrowerName,
    borrowerNim: loan.borrowerNim,
    equipmentName: loan.equipmentName,
    quantity: String(loan.quantity),
    loanDate: loan.loanDate,
    dueDate: loan.dueDate,
    notes: loan.notes ?? "",
  };
}

function validate(form: FormState): Partial<Record<keyof FormState, string>> {
  const errors: Partial<Record<keyof FormState, string>> = {};
  if (form.borrowerName.trim().length < 2) errors.borrowerName = "Nama minimal 2 karakter";
  if (!/^[0-9A-Za-z/]{5,30}$/.test(form.borrowerNim)) errors.borrowerNim = "NIM hanya boleh angka, huruf, dan garis miring (5 sampai 30 karakter)";
  if (form.equipmentName.trim().length < 2) errors.equipmentName = "Nama alat minimal 2 karakter";
  const quantity = Number(form.quantity);
  if (!Number.isInteger(quantity) || quantity < 1 || quantity > 100) errors.quantity = "Jumlah harus bilangan bulat 1 sampai 100";
  if (!form.loanDate) errors.loanDate = "Tanggal pinjam wajib diisi";
  if (!form.dueDate) errors.dueDate = "Tanggal jatuh tempo wajib diisi";
  if (form.loanDate && form.dueDate && form.dueDate < form.loanDate) errors.dueDate = "Jatuh tempo tidak boleh lebih awal dari tanggal pinjam";
  if (form.notes.length > 255) errors.notes = "Catatan maksimal 255 karakter";
  return errors;
}

export default function LoanForm({ editing, submitting, onSubmit, onCancelEdit }: Props) {
  const [form, setForm] = useState<FormState>(EMPTY);
  const [errors, setErrors] = useState<Partial<Record<keyof FormState, string>>>({});

  // Isi form saat mode edit dibuka. Untuk data baru, tanggal diisi dengan hari ini.
  useEffect(() => {
    if (editing) {
      setForm(fromLoan(editing));
    } else {
      const today = todayString();
      setForm({ ...EMPTY, loanDate: today, dueDate: today });
    }
    setErrors({});
  }, [editing]);

  function change(field: keyof FormState, value: string) {
    setForm((current) => ({ ...current, [field]: value }));
  }

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    const found = validate(form);
    setErrors(found);
    if (Object.keys(found).length > 0) return;

    const saved = await onSubmit({
      borrowerName: form.borrowerName.trim(),
      borrowerNim: form.borrowerNim.trim(),
      equipmentName: form.equipmentName.trim(),
      quantity: Number(form.quantity),
      loanDate: form.loanDate,
      dueDate: form.dueDate,
      // Saat edit, catatan kosong dikirim sebagai null agar terhapus di server
      notes: form.notes.trim() === "" ? (editing ? null : undefined) : form.notes.trim(),
    });

    // Setelah peminjaman baru tersimpan, kosongkan form untuk input berikutnya
    if (saved && !editing) {
      const today = todayString();
      setForm({ ...EMPTY, loanDate: today, dueDate: today });
    }
  }

  return (
    <form className="card form" onSubmit={handleSubmit} noValidate>
      <h2>{editing ? "Ubah Data Peminjaman" : "Catat Peminjaman Baru"}</h2>

      <div className="grid">
        <label>
          Nama peminjam
          <input value={form.borrowerName} onChange={(e) => change("borrowerName", e.target.value)} placeholder="Contoh: Sophie" />
          {errors.borrowerName && <span className="error">{errors.borrowerName}</span>}
        </label>

        <label>
          NIM
          <input value={form.borrowerNim} onChange={(e) => change("borrowerNim", e.target.value)} placeholder="24/540586/TK/60019" />
          {errors.borrowerNim && <span className="error">{errors.borrowerNim}</span>}
        </label>

        <label>
          Nama alat
          <input value={form.equipmentName} onChange={(e) => change("equipmentName", e.target.value)} placeholder="Contoh: ESP32 DevKit" />
          {errors.equipmentName && <span className="error">{errors.equipmentName}</span>}
        </label>

        <label>
          Jumlah
          <input type="number" min={1} max={100} value={form.quantity} onChange={(e) => change("quantity", e.target.value)} />
          {errors.quantity && <span className="error">{errors.quantity}</span>}
        </label>

        <label>
          Tanggal pinjam
          <input type="date" value={form.loanDate} onChange={(e) => change("loanDate", e.target.value)} />
          {errors.loanDate && <span className="error">{errors.loanDate}</span>}
        </label>

        <label>
          Jatuh tempo
          <input type="date" value={form.dueDate} onChange={(e) => change("dueDate", e.target.value)} />
          {errors.dueDate && <span className="error">{errors.dueDate}</span>}
        </label>
      </div>

      <label>
        Catatan (opsional)
        <textarea rows={2} value={form.notes} onChange={(e) => change("notes", e.target.value)} />
        {errors.notes && <span className="error">{errors.notes}</span>}
      </label>

      <div className="actions">
        {editing && (
          <button type="button" className="btn" onClick={onCancelEdit} disabled={submitting}>
            Batal
          </button>
        )}
        <button type="submit" className="btn btn-primary" disabled={submitting}>
          {submitting ? "Menyimpan..." : editing ? "Simpan Perubahan" : "Simpan Peminjaman"}
        </button>
      </div>
    </form>
  );
}
