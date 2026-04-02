import { fireEvent, render, screen, waitFor } from "@testing-library/react";

const { getNotificationsMock, markNotificationReadMock } = vi.hoisted(() => ({
  getNotificationsMock: vi.fn(),
  markNotificationReadMock: vi.fn()
}));

vi.mock("../api/messaging", () => ({
  getNotifications: getNotificationsMock,
  markNotificationRead: markNotificationReadMock
}));

vi.mock("./dashboard/AdminDashboard", () => ({
  AdminDashboard: () => <div>Admin dashboard</div>
}));

vi.mock("./dashboard/DataQualityDashboard", () => ({
  DataQualityDashboard: () => <div>Data quality dashboard</div>
}));

vi.mock("./dashboard/FinanceDashboard", () => ({
  FinanceDashboard: () => <div>Finance dashboard</div>
}));

vi.mock("./dashboard/ReviewerDashboard", () => ({
  ReviewerDashboard: ({ roleLabel }: { roleLabel: string }) => <div>{roleLabel} dashboard</div>
}));

vi.mock("./dashboard/StudentDashboard", () => ({
  StudentDashboard: () => <div>Student dashboard</div>
}));

import { AppPortal } from "./AppPortal";
import { Role } from "../types";

function renderPortal(role: Role) {
  return render(<AppPortal token="token" role={role} username="alice" onLogout={vi.fn()} />);
}

describe("AppPortal role workflows", () => {
  beforeEach(() => {
    getNotificationsMock.mockResolvedValue({
      unread_count: 1,
      notifications: [
        {
          id: 1,
          title: "Unread notice",
          message: "Check this update",
          read: false,
          delivered_at: "2026-04-02T12:00:00Z"
        }
      ]
    });
    markNotificationReadMock.mockResolvedValue({ id: 1, read: true });
  });

  it("shows student workspace and student dashboard", async () => {
    renderPortal("STUDENT");

    expect(await screen.findByText("Student Workspace")).toBeInTheDocument();
    expect(await screen.findByText("Student dashboard")).toBeInTheDocument();
    expect(screen.queryByText("Data Quality")).not.toBeInTheDocument();
  });

  it("shows finance workspace and finance dashboard", async () => {
    renderPortal("FINANCE_CLERK");

    expect(await screen.findByText("Finance Desk")).toBeInTheDocument();
    expect(await screen.findByText("Finance dashboard")).toBeInTheDocument();
  });

  it("allows admin to switch from overview to data quality", async () => {
    renderPortal("ADMIN");

    expect(await screen.findByText("Admin dashboard")).toBeInTheDocument();

    fireEvent.click(screen.getAllByText("Data Quality")[0]);
    expect(await screen.findByText("Data quality dashboard")).toBeInTheDocument();
  });

  it("marks unread notifications as read", async () => {
    renderPortal("STUDENT");

    await screen.findByText("Student dashboard");
    fireEvent.click(screen.getByLabelText(/open notifications/i));

    const unread = await screen.findByText("Unread notice");
    fireEvent.click(unread);

    await waitFor(() => {
      expect(markNotificationReadMock).toHaveBeenCalledWith("token", 1);
    });
  });
});
