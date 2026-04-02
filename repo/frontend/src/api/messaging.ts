import { apiClient } from "./client";

export async function getNotifications(token: string) {
  const response = await apiClient.get("/messaging/notifications", {
    headers: { Authorization: `Bearer ${token}` }
  });
  return response.data as {
    unread_count: number;
    notifications: Array<{ id: number; title: string; message: string; read: boolean; delivered_at: string }>;
  };
}

export async function markNotificationRead(token: string, notificationId: number) {
  const response = await apiClient.patch(
    `/messaging/notifications/${notificationId}/read`,
    {},
    { headers: { Authorization: `Bearer ${token}` } }
  );
  return response.data as { id: number; read: boolean };
}
