import { apiClient } from "./client";

export async function getCourses(token: string) {
  const response = await apiClient.get("/courses", {
    headers: { Authorization: `Bearer ${token}` }
  });
  return response.data as Array<{ id: number; code: string; title: string; credits: number; available_seats: number }>;
}

export async function getRegistrationStatus(token: string) {
  const response = await apiClient.get("/registration/status", {
    headers: { Authorization: `Bearer ${token}` }
  });
  return response.data as Array<{ section_id: number; course_code: string; status: string }>;
}

export async function getRegistrationHistory(token: string) {
  const response = await apiClient.get("/registration/history", {
    headers: { Authorization: `Bearer ${token}` }
  });
  return response.data as Array<{ id: number; event_type: string; details: string | null; created_at: string }>;
}
