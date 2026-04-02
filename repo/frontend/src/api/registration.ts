import { apiClient } from "./client";

function authHeader(token: string) {
  return { Authorization: `Bearer ${token}` };
}

function idempotencyHeader() {
  return { "Idempotency-Key": `${Date.now()}-${Math.random().toString(16).slice(2)}` };
}

export async function getCourses(token: string) {
  const response = await apiClient.get("/courses", {
    headers: authHeader(token)
  });
  return response.data as Array<{ id: number; code: string; title: string; credits: number; available_seats: number }>;
}

export async function getCourseDetail(token: string, courseId: number) {
  const response = await apiClient.get(`/courses/${courseId}`, {
    headers: authHeader(token)
  });
  return response.data as {
    id: number;
    code: string;
    title: string;
    credits: number;
    prerequisites: string[];
    sections: Array<{ id: number; code: string; capacity: number; term_id: number }>;
  };
}

export async function getEligibility(token: string, courseId: number, sectionId: number) {
  const response = await apiClient.get(`/courses/${courseId}/sections/${sectionId}/eligibility`, {
    headers: authHeader(token)
  });
  return response.data as { eligible: boolean; reasons: string[] };
}

export async function getRegistrationStatus(token: string) {
  const response = await apiClient.get("/registration/status", {
    headers: authHeader(token)
  });
  return response.data as Array<{ section_id: number; course_code: string; status: string }>;
}

export async function getRegistrationHistory(token: string) {
  const response = await apiClient.get("/registration/history", {
    headers: authHeader(token)
  });
  return response.data as Array<{ id: number; event_type: string; details: string | null; created_at: string }>;
}

export async function enrollInSection(token: string, sectionId: number) {
  const response = await apiClient.post(
    "/registration/enroll",
    { section_id: sectionId },
    { headers: { ...authHeader(token), ...idempotencyHeader() } }
  );
  return response.data as { status: string; section_id: number };
}

export async function joinWaitlist(token: string, sectionId: number) {
  const response = await apiClient.post(
    "/registration/waitlist",
    { section_id: sectionId },
    { headers: authHeader(token) }
  );
  return response.data as { status: string; section_id: number; priority?: number };
}

export async function dropSection(token: string, sectionId: number) {
  const response = await apiClient.post(
    "/registration/drop",
    { section_id: sectionId },
    { headers: { ...authHeader(token), ...idempotencyHeader() } }
  );
  return response.data as { status: string; section_id: number };
}
