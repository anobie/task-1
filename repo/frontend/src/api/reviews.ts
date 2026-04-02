import { apiClient } from "./client";

function authHeader(token: string) {
  return { Authorization: `Bearer ${token}` };
}

export async function getReviewAssignments(token: string, roundId: number) {
  const response = await apiClient.get(`/reviews/rounds/${roundId}/assignments`, {
    headers: authHeader(token)
  });
  return response.data as Array<{ id: number; reviewer_id: number; student_id: number | null; section_id: number; round_id: number }>;
}

export async function getOutliers(token: string, roundId: number) {
  const response = await apiClient.get(`/reviews/rounds/${roundId}/outliers`, {
    headers: authHeader(token)
  });
  return response.data as Array<{ id: number; deviation: number; resolved: boolean }>;
}

export async function submitScore(token: string, payload: { assignment_id: number; criterion_scores: Record<string, number>; comment?: string }) {
  const response = await apiClient.post("/reviews/scores", payload, {
    headers: authHeader(token)
  });
  return response.data as { id: number; assignment_id: number; total_score: number; submitted_at: string };
}

export async function createRecheck(token: string, payload: { round_id: number; student_id: number; section_id: number; reason: string }) {
  const response = await apiClient.post("/reviews/rechecks", payload, {
    headers: authHeader(token)
  });
  return response.data as { id: number; status: string };
}

export async function manualAssign(token: string, roundId: number, reviewerId: number, studentId: number) {
  const response = await apiClient.post(
    `/reviews/rounds/${roundId}/assignments/manual`,
    { reviewer_id: reviewerId, student_id: studentId },
    { headers: authHeader(token) }
  );
  return response.data as { id: number };
}

export async function autoAssign(token: string, roundId: number, studentIds: number[], reviewersPerStudent: number) {
  const response = await apiClient.post(
    `/reviews/rounds/${roundId}/assignments/auto`,
    { student_ids: studentIds, reviewers_per_student: reviewersPerStudent },
    { headers: authHeader(token) }
  );
  return response.data as { created_assignments: number };
}

export async function assignRecheck(token: string, recheckId: number, reviewerId: number) {
  const response = await apiClient.post(
    `/reviews/rechecks/${recheckId}/assign`,
    { reviewer_id: reviewerId },
    { headers: authHeader(token) }
  );
  return response.data as { message: string };
}
