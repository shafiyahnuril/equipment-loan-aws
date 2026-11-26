"""Endpoint REST untuk resource /loans dan /health."""

import logging
from typing import Annotated, List, Optional

from fastapi import APIRouter, HTTPException, Path, Query, Response, status
from fastapi.responses import JSONResponse

from . import repository
from .schemas import Loan, LoanCreate, LoanStatus, LoanUpdate

logger = logging.getLogger("equipment-loan")

router = APIRouter()

LoanId = Annotated[
    str,
    Path(description="ID peminjaman (UUID)", pattern=r"^[0-9a-fA-F-]{36}$"),
]


@router.get("/health", tags=["Health"], summary="Cek koneksi Lambda ke penyimpanan data")
def health():
    try:
        info = repository.ping()
    except repository.StorageError:
        logger.exception("Health check gagal")
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"status": "error", "detail": "Tidak bisa terhubung ke penyimpanan data"},
        )
    return {"status": "ok", **info}


@router.post(
    "/loans",
    response_model=Loan,
    status_code=status.HTTP_201_CREATED,
    tags=["Loans"],
    summary="Catat peminjaman baru",
)
def create_loan(payload: LoanCreate):
    data = payload.model_dump(mode="json")
    return repository.create_loan(data)


@router.get(
    "/loans",
    response_model=List[Loan],
    tags=["Loans"],
    summary="Ambil daftar semua peminjaman",
)
def list_loans(
    status_filter: Annotated[
        Optional[LoanStatus],
        Query(alias="status", description="Filter berdasarkan status"),
    ] = None,
):
    return repository.list_loans(status_filter.value if status_filter else None)


@router.get(
    "/loans/{loan_id}",
    response_model=Loan,
    tags=["Loans"],
    summary="Ambil satu peminjaman",
)
def get_loan(loan_id: LoanId):
    loan = repository.get_loan(loan_id)
    if loan is None:
        raise HTTPException(status_code=404, detail="Data peminjaman tidak ditemukan")
    return loan


@router.put(
    "/loans/{loan_id}",
    response_model=Loan,
    tags=["Loans"],
    summary="Ubah data peminjaman atau tandai sudah dikembalikan",
)
def update_loan(loan_id: LoanId, payload: LoanUpdate):
    changes = payload.model_dump(mode="json", exclude_unset=True)

    # Hanya notes yang boleh dikosongkan. Field lain yang bernilai null diabaikan.
    changes = {k: v for k, v in changes.items() if v is not None or k == "notes"}
    if not changes:
        raise HTTPException(status_code=422, detail="Tidak ada perubahan yang valid")

    current = repository.get_loan(loan_id)
    if current is None:
        raise HTTPException(status_code=404, detail="Data peminjaman tidak ditemukan")

    # Validasi tanggal harus memperhitungkan nilai lama jika hanya satu tanggal yang diubah
    loan_date = changes.get("loanDate", current["loanDate"])
    due_date = changes.get("dueDate", current["dueDate"])
    if due_date < loan_date:
        raise HTTPException(
            status_code=422,
            detail="dueDate tidak boleh lebih awal dari loanDate",
        )

    # returnedAt mengikuti status
    new_status = changes.get("status")
    if new_status == LoanStatus.RETURNED.value and current["status"] != "RETURNED":
        changes["returnedAt"] = repository.now_iso()
    elif new_status == LoanStatus.BORROWED.value:
        changes["returnedAt"] = None

    updated = repository.update_loan(loan_id, changes)
    if updated is None:
        raise HTTPException(status_code=404, detail="Data peminjaman tidak ditemukan")
    return updated


@router.delete(
    "/loans/{loan_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["Loans"],
    summary="Hapus data peminjaman",
)
def delete_loan(loan_id: LoanId):
    if not repository.delete_loan(loan_id):
        raise HTTPException(status_code=404, detail="Data peminjaman tidak ditemukan")
    return Response(status_code=status.HTTP_204_NO_CONTENT)
