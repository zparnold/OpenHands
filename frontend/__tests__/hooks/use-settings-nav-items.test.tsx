import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { renderHook, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { SAAS_NAV_ITEMS, OSS_NAV_ITEMS } from "#/constants/settings-nav";
import OptionService from "#/api/option-service/option-service.api";
import { useSettingsNavItems } from "#/hooks/use-settings-nav-items";

const queryClient = new QueryClient();
const wrapper = ({ children }: { children: React.ReactNode }) => (
  <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
);

const mockConfig = (
  appMode: "saas" | "oss",
  options?: { hideLlmSettings?: boolean; enableBilling?: boolean },
) => {
  const { hideLlmSettings = false, enableBilling = false } = options ?? {};
  vi.spyOn(OptionService, "getConfig").mockResolvedValue({
    app_mode: appMode,
    feature_flags: {
      hide_llm_settings: hideLlmSettings,
      enable_billing: enableBilling,
    },
  } as Awaited<ReturnType<typeof OptionService.getConfig>>);
};

describe("useSettingsNavItems", () => {
  beforeEach(() => {
    queryClient.clear();
  });

  it("should return SAAS_NAV_ITEMS when app_mode is 'saas' and enable_billing is true", async () => {
    mockConfig("saas", { enableBilling: true });
    const { result } = renderHook(() => useSettingsNavItems(), { wrapper });

    await waitFor(() => {
      expect(result.current).toEqual(SAAS_NAV_ITEMS);
    });
  });

  it("should filter out billing when enable_billing is false in saas mode", async () => {
    mockConfig("saas");
    const { result } = renderHook(() => useSettingsNavItems(), { wrapper });

    await waitFor(() => {
      expect(
        result.current.find((item) => item.to === "/settings/billing"),
      ).toBeUndefined();
    });
  });

  it("should return OSS_NAV_ITEMS when app_mode is 'oss'", async () => {
    mockConfig("oss");
    const { result } = renderHook(() => useSettingsNavItems(), { wrapper });

    await waitFor(() => {
      expect(result.current).toEqual(OSS_NAV_ITEMS);
    });
  });

  it("should filter out '/settings' item when hide_llm_settings feature flag is enabled", async () => {
    mockConfig("saas", { hideLlmSettings: true });
    const { result } = renderHook(() => useSettingsNavItems(), { wrapper });

    await waitFor(() => {
      expect(
        result.current.find((item) => item.to === "/settings"),
      ).toBeUndefined();
    });
  });
});
