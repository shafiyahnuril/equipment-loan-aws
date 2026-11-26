"""Model data (Pydantic) untuk entity Loan beserta aturan validasinya."""

from datetime import date
from enum import Enum
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

# NIM boleh berisi angka, huruf, dan garis miring. Contoh: 24/540586/TK/60019
NIM_PATTERN = r"^[0-9A-Za-z/]{5,30}$"


class LoanStatus(str, Enum):
    BORROWED = "BORROWED"
    RETURNED = "RETURNED"


def _strip(value: Optional[str]) -> Optional[str]:
    return value.strip() if isinstance(value, str) else value


class LoanCreate(BaseModel):
    """Data yang dikirim client saat membuat peminjaman baru."""

    model_config = ConfigDict(extra="forbid")

    borrowerName: str = Field(min_length=2, max_length=100)
    borrowerNim: str = Field(pattern=NIM_PATTERN)
    equipmentName: str = Field(min_length=2, max_length=100)
    quantity: int = Field(ge=1, le=100)
    loanDate: date
    dueDate: date
    notes: Optional[str] = Field(default=None, max_length=255)

    @field_validator("borrowerName", "equipmentName", "notes", mode="before")
    @classmethod
    def strip_text(cls, value):
        return _strip(value)

    @model_validator(mode="after")
    def check_dates(self):
        if self.dueDate < self.loanDate:
            raise ValueError("dueDate tidak boleh lebih awal dari loanDate")
        return self


class LoanUpdate(BaseModel):
    """Data untuk mengubah peminjaman. Semua field bersifat opsional."""

    model_config = ConfigDict(extra="forbid")

    borrowerName: Optional[str] = Field(default=None, min_length=2, max_length=100)
    borrowerNim: Optional[str] = Field(default=None, pattern=NIM_PATTERN)
    equipmentName: Optional[str] = Field(default=None, min_length=2, max_length=100)
    quantity: Optional[int] = Field(default=None, ge=1, le=100)
    loanDate: Optional[date] = None
    dueDate: Optional[date] = None
    notes: Optional[str] = Field(default=None, max_length=255)
    status: Optional[LoanStatus] = None

    @field_validator("borrowerName", "equipmentName", "notes", mode="before")
    @classmethod
    def strip_text(cls, value):
        return _strip(value)

    @model_validator(mode="after")
    def check_not_empty(self):
        if not self.model_fields_set:
            raise ValueError("minimal satu field harus diisi")
        if self.loanDate and self.dueDate and self.dueDate < self.loanDate:
            raise ValueError("dueDate tidak boleh lebih awal dari loanDate")
        return self


class Loan(BaseModel):
    """Bentuk data peminjaman yang dikembalikan oleh API."""

    loanId: str
    borrowerName: str
    borrowerNim: str
    equipmentName: str
    quantity: int
    loanDate: str
    dueDate: str
    status: LoanStatus
    notes: Optional[str] = None
    returnedAt: Optional[str] = None
    createdAt: str
    updatedAt: str
