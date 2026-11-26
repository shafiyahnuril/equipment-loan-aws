export type LoanStatus = "BORROWED" | "RETURNED";

export interface Loan {
  loanId: string;
  borrowerName: string;
  borrowerNim: string;
  equipmentName: string;
  quantity: number;
  loanDate: string;
  dueDate: string;
  status: LoanStatus;
  notes?: string | null;
  returnedAt?: string | null;
  createdAt: string;
  updatedAt: string;
}

export interface LoanInput {
  borrowerName: string;
  borrowerNim: string;
  equipmentName: string;
  quantity: number;
  loanDate: string;
  dueDate: string;
  notes?: string | null;
}

export type LoanUpdate = Partial<LoanInput> & { status?: LoanStatus };
