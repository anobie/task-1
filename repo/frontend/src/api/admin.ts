import { apiClient } from "./client";

export async function getOrganizations(token: string) {
  const response = await apiClient.get("/admin/organizations", {
    headers: { Authorization: `Bearer ${token}` }
  });
  return response.data as Array<{ id: number; name: string; code: string; is_active: boolean }>;
}

export async function getAuditLogs(token: string) {
  const response = await apiClient.get("/admin/audit-log?limit=10", {
    headers: { Authorization: `Bearer ${token}` }
  });
  return response.data as Array<{ id: number; action: string; entity_name: string; created_at: string }>;
}
