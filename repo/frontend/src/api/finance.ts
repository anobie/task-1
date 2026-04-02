import { apiClient } from "./client";

export async function getArrears(token: string) {
  const response = await apiClient.get("/finance/arrears", {
    headers: { Authorization: `Bearer ${token}` }
  });
  return response.data as Array<{ student_id: number; balance: number; overdue_days: number }>;
}
