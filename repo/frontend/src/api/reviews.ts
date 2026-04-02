import { apiClient } from "./client";

export async function getReviewAssignments(token: string, roundId: number) {
  const response = await apiClient.get(`/reviews/rounds/${roundId}/assignments`, {
    headers: { Authorization: `Bearer ${token}` }
  });
  return response.data as Array<{ id: number; reviewer_id: number; student_id: number | null; section_id: number }>;
}

export async function getOutliers(token: string, roundId: number) {
  const response = await apiClient.get(`/reviews/rounds/${roundId}/outliers`, {
    headers: { Authorization: `Bearer ${token}` }
  });
  return response.data as Array<{ id: number; deviation: number; resolved: boolean }>;
}
