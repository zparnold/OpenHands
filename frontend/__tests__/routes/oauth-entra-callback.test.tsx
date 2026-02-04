import { render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { createMemoryRouter, RouterProvider } from "react-router";
import OAuthEntraCallback from "#/routes/oauth-entra-callback";
import { completeEntraPkceLogin } from "#/hooks/use-entra-pkce-login";
import * as localStorage from "#/utils/local-storage";

vi.mock("#/hooks/use-entra-pkce-login", () => ({
  completeEntraPkceLogin: vi.fn(),
}));
vi.mock("#/utils/local-storage", async (importOriginal) => {
  const actual = await importOriginal<typeof localStorage>();
  return {
    ...actual,
    setAccessToken: vi.fn(),
    setLoginMethod: vi.fn(),
  };
});

const VALID_STATE =
  "eyJjb2RlVmVyaWZpZXIiOiJ0ZXN0LXZlcmlmaWVyIiwicmV0dXJuVG8iOiIvIn0";

describe("OAuthEntraCallback", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    sessionStorage.removeItem("entra_pkce_exchanging");
  });

  it("shows loading spinner initially", () => {
    vi.mocked(completeEntraPkceLogin).mockImplementation(
      () => new Promise(() => {}),
    );

    const router = createMemoryRouter(
      [
        {
          path: "/oauth/entra/callback",
          element: <OAuthEntraCallback />,
        },
      ],
      {
        initialEntries: [
          `/oauth/entra/callback?code=test-code&state=${VALID_STATE}`,
        ],
      },
    );

    render(<RouterProvider router={router} />);

    expect(
      document.querySelector(".animate-spin.rounded-full"),
    ).toBeInTheDocument();
  });

  it("exchanges code for token and stores it on success", async () => {
    vi.mocked(completeEntraPkceLogin).mockResolvedValue({
      accessToken: "mock-token",
      returnTo: "/",
    });

    const router = createMemoryRouter(
      [
        {
          path: "/oauth/entra/callback",
          element: <OAuthEntraCallback />,
        },
      ],
      {
        initialEntries: [
          `/oauth/entra/callback?code=test-code&state=${VALID_STATE}`,
        ],
      },
    );

    render(<RouterProvider router={router} />);

    await waitFor(() => {
      expect(completeEntraPkceLogin).toHaveBeenCalledWith(
        "test-code",
        VALID_STATE,
      );
    });

    await waitFor(() => {
      expect(localStorage.setAccessToken).toHaveBeenCalledWith("mock-token");
      expect(localStorage.setLoginMethod).toHaveBeenCalledWith("enterprise_sso");
    });
  });

  it("shows error and return link when token exchange fails", async () => {
    vi.mocked(completeEntraPkceLogin).mockRejectedValue(
      new Error("Token exchange failed"),
    );

    const router = createMemoryRouter(
      [
        {
          path: "/oauth/entra/callback",
          element: <OAuthEntraCallback />,
        },
      ],
      {
        initialEntries: [
          `/oauth/entra/callback?code=invalid-code&state=${VALID_STATE}`,
        ],
      },
    );

    render(<RouterProvider router={router} />);

    await waitFor(() => {
      expect(
        screen.getByText(/Token exchange failed|failed/i),
      ).toBeInTheDocument();
    });

    // i18n mock returns the key as-is (INVITE$RETURN_TO_LOGIN)
    expect(
      screen.getByRole("link", { name: "INVITE$RETURN_TO_LOGIN" }),
    ).toBeInTheDocument();
  });

  it("shows error when no code in URL", async () => {
    const router = createMemoryRouter(
      [
        {
          path: "/oauth/entra/callback",
          element: <OAuthEntraCallback />,
        },
      ],
      {
        initialEntries: ["/oauth/entra/callback"],
      },
    );

    render(<RouterProvider router={router} />);

    await waitFor(() => {
      expect(
        screen.getByText(/No authorization code/i),
      ).toBeInTheDocument();
    });
  });
});
