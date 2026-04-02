import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";

import { login as loginRequest, logout as logoutRequest, me } from "../api/auth";
import { UserProfile } from "../types";

const TOKEN_KEY = "cems_token";

type AuthContextValue = {
  token: string | null;
  user: UserProfile | null;
  isAuthenticated: boolean;
  isBootstrapping: boolean;
  login: (username: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  refreshMe: () => Promise<void>;
};

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [token, setToken] = useState<string | null>(null);
  const [user, setUser] = useState<UserProfile | null>(null);
  const [isBootstrapping, setIsBootstrapping] = useState(true);

  const refreshMe = useCallback(async () => {
    if (!token) {
      setUser(null);
      return;
    }
    const profile = await me(token);
    setUser(profile);
  }, [token]);

  useEffect(() => {
    const stored = localStorage.getItem(TOKEN_KEY);
    if (!stored) {
      setIsBootstrapping(false);
      return;
    }

    setToken(stored);
  }, []);

  useEffect(() => {
    if (!token) {
      setUser(null);
      setIsBootstrapping(false);
      return;
    }

    const run = async () => {
      try {
        const profile = await me(token);
        setUser(profile);
      } catch {
        localStorage.removeItem(TOKEN_KEY);
        setToken(null);
        setUser(null);
      } finally {
        setIsBootstrapping(false);
      }
    };

    void run();
  }, [token]);

  const login = useCallback(async (username: string, password: string) => {
    const result = await loginRequest(username, password);
    localStorage.setItem(TOKEN_KEY, result.token);
    setToken(result.token);
    const profile = await me(result.token);
    setUser(profile);
  }, []);

  const logout = useCallback(async () => {
    if (token) {
      try {
        await logoutRequest(token);
      } catch {
        // ignore and continue with local cleanup
      }
    }
    localStorage.removeItem(TOKEN_KEY);
    setToken(null);
    setUser(null);
  }, [token]);

  const value = useMemo<AuthContextValue>(
    () => ({
      token,
      user,
      isAuthenticated: Boolean(token && user),
      isBootstrapping,
      login,
      logout,
      refreshMe
    }),
    [token, user, isBootstrapping, login, logout, refreshMe]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error("useAuth must be used within AuthProvider");
  }
  return ctx;
}
