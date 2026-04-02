export type Role = "STUDENT" | "INSTRUCTOR" | "REVIEWER" | "FINANCE_CLERK" | "ADMIN";

export type UserProfile = {
  id: number;
  username: string;
  role: Role;
  session_idle_expires_at: string;
  session_absolute_expires_at: string;
};
