import { apiClient } from "./client";

function authHeader(token: string) {
  return { Authorization: `Bearer ${token}` };
}

export async function getArrears(token: string) {
  const response = await apiClient.get("/finance/arrears", {
    headers: authHeader(token)
  });
  return response.data as Array<{ student_id: number; balance: number; overdue_days: number }>;
}

type FinanceMutation = {
  student_id: number;
  amount: number;
  entry_date: string;
  instrument?: string;
  description?: string;
  reference_entry_id?: number;
};

export async function postPayment(token: string, payload: FinanceMutation) {
  const response = await apiClient.post("/finance/payments", payload, { headers: authHeader(token) });
  return response.data as { id: number; entry_type: string; amount: number };
}

export async function postPrepayment(token: string, payload: FinanceMutation) {
  const response = await apiClient.post("/finance/prepayments", payload, { headers: authHeader(token) });
  return response.data as { id: number; entry_type: string; amount: number };
}

export async function postDeposit(token: string, payload: FinanceMutation) {
  const response = await apiClient.post("/finance/deposits", payload, { headers: authHeader(token) });
  return response.data as { id: number; entry_type: string; amount: number };
}

export async function postRefund(token: string, payload: FinanceMutation) {
  const response = await apiClient.post(
    "/finance/refunds",
    {
      student_id: payload.student_id,
      amount: payload.amount,
      reference_entry_id: payload.reference_entry_id,
      description: payload.description,
      entry_date: payload.entry_date
    },
    { headers: authHeader(token) }
  );
  return response.data as { id: number; entry_type: string; amount: number };
}

export async function postMonthEndBilling(token: string, payload: FinanceMutation) {
  const response = await apiClient.post(
    "/finance/month-end-billing",
    {
      student_id: payload.student_id,
      amount: payload.amount,
      description: payload.description,
      entry_date: payload.entry_date
    },
    { headers: authHeader(token) }
  );
  return response.data as { id: number; entry_type: string; amount: number };
}

export async function importReconciliationCsv(token: string, csvText: string) {
  const form = new FormData();
  const blob = new Blob([csvText], { type: "text/csv" });
  form.append("file", blob, "statement.csv");
  const response = await apiClient.post("/finance/reconciliation/import", form, {
    headers: authHeader(token)
  });
  return response.data as { import_id: string; matched_total: number; unmatched_total: number };
}
