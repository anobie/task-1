import { UserProfile } from "../types";
import { apiClient } from "./client";

export type LoginResponse = {
  token: string;
  idle_expires_at: string;
  absolute_expires_at: string;
};

export async function login(username: string, password: string): Promise<LoginResponse> {
  const response = await apiClient.post<LoginResponse>("/auth/login", { username, password });
  return response.data;
}

export async function me(token: string): Promise<UserProfile> {
  const response = await apiClient.get<UserProfile>("/auth/me", {
    headers: { Authorization: `Bearer ${token}` }
  });
  return response.data;
}

export async function logout(token: string): Promise<void> {
  await apiClient.post(
    "/auth/logout",
    {},
    {
      headers: { Authorization: `Bearer ${token}` }
    }
  );
}
