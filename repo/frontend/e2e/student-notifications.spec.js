import { expect, test } from "@playwright/test";

test("student login and notification read journey", async ({ page }) => {
  const state = {
    notifications: [
      {
        id: 21,
        title: "Unread notice",
        message: "Round update available",
        read: false,
        delivered_at: "2026-04-02T12:00:00Z"
      }
    ]
  };

  await page.route("**/api/v1/auth/login", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        token: "e2e-token",
        idle_expires_at: "2026-04-02T23:00:00Z",
        absolute_expires_at: "2026-04-03T23:00:00Z"
      })
    });
  });

  await page.route("**/api/v1/auth/me", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        id: 100,
        username: "student-e2e",
        role: "STUDENT",
        session_idle_expires_at: "2026-04-02T23:00:00Z",
        session_absolute_expires_at: "2026-04-03T23:00:00Z"
      })
    });
  });

  await page.route("**/api/v1/courses", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify([{ id: 1, code: "CSE101", title: "Intro", credits: 3, available_seats: 10 }])
    });
  });

  await page.route("**/api/v1/registration/status", async (route) => {
    await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify([]) });
  });

  await page.route("**/api/v1/registration/history", async (route) => {
    await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify([]) });
  });

  await page.route("**/api/v1/messaging/notifications", async (route) => {
    const unread = state.notifications.filter((item) => !item.read).length;
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ unread_count: unread, notifications: state.notifications })
    });
  });

  await page.route("**/api/v1/messaging/notifications/*/read", async (route) => {
    const id = Number(route.request().url().split("/").slice(-2)[0]);
    state.notifications = state.notifications.map((item) => (item.id === id ? { ...item, read: true } : item));
    await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ id, read: true }) });
  });

  await page.goto("/login");

  await page.getByLabel("Username").fill("student-e2e");
  await page.getByLabel("Password").fill("StudentPassword1!");
  await page.getByRole("button", { name: "Sign In" }).click();

  await expect(page).toHaveURL(/\/app$/);
  await expect(page.getByText("Student Workspace")).toBeVisible();

  await page.getByRole("button", { name: "1" }).first().click();
  await expect(page.getByText("Unread notice")).toBeVisible();
  await page.getByText("Unread notice").click();

  await expect.poll(() => state.notifications[0].read).toBe(true);
});
