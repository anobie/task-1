import { lazy, Suspense, useMemo, useState } from "react";

import { getNotifications, markNotificationRead } from "../api/messaging";
import { AppShell } from "../components/AppShell";
import { NotificationsDrawer } from "../components/NotificationsDrawer";
import { useAsyncResource } from "../hooks/useAsyncResource";
import { Role } from "../types";
import { LoadingBlock } from "../components/StateBlock";

const AdminDashboard = lazy(async () => import("./dashboard/AdminDashboard").then((module) => ({ default: module.AdminDashboard })));
const DataQualityDashboard = lazy(async () => import("./dashboard/DataQualityDashboard").then((module) => ({ default: module.DataQualityDashboard })));
const FinanceDashboard = lazy(async () => import("./dashboard/FinanceDashboard").then((module) => ({ default: module.FinanceDashboard })));
const ReviewerDashboard = lazy(async () => import("./dashboard/ReviewerDashboard").then((module) => ({ default: module.ReviewerDashboard })));
const StudentDashboard = lazy(async () => import("./dashboard/StudentDashboard").then((module) => ({ default: module.StudentDashboard })));

type AppPortalProps = {
  token: string;
  role: Role;
  username: string;
  onLogout: () => Promise<void>;
};

type ViewKey = "overview" | "data-quality";

export function AppPortal({ token, role, username, onLogout }: AppPortalProps) {
  const [view, setView] = useState<ViewKey>("overview");
  const [notifOpen, setNotifOpen] = useState(false);

  const notifications = useAsyncResource(() => getNotifications(token), [token]);

  const roleTitle = useMemo(() => {
    if (role === "ADMIN") {
      return "Administrator Dashboard";
    }
    if (role === "STUDENT") {
      return "Student Workspace";
    }
    if (role === "INSTRUCTOR") {
      return "Instructor Workbench";
    }
    if (role === "REVIEWER") {
      return "Reviewer Workbench";
    }
    return "Finance Desk";
  }, [role]);

  const navItems =
    role === "ADMIN"
      ? [
          { label: "Overview", active: view === "overview", onClick: () => setView("overview") },
          { label: "Data Quality", active: view === "data-quality", onClick: () => setView("data-quality") }
        ]
      : [{ label: "Overview", active: true, onClick: () => setView("overview") }];

  const handleMarkRead = async (id: number) => {
    await markNotificationRead(token, id);
    await notifications.reload();
  };

  const renderOverview = () => {
    if (role === "ADMIN") {
      if (view === "data-quality") {
        return <DataQualityDashboard token={token} />;
      }
      return <AdminDashboard token={token} />;
    }
    if (role === "STUDENT") {
      return <StudentDashboard token={token} />;
    }
    if (role === "REVIEWER") {
      return <ReviewerDashboard token={token} roleLabel="Reviewer" />;
    }
    if (role === "INSTRUCTOR") {
      return <ReviewerDashboard token={token} roleLabel="Instructor" />;
    }
    return <FinanceDashboard token={token} />;
  };

  return (
    <>
      <AppShell
        title={roleTitle}
        subtitle={`Signed in as ${username}`}
        navItems={navItems}
        unreadCount={notifications.data?.unread_count ?? 0}
        onNotificationsClick={() => setNotifOpen(true)}
        onLogout={() => {
          void onLogout();
        }}
      >
        <Suspense fallback={<LoadingBlock label="Loading workspace" />}>
          {renderOverview()}
        </Suspense>
      </AppShell>
      <NotificationsDrawer
        open={notifOpen}
        onClose={() => setNotifOpen(false)}
        items={notifications.data?.notifications ?? []}
        onMarkRead={(id) => {
          void handleMarkRead(id);
        }}
      />
    </>
  );
}
