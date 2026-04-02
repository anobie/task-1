import { apiClient } from "./client";

export async function getQuarantine(token: string) {
  const response = await apiClient.get("/data-quality/quarantine?limit=20", {
    headers: { Authorization: `Bearer ${token}` }
  });
  return response.data as Array<{ id: number; entity_type: string; quality_score: number; status: string }>;
}

export async function getQualityReport(token: string) {
  const response = await apiClient.get("/data-quality/report", {
    headers: { Authorization: `Bearer ${token}` }
  });
  return response.data as Array<{ entity_type: string; open_items: number; avg_quality_score: number }>;
}
