import { lazy, Suspense } from "react";

import { Box, CircularProgress } from "@mui/material";
import { Navigate, Route, Routes, useNavigate } from "react-router-dom";

import { useAuth } from "./contexts/AuthContext";

const AppPortal = lazy(async () => import("./pages/AppPortal").then((module) => ({ default: module.AppPortal })));
const LoginPage = lazy(async () => import("./pages/LoginPage").then((module) => ({ default: module.LoginPage })));

function CenterLoader() {
  return (
    <Box sx={{ minHeight: "100vh", display: "flex", alignItems: "center", justifyContent: "center" }}>
      <CircularProgress />
    </Box>
  );
}

function ProtectedApp() {
  const { user, token, logout } = useAuth();
  if (!user || !token) {
    return <Navigate to="/login" replace />;
  }
  return (
    <Suspense fallback={<CenterLoader />}>
      <AppPortal token={token} role={user.role} username={user.username} onLogout={logout} />
    </Suspense>
  );
}

function LoginRoute() {
  const navigate = useNavigate();
  const { isAuthenticated } = useAuth();
  if (isAuthenticated) {
    return <Navigate to="/app" replace />;
  }
  return (
    <Suspense fallback={<CenterLoader />}>
      <LoginPage onSuccess={() => navigate("/app", { replace: true })} />
    </Suspense>
  );
}

export function App() {
  const { isBootstrapping } = useAuth();
  if (isBootstrapping) {
    return <CenterLoader />;
  }

  return (
    <Routes>
      <Route path="/login" element={<LoginRoute />} />
      <Route path="/app" element={<ProtectedApp />} />
      <Route path="*" element={<Navigate to="/app" replace />} />
    </Routes>
  );
}
