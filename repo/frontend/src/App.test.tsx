import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";

import { App } from "./App";

type MockAuth = {
  user: { role: "ADMIN"; username: string } | null;
  token: string | null;
  isAuthenticated: boolean;
  isBootstrapping: boolean;
  logout: () => Promise<void>;
};

const authState: MockAuth = {
  user: null,
  token: null,
  isAuthenticated: false,
  isBootstrapping: false,
  logout: async () => undefined
};

vi.mock("./contexts/AuthContext", () => ({
  useAuth: () => authState
}));

vi.mock("./pages/LoginPage", () => ({
  LoginPage: () => <div>Login Page</div>
}));

vi.mock("./pages/AppPortal", () => ({
  AppPortal: ({ username }: { username: string }) => <div>App Portal {username}</div>
}));

describe("App route security", () => {
  it("redirects unauthenticated /app users to /login", async () => {
    authState.user = null;
    authState.token = null;
    authState.isAuthenticated = false;
    authState.isBootstrapping = false;

    render(
      <MemoryRouter initialEntries={["/app"]}>
        <App />
      </MemoryRouter>
    );

    expect(await screen.findByText("Login Page")).toBeInTheDocument();
  });

  it("redirects authenticated /login users to /app", async () => {
    authState.user = { role: "ADMIN", username: "alice" };
    authState.token = "token";
    authState.isAuthenticated = true;
    authState.isBootstrapping = false;

    render(
      <MemoryRouter initialEntries={["/login"]}>
        <App />
      </MemoryRouter>
    );

    expect(await screen.findByText("App Portal alice")).toBeInTheDocument();
  });
});
